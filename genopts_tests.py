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
    def test_combine(self):
        # type: () -> None
        self.assertEquals(['aba', 'abca'], combine(['ab','abc'],['a']))
        self.assertEquals(['aba', 'abca'], combine(['a'],['ba', 'bca']))
        self.assertEquals(['aba', 'abca'], combine(['aba', 'abca'], ['']))
        self.assertEquals([], combine(['aba', 'abca'], []))

    def test_parse_optional_simple(self):
        # type: () -> None
        rem, parse_tree = parse_optional("[--option]")
        self.assertEquals('', rem)
        self.assertTrue(isinstance(parse_tree, Optional))
        self.assertEquals(1, len(parse_tree.list))
        self.assertTrue(isinstance(parse_tree.list[0], OptionWithArg))
        self.assertEquals("--option", parse_tree.list[0].command)

    def test_parse_optional_mx(self):
        # type: () -> None
        rem, parse_tree = parse_optional("[--option|--no-option]")
        self.assertEquals('', rem)
        self.assertTrue(isinstance(parse_tree, Optional))
        self.assertEquals(2, len(parse_tree.list))
        self.assertTrue(isinstance(parse_tree.list[0], OptionWithArg))
        self.assertTrue(isinstance(parse_tree.list[1], OptionWithArg))
        self.assertEquals("--option", parse_tree.list[0].command)
        self.assertEquals("--no-option", parse_tree.list[1].command)

    def test_parse_optional_short(self):
        # type: () -> None
        rem, parse_tree = parse_optional("[--[no-]option]")
        self.assertEquals('', rem)
        self.assertTrue(isinstance(parse_tree, Optional))
        self.assertEquals(2, len(parse_tree.list))
        self.assertTrue(isinstance(parse_tree.list[0], OptionWithArg))
        self.assertTrue(isinstance(parse_tree.list[1], OptionWithArg))
        self.assertEquals("--option", parse_tree.list[0].command)
        self.assertEquals("--no-option", parse_tree.list[1].command)

    def test_parse_two_patterns(self):
        # type: () -> None
        parse_tree = []
        parse_tree.append(parse_pattern("[--common-option] cmd1 [--same] [--cmd1-option]"))
        parse_tree.append(parse_pattern("[--common-option] cmd2 [--same] [--cmd2-option]"))
        template = Template(parse_tree)
        gf = GenFile(f=open("/dev/zero","w"))
        field_names = dict() # type: Dict[str, str]
        command_index_map = CommandIndexMap()
        parent_map = ParentMap()
        token_action_map = TokenActionMap()
        navigate(template, GenerateParserVisitor(field_names, command_index_map, parent_map, token_action_map))

        gf = GenFile()
        self.assertTrue("--common-option" in token_action_map)
        self.assertTrue("--same" in token_action_map)
        self.assertTrue("--cmd1-option" in token_action_map)
        self.assertTrue("--cmd2-option" in token_action_map)
        self.assertTrue("cmd1" in token_action_map)
        self.assertTrue("cmd2" in token_action_map)

        options = [] # type: List[OptionWithArg]
        navigate(template, OptionWithArgExtractorVisitor(True, options))
        self.assertEquals(4, len(options))

if __name__ == "__main__":
    unittest.main()
