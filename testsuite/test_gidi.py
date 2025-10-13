#!/usr/bin/env python3

from Cinema.Prompt.GidiSetting import GidiSetting 
import unittest

skip_expr = "[PT_SKIP_TEST]"
reasonNotCompiled = f"{skip_expr} Gidi is NOT compiled. Tests related skipped. Run 'cimbuild -t --enablegidi' to enable testing with Gidi."
class GidiTest(unittest.TestCase):

    def test_gidi_compile(self):
        cdata = GidiSetting()
        if not cdata.isCompiled:
            self.skipTest(reasonNotCompiled)

def get_skip_expr():
    return skip_expr

def skip_test(reason):
    raise unittest.SkipTest(reason)

def skip_test_gidi_not_compile():
    cdata = GidiSetting()
    if not cdata.isCompiled:
        skip_test(reasonNotCompiled)