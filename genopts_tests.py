#!/usr/bin/python
#
# (c) 2017 by Sebastian Bauer
#
# Unit tests for genopts.py
#

from __future__ import print_function

from genopts import *

import unittest

class TestParser(unittest.TestCase):
    def test_parse_optional_simple(self):
        rem, parse_tree = parse_optional("[--option]")
        self.assertEquals('', rem)
        self.assertTrue(isinstance(parse_tree, Optional))
        self.assertEquals(1, len(parse_tree.list))
        self.assertTrue(isinstance(parse_tree.list[0], OptionWithArg))
        self.assertEquals("--option", parse_tree.list[0].command)

    def test_parse_optional_mx(self):
        rem, parse_tree = parse_optional("[--option|--no-option]")
        self.assertEquals('', rem)
        self.assertTrue(isinstance(parse_tree, Optional))
        self.assertEquals(2, len(parse_tree.list))
        self.assertTrue(isinstance(parse_tree.list[0], OptionWithArg))
        self.assertTrue(isinstance(parse_tree.list[1], OptionWithArg))
        self.assertEquals("--option", parse_tree.list[0].command)
        self.assertEquals("--no-option", parse_tree.list[1].command)

if __name__ == "__main__":
    unittest.main()
