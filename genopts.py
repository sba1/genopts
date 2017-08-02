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
# TODO: There is no real difference beteen [] that contains options and those that can
#   be found in shorted options, this is not really reflected in this approach

from __future__ import print_function

import collections
import sys

if False: # For MyPy, see https://stackoverflow.com/questions/446052/how-can-i-check-for-python-version-in-a-program-that-uses-new-language-features
    from typing import List,IO,Union,Tuple

################################################################################

class Command:
    """
    A command contains a command string, a list of options (that may be empty)
    and an optional subcommand.
    """
    def __init__(self, command, options, subcommand):
        # type: (str, List[Optional], Command)->None
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
        # type: (str, str)->None
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
        # type: (List[OptionWithArg])->None
        self.list = list
    def __repr__(self):
        return "Optional(" + repr(self.list) + ")"

class Pattern:
    """Contains commands"""
    def __init__(self, list):
        # type: (List[Command])->None
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
    # type: (str) -> Tuple[str, str]
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
    # type: (str) -> Tuple[str, Command]
    rem, command_tk = parse_command_token(command)
    if rem is None:
        return None, None

    options = [] # type: List[Optional]
    subcommand = None # type: Command

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
    # type: (str)->Tuple[str, OptionWithArg]
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

def combine(first,second):
    # type: (List[str],List[str])->List[str]
    r = [] # type: List[str]
    for a in first:
        for b in second:
            r.append(a+b)
    return r

def expand(token):
    # type: (List[Tuple[int,str]])->List[str]
    """Expand the given tokens and return a list of strings with possible matches"""
    if len(token) == 0:
        return ['']

    l = [] # type: List[str]

    if token[0][0] == 0:
        l.append(token[0][1])
    else:
        l.append(token[0][1])
        l.append('')

    expanded = expand(token[1:])
    return combine(l, expanded)


def parse_shorted_options(option):
    # type: (str)->Tuple[str, List[str]]
    """
    Parses a shorted option token that really is a mutual exlusive set of
    options, e.g., --[no]-option. This call will already expand the argument,
    i.e., it will return two options: --option and --no-option.

    Parameters
    ----------
    option : the string to parse

    Returns
    -------
    rem, list
        a tuple of the remainder (not consumed part) of the string and a list
        of parsed options (OptionWithArg).
        None, None on a failure
    """
    level = 0 # Type: int
    variants = 1 # Type: int
    last_pos = 0 # Type: int
    token = [] # Type: List[Tuple[int,str]]
    for i in range(0,len(option)):
        if option[i] == '[':
            token.append((0, option[last_pos:i]))
            level = level + 1
            variants = variants + 1
            last_pos = i + 1
        if option[i] == '|':
            return None,None
        if option[i] == ']':
            token.append((level, option[last_pos:i]))
            if level == 0:
                break
            level = level - 1
            last_pos = i + 1

    options = expand(token)
    if options is None:
        return None, None
    return option[i:], options

def parse_optional(optional):
    # type: (str)->Tuple[str,Optional]
    if optional[0] != '[': return None, None
    rem = optional[1:]
    l = [] # type: List[OptionWithArg]
    while len(rem) > 0 and rem[0] != ']':
        elm = None
        new_rem, elm = parse_command_with_arg(rem)

        if new_rem is None:
            new_rem, options = parse_shorted_options(rem)
            if new_rem is not None:
                for o in options[1:]:
                    l.append(OptionWithArg(o, None))
                elm = OptionWithArg(options[0], None)
        if new_rem is None:
            new_rem, command = parse_command_token(rem)
            elm = OptionWithArg(command, None)
        if new_rem is None: return None, None
        rem = new_rem
        l.append(elm)

        rem = skip_spaces(rem)
        if rem[0] == '|':
            rem = skip_spaces(rem[1:])
    if rem[0] != ']': return None, None
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
        # type: (IO[str])->None
        self.f = f
        # Stores the indendation level
        self.level = 0 # type: int

    def writeline(self, str=""):
        # type: (str)->None
        if str.startswith('}'):
            self.level = self.level - 1;
        print('\t' * self.level + str,file=self.f)
        if str == '{':
            self.level = self.level + 1

################################################################################

# Poor man's visitor
class Visitor:
    def enter_pattern(self, n):
        # type: (Pattern)->None
        pass
    def leave_pattern(self, n):
        # type: (Pattern)->None
        pass
    def enter_optional(self, n):
        # type: (Optional)->None
        pass
    def leave_optional(self, n):
        # type: (Optional)->None
        pass
    def visit_command(self, n):
        # type: (Command)->None
        pass
    def visit_option_with_arg(self, n):
        # type: (OptionWithArg)->None
        pass

