#!/usr/bin/python
#
# (c) 2017 by Sebastian Bauer
#
# Generates low-level parser for given command line arguments
#

# TODO: Add possibility to express that e.g., -m can appear multiple times (e.g., use asteriks)
# TODO: Accept generic string <> (not only in args)
# TODO: Command / Options / Subcommand / Options
# TODO: Add parent command to check which options belong to which command

from __future__ import print_function

import sys

pattern = "commit [-a | --interactive | --patch]  [-F <file> | -m <msg>] [--reset-author]"
pattern2 = "submodule [--quiet] update [--init] [--remote] [-N|--no-fetch] [--[no-]recommend-shallow] [-f|--force] [--rebase|--merge]"

################################################################################

class Command:
    def __init__(self, command):
        self.command = command
    def __repr__(self):
        return "Command("+self.command+")"

class Arg:
    def __init__(self, arg):
        self.arg = arg
    def __repr__(self):
        return "Arg("+self.arg+")"

class CommandWithArg:
    """Contains an option with args"""
    def __init__(self, command, arg):
        self.command = command
        self.arg = arg
    def __repr__(self):
        return "CommandWithArg(" + self.command + ", " + self.arg + ")"

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

def parse_command(command):
    for i, c in enumerate(command):
        if c == ' ':
            break
        if c == '[':
            return None, None
        if c == '|':
            return None, None
        if c == ']':
            break
    return command[i:], command[:i]

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
    rem, command = parse_command(command_with_arg)
    if rem == None:
        return None, None
    rem = skip_spaces(rem)
    if rem == None:
        return None, None
    rem, arg = parse_arg(rem)
    if rem == None:
        return None, None
    return rem, CommandWithArg(command, arg)

def parse_optional(optional):
    if optional[0] != '[': return None
    rem = optional[1:]
    l = []
    while len(rem) > 0 and rem[0] != ']':
        elm = None
        new_rem, elm = parse_command_with_arg(rem)
        if new_rem == None:
            rem, command = parse_command(rem)
            elm = Command(command)
        else:
            rem = new_rem;
        if rem is None: return None
        l.append(elm)

        rem = skip_spaces(rem)
        if rem[0] == '|':
            rem = skip_spaces(rem[1:])
    if rem[0] != ']': return None
    return rem[1:], Optional(l)

def skip_spaces(text):
    if len(text) == 0: return text

    for i, c in enumerate(text):
        if c != ' ': break
    return text[i:]

def parse_pattern(pattern):
    rem = pattern
    l = []
    while rem is not None and len(rem) != 0:
        rem = skip_spaces(rem)
        next_rem, command = parse_command(rem)
        if next_rem is not None:
            l.append(Command(command))
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
#        self.f = open('/dev/zero', 'w')
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
    def visit_command_with_arg(self, n):
        pass

def accept(n, visitor):
    if isinstance(n, Pattern):
        visitor.enter_pattern(n)
        for e in n.list:
            accept(e, visitor)
        visitor.leave_pattern(n)
    elif isinstance(n, Optional):
        visitor.enter_optional(n)
        for e in n.list:
            accept(e, visitor)
        visitor.leave_optional(n)
    elif isinstance(n, Command):
        visitor.visit_command(n)
    elif isinstance(n, CommandWithArg):
        visitor.visit_command_with_arg(n)

################################################################################

class CollectNamesVisitor(Visitor):
    """
    Visitor to collect the names of the command/args in a flat list.
    The lists contain tuples with the name of the command/option and
    the name of the argument.
    """
    def __init__(self, names):
        self.names = names
    def visit_command(self, n):
        self.names.append((n.command, None))
    def visit_command_with_arg(self, n):
        self.names.append((n.command, n.arg))

################################################################################

class GenerateMXValidatorVisitor(Visitor):
    """
    Visitor to generate code for validation of multual exclusions.
    """
    def __init__(self):
        self.cmds = []

    def enter_optional(self, n):
        self.cmds = []

    def leave_optional(self, n):
        if len(self.cmds) < 2:
            return

        print("\t{")
        print("\t\tint count = 0;")
        for cmd in self.cmds:
            print("\t\tcount += !!cli->{0};".format(makename(cmd)))
        opts = [cmd.command for cmd in self.cmds]
        print("\t\tif (count > 1)")
        print("\t\t{")
        print("\t\t\tfprintf(stderr, \"Only one of {0} may be given\\n\");".format(", ".join(opts)))
        print("\t\t\treturn 0;")
        print("\t\t}")
        print("\t}")

    def visit_command(self, n):
        self.cmds.append(n)

    def visit_command_with_arg(self, n):
        self.cmds.append(n)

################################################################################

class GenerateCommandValidatorVisitor(Visitor):
    def __init__(self):
        pass

    def visit_command(self, n):
        pass

################################################################################

parsed = parse_pattern(pattern)
#print(parsed)

names = []
accept(parsed, CollectNamesVisitor(names))
#print(names)

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
    elif isinstance(o, CommandWithArg):
        return makecname(o.arg)
    sys.exit("Wrong class type")

class GenerateParserVisitor(Visitor):
    def __init__(self, gf, field_names):
        self.gf = gf
        self.first = True
        self.field_names = field_names

    def write_strcmp_prologue(self, str):
        self.gf.writeline('if (!strcmp("{0}", argv[i]))'.format(str))
        self.gf.writeline('{')
    def write_strcmp_epilogue(self):
        self.gf.writeline('}')

    def visit_command(self, n):
        cmd = n.command
        self.write_strcmp_prologue(cmd)

        field_name = makename(n)
        self.field_names[field_name] = "int"
        self.gf.writeline("cli->{0} = 1;".format(field_name))
        if not is_flag(cmd):
            pos_name = field_name + "_pos"
            self.field_names[pos_name] = "int"
            self.gf.writeline("cli->{0} = i;".format(pos_name))

        self.write_strcmp_epilogue()

    def visit_command_with_arg(self, n):
        self.write_strcmp_prologue(n.command)

        field_name = makename(n)
        self.field_names[field_name] = "char *"

        field_name = makename(n)

        self.gf.writeline("if (++i == argc) break;")
        self.gf.writeline("cli->{0} = argv[i];".format(field_name))

        self.write_strcmp_epilogue()

gf = GenFile()

gf.writeline("#include <stdio.h>")
gf.writeline("#include <string.h>")

# Generate the struct cli by calling the generate
# visitor with a /dev/zero sink. This will fill the
# field_names dictionary
field_names = dict()
accept(parsed, GenerateParserVisitor(GenFile(f=open("/tmp/huhuhu", "w")), field_names))
gf.writeline("struct cli")
gf.writeline("{")
for k in field_names:
    t = field_names[k]
    space = ' '
    if t.endswith('*'):
        space = ''
    gf.writeline("{0}{1}{2};".format(t, space, k))
gf.writeline("};")
gf.writeline()

# Generate a function that parses the command line and populates
# the struct cli. It does not yet make verification
gf.writeline()
gf.writeline("void parse(int argc, char *argv[], struct cli *cli)")
gf.writeline("{")
gf.writeline("int i;")
gf.writeline("for (i=0;i < argc; i++)")
gf.writeline("{")

field_names = dict()
accept(parsed, GenerateParserVisitor(gf, field_names))

gf.writeline("}")
gf.writeline("}")
gf.writeline()

# Generates the validation function
gf.writeline("int validate(struct cli *cli)")
gf.writeline("{")
accept(parsed, GenerateCommandValidatorVisitor())
accept(parsed, GenerateMXValidatorVisitor())
gf.writeline("return 1;")
gf.writeline("}")
