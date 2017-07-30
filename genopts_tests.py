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

if __name__ == "__main__":
    unittest.main()
