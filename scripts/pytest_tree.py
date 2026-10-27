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
    # --color=no: pytest 9 colorizes each per-file progress character even
    # when piped; the parser below expects bare status chars.
    cmd = [VENV_PYTHON, '-m', 'pytest', TEST_DIR, '-v', '--forked',
           '--tb=line', '-q', '--color=no']
    marker = TIERS[tier]
    if marker:
        cmd += ['-m', marker]
    # Rebuild PYTHONPATH from CINEMAPATH instead of trusting the ambient
    # value: install.sh APPENDS to it, so leftovers from the shell (foreign
    # site-packages of another conda env, empty entries -> cwd) ride along
    # and sit AHEAD of the venv's site-packages - a py3.10 numpy from
    # another env then shadows the venv's and breaks every import Cinema
    # test at collection ("no tests collected").
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([
        os.path.join(CINEMA_PATH, 'src', 'python'),
        os.path.join(CINEMA_PATH, 'src', 'python', 'ptgeo', 'python'),
    ])
    result = subprocess.run(cmd, capture_output=True, text=True,
                            cwd=BUILD_DIR, env=env)
    return result.stdout + result.stderr, result.returncode

def parse_results(output):
    stat_map = {'.': 'PASSED', 's': 'SKIPPED', 'F': 'FAILED', 'E': 'ERROR'}
    # Priority when one file mixes outcomes: any failing test must mark the
    # file red, not just its first test.
    prio = {'PASSED': 0, 'SKIPPED': 1, 'FAILED': 2, 'ERROR': 3}
    passed = failed = skipped = error = 0
    # Strip ANSI escapes first (pytest 9 emits them even when piped), and
    # accept both cwd-relative (../src/...) and rootdir-relative (src/...)
    # path spellings across pytest versions.
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    # A per-file progress line carries one character PER TEST ('.F..' = a
    # pass then a fail), so capture the whole run - stopping at the first
    # char would report that file green and let a failure hide behind an
    # earlier passing test in the same file.
    pattern = re.compile(r'(?:\.\./)?src/pythontests/(.+?\.py)\s+([.sFE]+)')

    file_status = {}
    for line in output.split('\n'):
        m = pattern.search(line)
        if not m:
            continue
        relpath, chars = m.group(1), m.group(2)
        for c in chars:
            status = stat_map[c]
            if status == 'PASSED':    passed += 1
            elif status == 'FAILED':  failed += 1
            elif status == 'SKIPPED': skipped += 1
            else:                     error += 1
        worst = max((stat_map[c] for c in chars), key=prio.get)
        prev = file_status.get(relpath)
        if prev is None or prio[worst] > prio[prev]:
            file_status[relpath] = worst

    # The short summary is authoritative for WHICH files failed: a file with
    # many tests wraps its progress chars onto continuation lines that carry
    # no filename, so a wrapped F/E never matches the pattern above.
    summary_pat = re.compile(
        r'^(FAILED|ERROR) (?:\.\./)?src/pythontests/(.+?\.py)\b', re.MULTILINE)
    for m in summary_pat.finditer(output):
        relpath = m.group(2)
        worst = 'FAILED' if m.group(1) == 'FAILED' else 'ERROR'
        prev = file_status.get(relpath)
        if prev is None or prio[worst] > prio[prev]:
            file_status[relpath] = worst

    # Totals likewise from pytest's own final line, which counts the wrapped
    # tests the char scan cannot see.
    m = re.search(r'^=+ (.*?) in [\d.]+s =+\s*$', output, re.MULTILINE)
    if m:
        counts = {label: int(n) for n, label in re.findall(
            r'(\d+) (passed|failed|skipped|errors?)', m.group(1))}
        passed = int(counts.get('passed', passed))
        failed = int(counts.get('failed', failed))
        skipped = int(counts.get('skipped', skipped))
        error = int(counts.get('errors', counts.get('error', error)))

    tree = {}
    for relpath, status in file_status.items():
        parts = relpath.split('/')
        current = tree
        for p in parts[:-1]:
            current = current.setdefault(p, {})
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
