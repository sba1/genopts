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
    from typing import Dict,List,IO,Union,Tuple

################################################################################

class Command:
    """
    A command contains a command string, a list of options (that may be empty)
    and an optional subcommand.
    """
    def __init__(self, command, options, subcommand):
        # type: (str, List[Optional], Command)->None
        self.command = command
        self.options = options
        self.subcommand = subcommand
    def __repr__(self):
        # type: ()->str
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
        # type: ()->str
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
        # type: ()->str
        return "Optional(" + repr(self.list) + ")"

class Pattern:
    """Contains commands"""
    def __init__(self, list):
        # type: (List[Command])->None
        self.list = list
    def __repr__(self):
        # type: ()->str
        return "Pattern(" + repr(self.list) + ")"

class Template:
    """Contains patterns"""
    def __init__(self, list):
        # type: (List[Template])->None
        self.list = list
    def __repr__(self):
        # type: ()->str
        return "Template(" + repr(self.list) + ")"

################################################################################

def skip_spaces(text):
    # type: (str) -> str
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
    # type: (str) -> Tuple[str, str]
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
            # TODO: Add dummy command
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
    # type: (Union[Template, Pattern, Command, Optional, OptionWithArg], Visitor) -> None
    """
    Navigate through the hierarchy starting at n and call the visitor
    """
    if isinstance(n, Template):
        for t in n.list:
            navigate(t, visitor)
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
        self.cmds = [] # type: List[OptionWithArg]
        self.gf = gf

    def enter_optional(self, n):
        # type: (Optional) -> None
        self.cmds = [] # type: List[OptionWithArg]

    def leave_optional(self, n):
        # type: (Optional) -> None
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
        # type: (OptionWithArg) -> None
        self.cmds.append(n)

################################################################################

class OptionWithArgExtractorVisitor(Visitor):
    def __init__(self, option_with_args):
        # type: (List[OptionWithArg]) -> None
        self.option_with_args = option_with_args

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg)->None
        self.option_with_args.append(n)

################################################################################

def write_command_validation(gf, command_index_map, parent_map, option_with_args):
    # type: (GenFile, CommandIndexMap, ParentMap, List[OptionWithArg]) -> None
    for n in option_with_args:
        name = makename(n)
        cur_command_name = name + "_cmd"
        parents = parent_map.parents_of_option(n)
        parent_names = [p.command if p is not None else "" for p in parents]
        parent_indices = [command_index_map.map(p) for p in parents]

        # Make list of conditions
        conds = ["cli->{0} != {1}".format(cur_command_name, pi) for pi in set(parent_indices)]

        gf.writeline("if (cli->{0} != 0 && {1})".format(cur_command_name, " && ".join(conds)))
        gf.writeline("{")
        gf.writeline("fprintf(stderr,\"Option {0} may be given only for the \\\"{1}\\\" command\\n\");".format(n.command, parent_names[0]))
        gf.writeline("return 0;")
        gf.writeline("}")

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

class ParentMap:
    """
    Instances of this class represent the possible parents of an option_with_arg
    or command.
    """
    def __init__(self):
        # type: () -> None
        self.parents = dict() # type: Dict[str,List[Command]]

    def add_option(self, option_with_arg, parent):
        # type: (OptionWithArg, Command) -> None
        name = option_with_arg.command
        if name in self.parents:
            self.parents[name].append(parent)
        else:
            self.parents[name] = [parent]

    def add_command(self, command, parent):
        # type: (Command, Command) -> None
        name = command.command
        if name in self.parents:
            self.parents[name].append(parent)
        else:
            self.parents[name] = [parent]

    def parents_of_command(self, command):
        # type: (Command) -> List[Command]
        name = command.command
        if name in self.parents:
            return self.parents[name]
        return [];

    def parents_of_option(self, option_with_arg):
        # type: (OptionWithArg) -> List[Command]
        name = option_with_arg.command
        if name in self.parents:
            return self.parents[name]
        return []

class CommandIndexMap:
    """Instances of this class provide a numeric index to a given command"""
    def __init__(self):
        # type: () -> None
        self.index = dict() # type: Dict[str,int]
        self.cur_num = 2

    def map(self, command):
        # type: (Command) -> int
        """
        Map the given command to an index. Command indices start with 2
        because 0 and 1 has a special meaning.
        """
        if command is None:
            return 1
        if command.command in self.index:
            return self.index[command.command]
        self.index[command.command] = self.cur_num
        self.cur_num = self.cur_num + 1
        return self.index[command.command]

