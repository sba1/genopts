#!/usr/bin/python
#
# (c) 2017 by Sebastian Bauer
#
# Generates low-level parser for given command line arguments
#

# TODO: Add possibility to express that e.g., -m can appear multiple times (e.g., use asteriks)
# TODO: Accept generic string <> (not only in args)
# TODO: Completion support
# TODO: Types

from __future__ import print_function

import collections
import sys

################################################################################

class Command:
    """
    A command contains a command string, a list of options (that may be empty)
    and an optional subcommand.
    """
    def __init__(self, command, options, subcommand):
        self.command = command
        self.options = options # List
        self.subcommand = subcommand
    def __repr__(self):
        if self.subcommand != None:
            subcommand = ", " + repr(self.subcommand)
        else:
            subcommand = ""
        return "Command(" + self.command + ", " + repr(self.options) + subcommand + ')'

class OptionWithArg:
    """Contains an option with args"""
    def __init__(self, command, arg):
        self.command = command
        self.arg = arg
    def __repr__(self):
        if self.arg == None:
            arg = ""
        else:
            arg = ", " + self.arg
        return "OptionWithArg(" + self.command + arg + ")"

class Optional:
    """Contains a set of mutual exlusive options"""
    def __init__(self, list):
        self.list = list
    def __repr__(self):
        return "Optional(" + repr(self.list) + ")"

class Pattern:
    def __init__(self, list):
        self.list = list
    def __repr__(self):
        return "Pattern(" + repr(self.list) + ")"

################################################################################

def skip_spaces(text):
    if len(text) == 0: return text

    for i, c in enumerate(text):
        if c != ' ': break
    return text[i:]

def parse_command_token(command):
    """Parse a command token and return it and and the remainder"""
    for i, c in enumerate(command):
        if c == ' ':
            break
        if c == '[':
            break
        if c == '|':
            break
        if c == ']':
            break
    if i==0:
        return None, None

    return command[i:], command[:i]

def parse_command(command):
    rem, command_tk = parse_command_token(command)
    if rem is None:
        return None, None

    options = []
    subcommand = []

    while rem is not None and len(rem) != 0:
        rem = skip_spaces(rem)
        if rem is None:
            break

        # Try command first
        new_rem, subcommand = parse_command(rem)
        if new_rem is not None:
            rem = new_rem
            #rem = ""
            break

        # Then optional
        new_rem, optional = parse_optional(rem)
        if new_rem is not None:
            options.append(optional)
        rem = new_rem

    return rem, Command(command_tk, options, subcommand)

def parse_arg(arg):
    is_arg = False
    if len(arg) < 3:
        return None, None
    if arg[0] != '<':
        return None, None
    rem = arg[1:]
    for i, c in enumerate(rem):
        if c == '>':
            is_arg = True
            break;
    if not is_arg:
        return None, None
    return rem[i+1:], rem[:i]

def parse_command_with_arg(command_with_arg):
    rem, command = parse_command_token(command_with_arg)
    if rem == None:
        return None, None
    rem = skip_spaces(rem)
    if rem == None:
        return None, None
    rem, arg = parse_arg(rem)
    if rem == None:
        return None, None
    return rem, OptionWithArg(command, arg)

def parse_optional(optional):
    if optional[0] != '[': return None, None
    rem = optional[1:]
    l = []
    while len(rem) > 0 and rem[0] != ']':
        elm = None
        new_rem, elm = parse_command_with_arg(rem)

        if new_rem == None:
            new_rem, command = parse_command_token(rem)
            elm = OptionWithArg(command, None)
        if new_rem is None: return None
        rem = new_rem
        l.append(elm)

        rem = skip_spaces(rem)
        if rem[0] == '|':
            rem = skip_spaces(rem[1:])
    if rem[0] != ']': return None
    return rem[1:], Optional(l)

def parse_pattern(pattern):
    rem = pattern
    l = []
    while rem is not None and len(rem) != 0:
        rem = skip_spaces(rem)
        next_rem, command = parse_command(rem)
        if next_rem is not None:
            l.append(command)
        else:
            next_rem, optional = parse_optional(rem)
            l.append(optional)
        if next_rem is None:
            return
        rem = next_rem
    return Pattern(l)