# Similar to accept() but does implement the naviation
# in a monolitic fashion
def navigate(n, visitor):
    # type: (Union[Pattern,Command,Optional,OptionWithArg], Visitor)->None
    """
    Navigate through the hierarchy starting at n and call the visitor
    """
    if isinstance(n, Pattern):
        visitor.enter_pattern(n)
        for c in n.list:
            navigate(c, visitor)
        visitor.leave_pattern(n)
    elif isinstance(n, Optional):
        visitor.enter_optional(n)
        for a in n.list:
            navigate(a, visitor)
        visitor.leave_optional(n)
    elif isinstance(n, Command):
        visitor.visit_command(n)
        for o in n.options:
            navigate(o, visitor)
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
        # type: (GenFile)->None
        self.cmds = [] # type: List[Optional]
        self.gf = gf

    def enter_optional(self, n):
        self.cmds = []

    def leave_optional(self, n):
        if len(self.cmds) < 2:
            return

        self.gf.writeline("{")
        self.gf.writeline("int count = 0;")
        for cmd in self.cmds:
            self.gf.writeline("count += !!cli->{0};".format(makename(cmd)))
        opts = [cmd.command for cmd in self.cmds]
        self.gf.writeline("if (count > 1)")
        self.gf.writeline("{")
        self.gf.writeline("fprintf(stderr, \"Only one of {0} may be given\\n\");".format(", ".join(opts)))
        self.gf.writeline("return 0;")
        self.gf.writeline("}")
        self.gf.writeline("}")

    def visit_option_with_arg(self, n):
        self.cmds.append(n)

################################################################################

class GenerateCommandValidatorVisitor(Visitor):
    def __init__(self, gf, option_cmd_parents):
        # type: (GenFile,Dict[Union[Pattern,Command,Optional,OptionWithArg],List[int]])->None
        self.gf = gf
        self.option_cmd_parents = option_cmd_parents

    def visit_command(self, n):
        # type: (Command)->None
        self.cur_command_name = n.command

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg)->None
        name = makename(n)
        cur_command_name = name + "_cmd"
        assert len(self.option_cmd_parents[n]) == 1
        self.gf.writeline("if (cli->{0} != 0 && cli->{0} != {1})".format(cur_command_name, self.option_cmd_parents[n][0]))
        self.gf.writeline("{")
        self.gf.writeline("fprintf(stderr,\"Option {0} may be given only for the \\\"{1}\\\" command\\n\");".format(n.command,self.cur_command_name))
        self.gf.writeline("return 0;")
        self.gf.writeline("}")

################################################################################

def is_flag(str):
    # type: (str)->bool
    return str[0] == '-'

def makecname(str):
    # type: (str)->str
    str = str.replace("-", "_")
    return str.lstrip("_")

def makename(o):
    # type: (Union[Command,OptionWithArg])->str
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
        # type: (GenFile, Dict[str,str], Dict[Union[Pattern,Command,Optional,OptionWithArg],List[int]]) -> None
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
        option_cmd_parents:
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
        # type: (str) -> None
        if self.first:
            self.gf.writeline('if (!strcmp("{0}", argv[i]))'.format(str))
            self.first = False
        else:
            self.gf.writeline('else if (!strcmp("{0}", argv[i]))'.format(str))
        self.gf.writeline('{')
    def write_strcmp_epilogue(self):
        # type: () -> None
        self.gf.writeline('}')

    def remember_pos(self, field_name):
        # type: (str) -> None
        cur_command_name = field_name + "_cmd"
        self.field_names[cur_command_name] = "int"
        self.gf.writeline("cli->{0} = cur_command;".format(cur_command_name))

    def visit_command(self, n):
        # type: (Command) -> None
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
        # type: (OptionWithArg) -> None
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

def genopts(patterns):
    # type: (List[str])->None
    parsed = parse_pattern(patterns[0].strip())
    #print(parsed)

    gf = GenFile()

    gf.writeline("#include <stdio.h>")
    gf.writeline("#include <string.h>")

    # Generate the struct cli by calling the generate
    # visitor with a /dev/zero sink. This will fill the
    # field_names dictionary
    field_names = dict() # type: Dict[str,str]
    option_cmd_parents = dict() # type: Dict[Union[Pattern,Command,Optional,OptionWithArg],List[int]]
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
    gf.writeline("static int parse_cli(int argc, char *argv[], struct cli *cli)")
    gf.writeline("{")
    gf.writeline("int i;")
    gf.writeline("int cur_command = -1;")
    gf.writeline("for (i=0; i < argc; i++)")
    gf.writeline("{")

    field_names = dict()
    option_cmd_parents = dict()
    navigate(parsed, GenerateParserVisitor(gf, field_names, option_cmd_parents))

    gf.writeline("else")
    gf.writeline("{")
    gf.writeline('fprintf(stderr,"Unknown command or option \\"%s\\"\\n\", argv[i]);')
    gf.writeline("return 0;")
    gf.writeline("}")
    gf.writeline("}")
    gf.writeline("return 1;")
    gf.writeline("}")
    gf.writeline()

    # Generates the validation function
    gf.writeline("static int validate_cli(struct cli *cli)")
    gf.writeline("{")
    navigate(parsed, GenerateCommandValidatorVisitor(gf, option_cmd_parents))
    navigate(parsed, GenerateMXValidatorVisitor(gf))
    gf.writeline("return 1;")
    gf.writeline("}")

def main():
    lines = sys.stdin.readlines()
    if len(lines) < 1:
        sys.exit("Input must contain at least one line")
    genopts(lines)

if __name__ == "__main__":
    main()
