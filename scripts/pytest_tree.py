#!/usr/bin/env python3
"""Run pytest and format results as a filesystem tree."""

import argparse
import subprocess
import sys
import os
import re

CINEMA_PATH = os.environ.get('CINEMAPATH')
if not CINEMA_PATH:
    sys.exit("Error: CINEMAPATH is not set - source env.sh first.")
BUILD_DIR = os.path.join(CINEMA_PATH, 'cinemabin')
TEST_DIR = os.path.join(CINEMA_PATH, 'src', 'pythontests')
# Prefer the project venv's interpreter - via the version-agnostic 'python3'
# symlink rather than a hardcoded python3.10 - and fall back to the
# interpreter running this script when the venv does not exist.
VENV_PYTHON = os.path.join(CINEMA_PATH, 'cinemavirenv', 'bin', 'python3')
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

# Test tiers, matching the markers registered in src/pythontests/conftest.py:
# fast = unmarked, medium = 50 ms - 0.7 s, slow = > 0.7 s.
TIERS = {
    'fast': 'not medium and not slow',
    'medium': 'not slow',
    'full': None,
}

def run_pytest(tier):
    cmd = [VENV_PYTHON, '-m', 'pytest', TEST_DIR, '-v', '--forked', '--tb=line', '-q']
    marker = TIERS[tier]
    if marker:
        cmd += ['-m', marker]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=BUILD_DIR)
    return result.stdout + result.stderr, result.returncode

def parse_results(output):
    stat_map = {'.': 'PASSED', 's': 'SKIPPED', 'F': 'FAILED', 'E': 'ERROR'}
    tree = {}
    passed = failed = skipped = error = 0
    pattern = re.compile(r'\.\./src/pythontests/(.+?\.py)\s+([.sFE])')
    
    for line in output.split('\n'):
        m = pattern.search(line)
        if m:
            relpath = m.group(1)
            status_char = m.group(2)
            status = stat_map.get(status_char, '?')
            
            if status == 'PASSED':    passed += 1
            elif status == 'FAILED':  failed += 1
            elif status == 'SKIPPED': skipped += 1
            elif status == 'ERROR':   error += 1
            
            parts = relpath.split('/')
            current = tree
            for p in parts[:-1]:
                if p not in current:
                    current[p] = {}
                current = current[p]
            current[parts[-1]] = status
    
    return tree, passed, failed, skipped, error

def _has_failure(d):
    for v in d.values():
        if isinstance(v, dict):
            if _has_failure(v):
                return True
        elif v in ('FAILED', 'ERROR'):
            return True
    return False

def _root_color(tree):
    if _has_failure(tree):
        return '31'  # red
    if any(v == 'SKIPPED' for v in _walk(tree)):
        return '33'  # yellow
    return '32'      # green

def _walk(d):
    for v in d.values():
        if isinstance(v, dict):
            yield from _walk(v)
        else:
            yield v

def print_tree(tree, prefix='', root_label='pythontests/'):
    items = sorted(tree.items())
    
    # Print root
    rc = _root_color(tree)
    print(f"\033[{rc}m{root_label}\033[0m")
    
    for i, (name, value) in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = '└── ' if is_last else '├── '
        
        if isinstance(value, dict):
            has_fail = _has_failure(value)
            line = f"{prefix}{connector}{name}/"
            if has_fail:
                print(f"\033[31m{line}\033[0m")
            else:
                print(line)
            ext = '    ' if is_last else '│   '
            # Print subtree without its own root
            _print_subtree(value, prefix + ext, is_last)
        else:
            _print_file(name, value, prefix, connector)

def _print_subtree(tree, prefix, parent_last):
    items = sorted(tree.items())
    for i, (name, value) in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = '└── ' if is_last else '├── '
        if isinstance(value, dict):
            has_fail = _has_failure(value)
            line = f"{prefix}{connector}{name}/"
            print(f"\033[31m{line}\033[0m" if has_fail else line)
            ext = '    ' if is_last else '│   '
            _print_subtree(value, prefix + ext, is_last)
        else:
            _print_file(name, value, prefix, connector)

def _print_file(name, status, prefix, connector):
    if status == 'PASSED':
        print(f"\033[32m{prefix}{connector}{name} ✓\033[0m")
    elif status == 'FAILED':
        print(f"\033[31m{prefix}{connector}{name} ✗\033[0m")
    elif status == 'SKIPPED':
        print(f"\033[33m{prefix}{connector}{name} –\033[0m")
    else:
        print(f"\033[31m{prefix}{connector}{name} !\033[0m")

def main():
    ap = argparse.ArgumentParser(description="Run pytest and print per-file results as a tree.")
    ap.add_argument('--tier', choices=sorted(TIERS), default='full',
                    help="test tier: 'fast' (pre-push/cimbuild -t), 'medium' (-tt), "
                         "'full' (-ttt, default when run directly)")
    args = ap.parse_args()

    print("\n=== Python Tests Tree ===\n")
    output, retcode = run_pytest(args.tier)
    tree, passed, failed, skipped, error = parse_results(output)

    # An empty tree means the pytest subprocess produced no parseable per-file
    # results. That happens when pytest itself failed to run (e.g. 'No module
    # named pytest' on stderr) and, with exit code 5, when it collected no
    # tests. Both must fail the gate instead of silently reporting zero failed
    # tests; the wording mirrors scripts/git-hooks/pre-push.
    if not tree:
        print("  (no tests collected)")
        if retcode == 5:
            print(f"pytest_tree: pytest collected no tests (tier '{args.tier}')",
                  file=sys.stderr)
            return 5
        print("pytest_tree: pytest produced no parseable results (missing "
              "module or collection failure) - install it with:", file=sys.stderr)
        print(f"    {VENV_PYTHON} -m pip install pytest pytest-forked", file=sys.stderr)
        return 1

    print_tree(tree)

    print(f"\n{'─'*40}")
    parts = []
    if passed:  parts.append(f"\033[32m{passed} passed\033[0m")
    if failed:  parts.append(f"\033[31m{failed} failed\033[0m")
    if skipped: parts.append(f"\033[33m{skipped} skipped\033[0m")
    if error:   parts.append(f"\033[31m{error} error\033[0m")
    print(f"Python tests: {', '.join(parts)}\n")
    ret = failed + error
    if ret == 0 and retcode != 0:
        # pytest exited nonzero (interrupted, internal or usage error, ...)
        # although no individual failure was parsed; fail the gate anyway.
        return retcode
    return ret

if __name__ == '__main__':
    sys.exit(main())