################################################################################
class GenFile:
    def __init__(self, f=sys.stdout):
        self.f = f
        # Stores the indendation level
        self.level = 0

    def writeline(self, str=""):
        if str.startswith('}'):
            self.level = self.level - 1;
        print('\t' * self.level + str,file=self.f)
        if str == '{':
            self.level = self.level + 1

################################################################################

# Poor man's visitor
class Visitor:
    def enter_pattern(self, n):
        pass
    def leave_pattern(self, n):
        pass
    def enter_optional(self, n):
        pass
    def leave_optional(self, n):
        pass
    def visit_command(self, n):
        pass
    def visit_option_with_arg(self, n):
        pass

# Similar to accept() but does implement the naviation
# in a monolitic fashion
def navigate(n, visitor):
    """
    Navigate through the hierarchy starting at n and call the visitor
    """
    if isinstance(n, Pattern):
        visitor.enter_pattern(n)
        for e in n.list:
            navigate(e, visitor)
        visitor.leave_pattern(n)
    elif isinstance(n, Optional):
        visitor.enter_optional(n)
        for e in n.list:
            navigate(e, visitor)
        visitor.leave_optional(n)
    elif isinstance(n, Command):
        visitor.visit_command(n)
        for e in n.options:
            navigate(e, visitor)
        if n.subcommand is not None:
            navigate(n.subcommand, visitor)
    elif isinstance(n, OptionWithArg):
        visitor.visit_option_with_arg(n)

################################################################################

class GenerateMXValidatorVisitor(Visitor):
    """
    Visitor to generate code for validation of multual exclusions.
    """
    def __init__(self, gf):
        self.cmds = []
        self.gf = gf

    def enter_optional(self, n):
        self.cmds = []

    def leave_optional(self, n):
        if len(self.cmds) < 2:
            return

        gf.writeline("{")
        gf.writeline("int count = 0;")
        for cmd in self.cmds:
            gf.writeline("count += !!cli->{0};".format(makename(cmd)))
        opts = [cmd.command for cmd in self.cmds]
        gf.writeline("if (count > 1)")
        gf.writeline("{")
        gf.writeline("fprintf(stderr, \"Only one of {0} may be given\\n\");".format(", ".join(opts)))
        gf.writeline("return 0;")
        gf.writeline("}")
        gf.writeline("}")

    def visit_option_with_arg(self, n):
        self.cmds.append(n)

################################################################################

class GenerateCommandValidatorVisitor(Visitor):
    def __init__(self, gf, option_cmd_parents):
        self.gf = gf
        self.option_cmd_parents = option_cmd_parents

    def visit_command(self, n):
        self.cur_command_name = n.command

    def visit_option_with_arg(self, n):
        name = makename(n)
        cur_command_name = name + "_cmd"
        assert len(self.option_cmd_parents[n]) == 1
        gf.writeline("if (cli->{0} != 0 && cli->{0} != {1})".format(cur_command_name, self.option_cmd_parents[n][0]))
        gf.writeline("{")
        gf.writeline("fprintf(stderr,\"Option {0} may be given only for the \\\"{1}\\\" command\\n\");".format(n.command,self.cur_command_name))
        gf.writeline("return 0;")
        gf.writeline("}")

################################################################################

def is_flag(str):
    return str[0] == '-'

def makecname(str):
    str = str.replace("-", "_")
    return str.lstrip("_")

def makename(o):
    """
    Make a field name for a given object.
    """
    if isinstance(o, Command):
        return makecname(o.command)
    elif isinstance(o, OptionWithArg):
        if o.arg is not None:
            return makecname(o.arg)
        else:
            return makecname(o.command)
    sys.exit("Wrong class type")

