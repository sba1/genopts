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

    def test_parse_command_token(self):
        # type: () -> None
        rem, command_tk = parse_command_token("cmd1 --option")
        self.assertEquals('cmd1', command_tk)
        self.assertEquals(' --option', rem)

        rem, command_tk = parse_command_token("cmd")
        self.assertEquals('cmd', command_tk)
        self.assertEquals('', rem)

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

    def test_parse_command_only(self):
        parse_tree = parse_pattern("cmd")
        self.assertIsNotNone(parse_tree)
        self.assertTrue(isinstance(parse_tree, Pattern))

    def test_parse_varargs(self):
        # type: () -> None
        rem, optional = parse_optional("[<pathspec>...]")
        self.assertIsNotNone(optional)
        self.assertIsNotNone(optional)
        self.assertEquals('', rem)
        self.assertEquals(1, len(optional.list))
        self.assertTrue(isinstance(optional.list[0], Arg))
        self.assertEquals("pathspec", optional.list[0].command)
        if isinstance(optional.list[0], Arg):
            # Work-arround for mypy not being able to type-infer former
            # self.assertTrue(isinstance())
            self.assertTrue(optional.list[0].variadic)

    def test_parse_pattern_with_arg(self):
        # type: () -> None
        parse_tree = parse_pattern("add <file>")
        self.assertIsNotNone(parse_tree)
        self.assertEquals(1, len(parse_tree.list))
        self.assertEquals(1, len(parse_tree.list[0].options))
        opts = parse_tree.list[0].options
        self.assertTrue(isinstance(opts[0], Arg))
        if isinstance(opts[0], Arg):
            self.assertEquals("file", opts[0].command)
            self.assertFalse(opts[0].variadic)

    def test_parse_two_patterns(self):
        # type: () -> None
        parse_tree = []
        parse_tree.append(parse_pattern("[--common-option] cmd1 [--same] [--cmd1-option]"))
        parse_tree.append(parse_pattern("[--common-option] cmd2 [--same] [--cmd2-option]"))
        template = Template(parse_tree)
        gf = GenFile(f=open("/dev/zero","w"))
        context = GeneratorContext()
        token_action_map = context.token_action_map
        navigate(template, GenerateParserVisitor(context))

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