class TokenActionMap:
    """
    Instances of this class represent token and their actions.
    """
    def __init__(self):
        # type: () -> None
        self.token_action_map = dict() # type: Dict[str,List[str]]

    def __contains__(self, item):
        # type: (str) -> bool
        return item in self.token_action_map

    def add(self, token, action):
        # type: (str, str) -> None
        if token not in self.token_action_map:
            self.token_action_map[token] = []
        self.token_action_map[token].append(action)

    def write(self, gf):
        # type: (GenFile) -> None
        sorted_tokens = sorted([t for t in self.token_action_map])
        first = True
        for token in sorted_tokens:
            if first:
                gf.writeline('if (!strcmp("{0}", argv[i]))'.format(token))
                first = False
            else:
                gf.writeline('else if (!strcmp("{0}", argv[i]))'.format(token))

            gf.writeline("{")
            for a in self.token_action_map[token]:
                gf.writeline(a)
            gf.writeline("}")

class GenerateParserVisitor(Visitor):
    """
    Vistor that generates the parsing of the command line arguments
    """
    def __init__(self, field_names, command_index_map, parent_map, token_action_map):
        # type: (Dict[str,str], CommandIndexMap, ParentMap, TokenActionMap) -> None
        """
        Constructs the visitor.

        Parameters
        ----------
        field_names:
            A dictionary in which all required field names of the struct
            are stored including their type. This will be modified by the
            visitor.
        command_index_map:
            Filled by this function. Associates an integer index with a command.
        parent_map:
            Filled by this functions. Corresponds to a map from commands or
            options to commands.
        token_action_map:
            Filled by this visitor. Will hole all relevant tokens with their
            action.
        """
        self.field_names = field_names
        self.command_index_map = command_index_map
        self.parent_map = parent_map
        self.token_action_map = token_action_map
        self.first = True

        # Start with 1 in case there options without commands and 0 means not
        # initialized
        self.cur_command = None # type: Command

    def remember_pos(self, token, field_name):
        # type: (str, str) -> None
        cur_command_name = field_name + "_cmd"
        self.field_names[cur_command_name] = "int"
        self.token_action_map.add(token, "cli->{0} = cur_command;".format(cur_command_name))

    def visit_command(self, n):
        # type: (Command) -> None
        cmd = n.command

        field_name = makename(n)
        pos_name = field_name + "_pos"

        self.field_names[field_name] = "int"
        self.field_names[pos_name] = "int"

        # Remember parent
        self.parent_map.add_command(n, self.cur_command)

        # This was a proper command, level up command index
        self.cur_command = n
        cur_command_idx = self.command_index_map.map(n)

        if cmd not in self.token_action_map:
            self.token_action_map.add(cmd, "cli->{0} = 1;".format(field_name))
            self.token_action_map.add(cmd, "cli->{0} = i;".format(pos_name))
            self.token_action_map.add(cmd, "cur_command = {0};".format(cur_command_idx))

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg) -> None

        # Remember parent
        self.parent_map.add_option(n, self.cur_command)

        option = n.command

        # Write token action if not already done before
        if option not in self.token_action_map:
            field_name = makename(n)
            if n.arg == None:
                self.field_names[field_name] = "int"
                self.token_action_map.add(option, "cli->{0} = 1;".format(field_name))
            else:
                self.field_names[field_name] = "char *"
                field_name = makename(n)

                self.token_action_map.add(option, "if (++i == argc) break;")
                self.token_action_map.add(option, "cli->{0} = argv[i];".format(field_name))

            self.remember_pos(option, field_name)

def genopts(patterns):
    # type: (List[str])->None
    parse_trees = [parse_pattern(p.strip()) for p in patterns]
    template = Template(parse_trees)
    #print(template)
    gf = GenFile()


    gf.writeline("#include <stdio.h>")
    gf.writeline("#include <string.h>")

    field_names = dict() # type: Dict[str,str]
    parent_map = ParentMap()
    command_index_map = CommandIndexMap()
    token_action_map = TokenActionMap()
    navigate(template, GenerateParserVisitor(field_names, command_index_map, parent_map, token_action_map))
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

    token_action_map.write(gf)

    gf.writeline("else")
    gf.writeline("{")
    gf.writeline('fprintf(stderr,"Unknown command or option \\"%s\\"\\n\", argv[i]);')
    gf.writeline("return 0;")
    gf.writeline("}")
    gf.writeline("}")
    gf.writeline("return 1;")
    gf.writeline("}")
    gf.writeline()

    option_with_args = [] # type: List[OptionWithArg]
    navigate(template, OptionWithArgExtractorVisitor(option_with_args))

    # Generates the validation function
    gf.writeline("static int validate_cli(struct cli *cli)")
    gf.writeline("{")
    write_command_validation(gf, command_index_map, parent_map, option_with_args)
    navigate(template, GenerateMXValidatorVisitor(gf))
    gf.writeline("return 1;")
    gf.writeline("}")

def main():
    # type: ()->None
    lines = sys.stdin.readlines()
    if len(lines) < 1:
        sys.exit("Input must contain at least one line")
    genopts(lines)

if __name__ == "__main__":
    main()