class GenerateParserVisitor(Visitor):
    """
    Vistor that generates the parsing of the command line arguments
    """
    def __init__(self, gf, field_names, option_cmd_parents):
        """
        Constructs the visitor.

        Parameters
        ----------
        gf: GenFile
            Where the generated code is written to
        field_names:
            A dictionary in which all required field names of the struct
            are stored including their type. This will be modified by the
            visitor.
        parents:
            A dictionary of the possible parents of a command. This will be
            modified by the visitor.
        """
        self.gf = gf
        self.first = True
        self.field_names = field_names
        self.option_cmd_parents = option_cmd_parents
        self.first = True
        # Start with 1 in case there options without commands and 0 means not
        # initialized
        self.cur_command = 1

    def write_strcmp_prologue(self, str):
        if self.first:
            self.gf.writeline('if (!strcmp("{0}", argv[i]))'.format(str))
            self.first = False
        else:
            self.gf.writeline('else if (!strcmp("{0}", argv[i]))'.format(str))
        self.gf.writeline('{')
    def write_strcmp_epilogue(self):
        self.gf.writeline('}')

    def remember_pos(self, field_name):
        cur_command_name = field_name + "_cmd"
        self.field_names[cur_command_name] = "int"
        self.gf.writeline("cli->{0} = cur_command;".format(cur_command_name))

    def visit_command(self, n):
        cmd = n.command
        self.write_strcmp_prologue(cmd)

        field_name = makename(n)
        pos_name = field_name + "_pos"

        self.field_names[field_name] = "int"
        self.field_names[pos_name] = "int"

        # This was a proper command, level up command index
        self.cur_command = self.cur_command + 1

        self.gf.writeline("cli->{0} = 1;".format(field_name))
        self.gf.writeline("cli->{0} = i;".format(pos_name))
        self.gf.writeline("cur_command = {0};".format(self.cur_command))

        # Remember our parent, for now only one parent
        self.option_cmd_parents[n] = [self.cur_command]

        self.write_strcmp_epilogue()

    def visit_option_with_arg(self, n):
        self.write_strcmp_prologue(n.command)

        field_name = makename(n)
        if n.arg == None:
            self.field_names[field_name] = "int"
            self.gf.writeline("cli->{0} = 1;".format(field_name))
        else:
            self.field_names[field_name] = "char *"
            field_name = makename(n)

            self.gf.writeline("if (++i == argc) break;")
            self.gf.writeline("cli->{0} = argv[i];".format(field_name))
        self.remember_pos(field_name)

        # Remember our parent, for now only one parent
        self.option_cmd_parents[n] = [self.cur_command]

        self.write_strcmp_epilogue()

lines = sys.stdin.readlines()
if len(lines) < 1:
    sys.exit("Input must contain at least one line")

parsed = parse_pattern(lines[0].strip())
#print(parsed)

gf = GenFile()

gf.writeline("#include <stdio.h>")
gf.writeline("#include <string.h>")

# Generate the struct cli by calling the generate
# visitor with a /dev/zero sink. This will fill the
# field_names dictionary
field_names = dict()
option_cmd_parents = dict()
navigate(parsed, GenerateParserVisitor(GenFile(f=open("/dev/zero", "w")), field_names, option_cmd_parents))
sorted_field_names = sorted([k for k in field_names])

gf.writeline()
gf.writeline("struct cli")
gf.writeline("{")
for k in sorted_field_names:
    t = field_names[k]
    space = ' '
    if t.endswith('*'):
        space = ''
    gf.writeline("{0}{1}{2};".format(t, space, k))
gf.writeline("};")

# Generate a function that parses the command line and populates
# the struct cli. It does not yet make verification
gf.writeline()
gf.writeline("void parse(int argc, char *argv[], struct cli *cli)")
gf.writeline("{")
gf.writeline("int i;")
gf.writeline("int cur_command = -1;")
gf.writeline("for (i=0;i < argc; i++)")
gf.writeline("{")

field_names = dict()
option_cmd_parents = dict()
navigate(parsed, GenerateParserVisitor(gf, field_names, option_cmd_parents))

gf.writeline("}")
gf.writeline("}")
gf.writeline()

# Generates the validation function
gf.writeline("int validate(struct cli *cli)")
gf.writeline("{")
navigate(parsed, GenerateCommandValidatorVisitor(gf, option_cmd_parents))
navigate(parsed, GenerateMXValidatorVisitor(gf))
gf.writeline("return 1;")
gf.writeline("}")
