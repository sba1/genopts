#!/usr/bin/python
#
# (c) 2017 by Sebastian Bauer
#
# Generates low-level parser for given command line arguments
#

# TODO: Add possibility to express that e.g., -m can appear multiple times (e.g., use asteriks)
# TODO: Completion support
# TODO: Types
# TODO: There is no real difference beteen [] that contains options and those that can
#   be found in shorted options, this is not really reflected in this approach

from __future__ import print_function

import collections
import sys

if False: # For MyPy, see https://stackoverflow.com/questions/446052/how-can-i-check-for-python-version-in-a-program-that-uses-new-language-features
    from typing import Dict,List,IO,Union,Set,Tuple

################################################################################

class Command:
    """
    A command contains a command string, a list of options (that may be empty)
    and an optional subcommand.
    """
    def __init__(self, command, options, subcommand, arg = None):
        # type: (str, List[Union[Optional, Arg]], Command, str)->None
        self.command = command
        self.arg = arg
        self.options = options
        self.subcommand = subcommand

    def __repr__(self):
        # type: ()->str
        if self.subcommand != None:
            subcommand = ", " + repr(self.subcommand)
        else:
            subcommand = ""
        if self.arg is not None:
            arg = ", arg=" + self.arg
        else:
            arg = ""
        return "Command(" + self.command + arg + ", "  + repr(self.options) + subcommand + ')'

class Arg:
    """Contains an argument"""
    def __init__(self, name, variadic=False):
        # type: (str, bool) -> None
        self.command = name
        self.variadic = variadic

    def __repr__(self):
        # type: () -> str
        return "Arg(" + self.command + ", variadic=" + str(self.variadic) + ")"

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
        # type: (List[Union[Arg, OptionWithArg]])->None
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
        # type: (List[Pattern])->None
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

def is_special(c):
    # type: (str) -> bool
    if c == ' ':
        return True
    if c == '[':
        return True
    if c == '|':
        return True
    if c == ']':
        return True
    if c == '=':
        return True
    return False

def parse_command_token(command):
    # type: (str) -> Tuple[str, str]
    """Parse a command token and return it and and the remainder"""
    for i, c in enumerate(command):
        if is_special(c):
            break
    if i==0:
        return None, None

    if not is_special(c):
        i = i + 1
    return command[i:], command[:i]

def parse_command(command):
    # type: (str) -> Tuple[str, Command]
    rem, command_tk = parse_command_token(command)
    if rem is None:
        return None, None

    arg = None # type: str
    carg = None # type: str # direct command argument
    options = [] # type: List[Union[Optional, Arg]]
    subcommand = None # type: Command

    while rem is not None and len(rem) != 0:
        if rem[0] == '=' and arg is None:
            # Try comment arg
            new_rem, carg = parse_arg(rem[1:])
            if new_rem is not None:
                rem = new_rem
                continue
        rem = skip_spaces(rem)
        if rem is None:
            break

        # Try arg first
        new_rem, arg = parse_arg(rem)
        if new_rem is not None:
            options.append(Arg(arg))

        if new_rem is None:
            # Try command next
            new_rem, subcommand = parse_command(rem)
            if new_rem is not None:
                rem = new_rem
                #rem = ""
                break

        # Then optional
        if new_rem is None:
            new_rem, optional = parse_optional(rem)
            if new_rem is not None:
                options.append(optional)

        rem = new_rem

    return rem, Command(command_tk, options, subcommand, carg)

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
    """
    Combine/Concatenate each element from first with each element of second.
    """
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
    l = [] # type: List[Union[Arg, OptionWithArg]]
    while len(rem) > 0 and rem[0] != ']':
        elm = None # type: Union[Arg, OptionWithArg]
        new_rem, elm = parse_command_with_arg(rem)

        if new_rem is None:
            new_rem, arg = parse_arg(rem)
            if new_rem is not None:
                varargs = False
                if new_rem.startswith('...'):
                    varargs = True
                    # skip three dots
                    new_rem = new_rem[3:]
                elm = Arg(arg, varargs)
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
    # type: (str) -> Pattern
    rem = pattern
    l = [] # type: List[Command]
    while rem is not None and len(rem) != 0:
        rem = skip_spaces(rem)
        next_rem, command = parse_command(rem)
        if next_rem is not None:
            l.append(command)
        else:
            next_rem, optional = parse_optional(rem)
            command = Command("", [optional], None)
            l.append(command)
        if next_rem is None:
            return None
        rem = next_rem
    return Pattern(l)

################################################################################
class GenFile(object):
    def __init__(self, f=sys.stdout):
        # type: (IO[str])->None
        self.f = f
        # Stores the indendation level
        self.level = 0 # type: int
        self.generated_code = [] # type: List[Union[str,Function]]

    def writeline(self, str=""):
        # type: (str)->None
        if len(str) == 0:
            self.generated_code.append('')
            return
        if str.startswith('}'):
            self.level = self.level - 1;
        self.generated_code.append('\t' * self.level + str)
        if str == '{':
            self.level = self.level + 1

    def add(self, node):
        # type: (Function) -> None
        node.level = 1
        self.generated_code.append(node)

    def flush(self):
        # type: () -> None
        for l in self.generated_code:
            if isinstance(l, basestring):
                print(l, file=self.f)
            elif isinstance(l, Function):
                print("{0} {1}({2})".format(l.output, l.name, ", ".join(l.input), file=self.f))
                print('{', file=self.f)
                l.flush()
                print('}', file=self.f)

class Function(GenFile):
    def __init__(self, parent, name, output, input):
        # (GenFile, str, str, List[str]) -> None
        super(Function, self).__init__(parent.f)
        self.name = name
        self.output = output
        self.input = input
        self.level = 1

################################################################################

# Poor man's visitor
class Visitor:
    def enter_template(self, n):
        # type: (Template) -> None
        pass
    def leave_template(self, n):
        # type: (Template) -> None
        pass
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
    def visit_arg(self, n):
        # type: (Arg)->None
        pass

# Similar to accept() but does implement the naviation
# in a monolitic fashion
def navigate(n, visitor):
    # type: (Union[Template, Pattern, Command, Optional, Arg, OptionWithArg], Visitor) -> None
    """
    Navigate through the hierarchy starting at n and call the visitor
    """
    if isinstance(n, Template):
        visitor.enter_template(n)
        for t in n.list:
            navigate(t, visitor)
        visitor.leave_template(n)
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
    elif isinstance(n, Arg):
        visitor.visit_arg(n)

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

        conds = " + ".join("!!cli->{0}".format(makename(cmd)) for cmd in self.cmds)
        opts = [cmd.command for cmd in self.cmds]
        self.gf.writeline("if (({0}) > 1)".format(conds))
        self.gf.writeline("{")
        self.gf.writeline("fprintf(stderr, \"Only one of {0} may be given\\n\");".format(join_enum(opts, "or")))
        self.gf.writeline("return 0;")
        self.gf.writeline("}")

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg) -> None
        self.cmds.append(n)

################################################################################

class OptionWithArgExtractorVisitor(Visitor):
    def __init__(self, avoid_duplicates, option_with_args):
        # type: (bool, List[OptionWithArg]) -> None
        self.option_with_args = option_with_args
        self.avoid_duplicates = avoid_duplicates
        self.names = set() # type: Set[str]

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg)->None
        if self.avoid_duplicates:
            if n.command in self.names:
                return
            self.names.add(n.command)
        self.option_with_args.append(n)

################################################################################

def join_enum(list, conjunction):
    # type: (List[str], str) -> str
    """Joins the given list of strings with a conjunction."""
    if len(list) == 1:
        return list[0]

    if len(list) == 2:
        return list[0] + " " + conjunction + " " + list[1]

    return ", ".join(list[:-1]) + ", " + conjunction + " " + list[-1]

def write_command_validation(gf, command_index_map, parent_map, option_with_args):
    # type: (GenFile, CommandIndexMap, ParentMap, List[OptionWithArg]) -> None
    for n in option_with_args:
        name = makename(n)
        cur_command_name = name + "_cmd"
        parents = parent_map.parents_of_option(n)
        parent_names = [p.command for p in parents if p is not None]
        parent_indices = [command_index_map.map(p) for p in parents]

        # Make list of conditions
        conds = ["aux->{0} != {1}".format(cur_command_name, pi) for pi in set(parent_indices)]
        valid_commands = ['\\"' + vc + '\\"' for vc in parent_names]
        valid_commands_text = join_enum(sorted(set(valid_commands)), "and") + " command"

        gf.writeline("if (aux->{0} != 0 && {1})".format(cur_command_name, " && ".join(conds)))
        gf.writeline("{")
        gf.writeline("fprintf(stderr,\"Option {0} may be given only for the {1}\\n\");".format(n.command, valid_commands_text))
        gf.writeline("return 0;")
        gf.writeline("}")

################################################################################

class CommandListExtractorVisitor(Visitor):
    def __init__(self, all_commands):
        # type: (List[Tuple[List[Command],List[Arg],Set[str]]]) -> None
        # FIXME: Use class instead of this tuple
        self.all_commands = all_commands # type: List[Tuple[List[Command], List[Arg], Set[str]]]
        self.commands = ([],[],set()) # type: Tuple[List[Command],List[Arg],Set[str]]
        self.optional = 0

    def enter_pattern(self, n):
        # type: (Pattern) -> None
        self.commands = ([],[],set()) # type: Tuple[List[Command],List[Arg]]

    def enter_optional(self, n):
        # type: (Optional) -> None
        self.optional = self.optional + 1

    def leave_optional(self, n):
        # type: (Optional) -> None
        self.optional = self.optional - 1

    def leave_pattern(self, n):
        # type: (Pattern) -> None
        self.all_commands.append(self.commands)

    def visit_command(self, n):
        # type: (Command) -> None
        self.commands[0].append(n)

    def visit_arg(self, n):
        # type: (Arg) -> None
        self.commands[1].append(n)
        if self.optional > 0:
            self.commands[2].add(n.command)

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

    def map_list(self, commands):
        # type: (List[Command]) -> List[int]
        return [self.map(c) for c in commands]

class TokenActionMap:
    """
    Instances of this class represent token and their actions.
    """
    def __init__(self):
        # type: () -> None
        self.token_action_map = dict() # type: Dict[str,List[str]]
        self.token_requires_arg = set() # type: Set[str]

    def __contains__(self, item):
        # type: (str) -> bool
        return item in self.token_action_map

    def add(self, token, action, requires_arg=False):
        # type: (str, str, bool) -> None
        if token not in self.token_action_map:
            self.token_action_map[token] = []
        self.token_action_map[token].append(action)
        if requires_arg:
            self.token_requires_arg.add(token)

    def write(self, gf):
        # type: (GenFile) -> None
        sorted_tokens = sorted([t for t in self.token_action_map])
        first = True
        for token in sorted_tokens:
            if first:
                el = ''
                first = False
            else:
                el = 'else '
            if token in self.token_requires_arg:
                token_len = len(token)
                gf.writeline('{0}if (!strncmp("{1}", argv[i], {2}) && (argv[i][{2}]==\'=\' || !argv[i][{2}]))'.format(el, token, token_len - 1))
            else:
                gf.writeline('{0}if (!strcmp("{1}", argv[i]))'.format(el, token))

            gf.writeline("{")
            for a in self.token_action_map[token]:
                gf.writeline(a)
            gf.writeline("}")

class PositionalActionMap:
    """
    Instances of this class represent positional arguments and their actions.
    """
    def __init__(self):
        # type: () -> None
        self.action_map = [] # type: List[Dict[int,List[str]]]
        self.last_is_variadic = False

    def add(self, pos, cmd_idx, action, variadic=False):
        # type: (int, int, str, bool) -> None
        if self.last_is_variadic:
            raise RuntimeError("""
                Adding another positional argument after a variadic one is not supported!
                """)
        if len(self.action_map) == pos:
            self.action_map.append(dict())
        elif len(self.action_map) < pos:
            raise RuntimeError("""
                Positional arguments must be added consecutively.
                """)

        if cmd_idx not in self.action_map[pos]:
            self.action_map[pos][cmd_idx] = []
        self.action_map[pos][cmd_idx].append(action)
        self.last_is_variadic = variadic

    def write(self, gf, first=False):
        # type: (GenFile, bool) -> None
        for pos, cmd_maps in enumerate(self.action_map):
            for cmd_idx in cmd_maps:
                if first:
                    el = ''
                    first = False
                else:
                    el = 'else '
                gf.writeline('{0}if (cur_position == {1} && cur_command == {2})'.format(el, pos, cmd_idx))

                gf.writeline("{")
                for a in cmd_maps[cmd_idx]:
                    gf.writeline(a)
                gf.writeline("}")

class Variable:
    def __init__(self, name, vtype):
        # type: (str, str) -> None
        self.name = name
        self.vtype = vtype

class Variables:
    """An abstraction of run time variabels needed during parsing."""
    def __init__(self, name):
        # type: (str) -> None
        self.variables = dict() # type: Dict[str, Variable]
        self.name = name

    def add(self, name, vtype):
        # type: (str, str) -> None
        self.variables[name] = Variable(name, vtype)

class GeneratorContext:
    """
    The context of the parser generator
    """
    def __init__(self):
        # type: () -> None
        self.cli_vars = Variables("cli")
        self.aux_vars = Variables("cli_aux")
        self.parent_map = ParentMap()
        self.command_index_map = CommandIndexMap()
        self.token_action_map = TokenActionMap()
        self.positional_action_map = PositionalActionMap()

    def add_cli_var(self, name, vtype):
        # type: (str, str) -> None
        self.cli_vars.add(name, vtype)

    def add_aux_var(self, name, vtype):
        # type: (str, str) -> None
        self.aux_vars.add(name, vtype)

class GenerateParserVisitor(Visitor):
    """
    Vistor that generates the parsing of the command line arguments
    """
    def __init__(self, context):
        # type: (GeneratorContext) -> None
        """
        Constructs the visitor.

        Parameters
        ----------
        context:
            The overall generator context that is setup by this visitor.
        """
        self.context = context
        self.command_index_map = context.command_index_map
        self.parent_map = context.parent_map
        self.token_action_map = context.token_action_map
        self.positional_action_map = context.positional_action_map
        self.first = True

        # Start with 1 in case there options without commands and 0 means not
        # initialized
        self.cur_command = None # type: Command

        # Number of current positional argument
        self.cur_position = 0

    def remember_pos(self, token, field_name):
        # type: (str, str) -> None
        cur_command_name = field_name + "_cmd"
        self.context.add_aux_var(cur_command_name, "int")
        self.token_action_map.add(token, "aux->{0} = cur_command;".format(cur_command_name))

    def visit_command(self, n):
        # type: (Command) -> None
        cmd = n.command
        cmd_requires_arg = n.arg != None

        field_name = makename(n)
        pos_name = field_name + "_pos"

        self.context.add_cli_var(field_name, "int")
        self.context.add_aux_var(pos_name, "int")

        if cmd_requires_arg:
            self.context.add_cli_var(makecname(n.arg), "char *")

        # Remember parent
        self.parent_map.add_command(n, self.cur_command)

        # This was a proper command, level up command index
        self.cur_command = n
        cur_command_idx = self.command_index_map.map(n)

        if cmd not in self.token_action_map:
            self.token_action_map.add(cmd, "cli->{0} = 1;".format(field_name), cmd_requires_arg)
            self.token_action_map.add(cmd, "aux->{0} = i;".format(pos_name), cmd_requires_arg)
            self.token_action_map.add(cmd, "cur_command = {0};".format(cur_command_idx), cmd_requires_arg)

            if cmd_requires_arg:
                self.token_action_map.add(cmd, "")
                self.token_action_map.add(cmd, "if (!argv[i][{0}])".format(len(cmd) - 1))
                self.token_action_map.add(cmd, "{")
                self.token_action_map.add(cmd, "if (i + 1 < argc)")
                self.token_action_map.add(cmd, "{")

                self.token_action_map.add(cmd, "cli->{0} = argv[i+1];".format(makecname(n.arg)))
                self.token_action_map.add(cmd, "i++;")

                self.token_action_map.add(cmd, "}")
                self.token_action_map.add(cmd, "else")
                self.token_action_map.add(cmd, "{")
                self.token_action_map.add(cmd, "fprintf(stderr, \"Argument \\\"{0}\\\" requires a value\\n\");".format(cmd))
                self.token_action_map.add(cmd, "return 0;")
                self.token_action_map.add(cmd, "}")
                self.token_action_map.add(cmd, "}")
                self.token_action_map.add(cmd, "else")
                self.token_action_map.add(cmd, "{")
                self.token_action_map.add(cmd, "cli->{0} = &argv[i][{1}];".format(makecname(n.arg), len(cmd)))
                self.token_action_map.add(cmd, "}")

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg) -> None

        # Remember parent
        self.parent_map.add_option(n, self.cur_command)

        option = n.command

        # Write token action if not already done before
        if option not in self.token_action_map:
            field_name = makename(n)
            if n.arg == None:
                self.context.add_cli_var(field_name, "int")
                self.token_action_map.add(option, "cli->{0} = 1;".format(field_name))
            else:
                self.context.add_cli_var(field_name, "char *")
                field_name = makename(n)

                self.token_action_map.add(option, "if (++i == argc) break;")
                self.token_action_map.add(option, "cli->{0} = argv[i];".format(field_name))

            self.remember_pos(option, field_name)

    def visit_arg(self, n):
        # type: (Arg) -> None
        field_name = makecname(n.command)
        cur_command_idx = self.command_index_map.map(self.cur_command)
        if n.variadic:
            count_field_name = field_name + "_count";

            self.context.add_cli_var(field_name, "char **")
            self.context.add_cli_var(count_field_name, "int")

            # Use helper fields, the real one will be set in the validation phase
            variadic_field_name = 'variadic_argv'
            variadic_count_field_name = 'variadic_argc'

            self.context.add_aux_var(variadic_field_name, "char **")
            self.context.add_aux_var(variadic_count_field_name, "int")

            self.positional_action_map.add(self.cur_position, cur_command_idx, "aux->{0} = &argv[i];".format(variadic_field_name))
            self.positional_action_map.add(self.cur_position, cur_command_idx, "aux->{0} = argc - i;".format(variadic_count_field_name))
            self.positional_action_map.add(self.cur_position, cur_command_idx, "break;")
        else:
            self.context.add_cli_var(field_name, "char *")

            # Use helper fields, the real one will be set in the validation phase
            positional_field_name = 'positional{0}'.format(self.cur_position)
            self.context.add_aux_var(positional_field_name, "char *")

            self.positional_action_map.add(self.cur_position, cur_command_idx, "aux->{0} = argv[i];".format(positional_field_name))
            self.positional_action_map.add(self.cur_position, cur_command_idx, "cur_position++;")

            self.cur_position = self.cur_position + 1

    def leave_pattern(self, n):
        # type: (Pattern) -> None
        self.cur_position = 0

class CommandArgPairs():
    def __init__(self):
        # type: () -> None
        self.pairs = {} # type: Dict[str, List[Tuple[Arg, Arg]]]

    def __contains__(self, command):
        # type: (str) -> bool
        return command in self.pairs

    def __len__(self):
        # type: () -> int
        return len(self.pairs)

def write_struct(gf, variables):
    # type: (GenFile, Variables) -> None
    sorted_field_names = sorted([k for k in variables.variables])

    gf.writeline("struct {0}".format(variables.name))
    gf.writeline("{")
    for k in sorted_field_names:
        t = variables.variables[k].vtype
        space = ' '
        if t.endswith('*'):
            space = ''
        gf.writeline("{0}{1}{2};".format(t, space, k))
    gf.writeline("};")

def genopts(patterns):
    # type: (List[str])->None
    parse_trees = [parse_pattern(p.strip()) for p in patterns]
    template = Template(parse_trees)
    #print(template)
    gf = GenFile()


    gf.writeline("#include <stdio.h>")
    gf.writeline("#include <string.h>")
    gf.writeline()

    context = GeneratorContext()
    navigate(template, GenerateParserVisitor(context))

    if "--help" not in context.token_action_map:
        context.add_cli_var("help", "int")
        context.add_aux_var("help_cmd", "int")
        context.token_action_map.add("--help", "cli->help = 1;")
        context.token_action_map.add("--help", "aux->help_cmd = cur_command;")

    write_struct(gf, context.cli_vars)
    gf.writeline()
    write_struct(gf, context.aux_vars)
    gf.writeline()

    gf.writeline("typedef enum")
    gf.writeline("{")
    gf.writeline("POF_VALIDATE = (1<<0),")
    gf.writeline("POF_USAGE = (1<<1)")
    gf.writeline("} parse_cli_options_t;")
    gf.writeline()

    option_with_args = [] # type: List[OptionWithArg]
    all_commands = [] # type: List[Tuple[List[Command], List[Arg], Set[str]]]
    navigate(template, OptionWithArgExtractorVisitor(True, option_with_args))
    navigate(template, CommandListExtractorVisitor(all_commands))

    # Generates the validation function
    vc = Function(gf,
        output="static int",
        name="validate_cli",
        input=['struct cli *cli', 'struct cli_aux *aux'])
    vc.writeline("if (cli->help)")
    vc.writeline("{")
    vc.writeline("return 1;")
    vc.writeline("}")
    write_command_validation(vc, context.command_index_map, context.parent_map, option_with_args)
    navigate(template, GenerateMXValidatorVisitor(vc))

    # Determine the maximal number of commands for all patterns
    max_commands = max(len(context.command_index_map.map_list(key[0])) for key in all_commands)

    def all_commands_key(key):
        # type: (Tuple[List[Command], List[Arg], Set[str]]) -> List[int]
        """
        The function that turns a Tuple into a key that is suitable for sorting.
        We basicall return the int list mapped from the commands filled up with
        some large numbers because we want to compare shorter patterns later.
        """
        return context.command_index_map.map_list(key[0]) + [999] * max_commands

    all_commands = sorted(all_commands, key=all_commands_key)

    # Add a check for proper command specificiation
    first = True
    for commands in all_commands:
        conds = [] # type: List[str]
        for command in commands[0]:
            conds.append("cli->{0}".format(makename(command)))
        vc.writeline("{0} ({1})".format("if" if first else "else if", " && ".join(conds)))
        vc.writeline("{")

        all_args = commands[1] # type: List[Arg]
        optional_args = commands[2] # type: Set[str]

        # FIXME: Generalize
        if not any(a.variadic for a in all_args) and len(all_args) == 2 and len(optional_args) == 1 and all_args[0].command in optional_args:
            vc.writeline("if (aux->positional{0} != NULL)".format(1))
            vc.writeline("{")
            for pos, arg in enumerate(commands[1]):
                vc.writeline("cli->{0} = aux->positional{1};".format(makecname(arg.command), pos))
            vc.writeline("}")
            vc.writeline("else")
            vc.writeline("{")
            vc.writeline("cli->{0} = aux->positional{1};".format(makecname(all_args[1].command), 0))
            vc.writeline("}")
        else:
            # Resolve positional arguments
            for pos, arg in enumerate(commands[1]):
                if arg.variadic:
                    vc.writeline("cli->{0}_count = aux->variadic_argc;".format(makecname(arg.command)))
                    vc.writeline("cli->{0} = aux->variadic_argv;".format(makecname(arg.command)))
                else:
                    vc.writeline("cli->{0} = aux->positional{1};".format(makecname(arg.command), pos))

        for a in all_args:
            if a.command not in optional_args:
                vc.writeline("if (!cli->{0})".format(makecname(a.command)))
                vc.writeline("{")
                vc.writeline("fprintf(stderr, \"Required argument \\\"{0}\\\" is missing. Use --help for usage\\n\");".format(a.command))
                vc.writeline("return 0;")
                vc.writeline("}")

        vc.writeline("}")
        first = False
    if not first:
        vc.writeline("else")
        vc.writeline("{")
        vc.writeline('fprintf(stderr,"Please specify a proper command. Use --help for usage.\\n");')
        vc.writeline("return 0;")
        vc.writeline("}")

    vc.writeline("return 1;")
    gf.add(vc)

    gf.writeline()
    gf.writeline("/**")
    gf.writeline(" * Print usage for the given cli.")
    gf.writeline(" *")
    gf.writeline(" * @return 1 if usage has been printed, 0 otherwise.")
    gf.writeline(" */")
    gf.writeline("static int usage_cli(char *cmd, struct cli *cli)")
    gf.writeline("{")
    gf.writeline("if (!cli->help)")
    gf.writeline("{")
    gf.writeline("return 0;")
    gf.writeline("}")
    gf.writeline('fprintf(stderr, "usage: %s <command> [<options>]\\n", cmd);'.format(patterns[0].strip()))
    for pattern in sorted(patterns):
        gf.writeline('fprintf(stderr, "{0}\\n");'.format(pattern.strip()))
    gf.writeline("return 1;")
    gf.writeline("}")

    # Generate a function that parses the command line and populates
    # the struct cli. It does not yet make verification
    gf.writeline()
    gf.writeline("static int parse_cli_simple(int argc, char *argv[], struct cli *cli, struct cli_aux *aux)")
    gf.writeline("{")
    gf.writeline("int i;")
    gf.writeline("int cur_command = -1;")
    gf.writeline("int cur_position = 0;")
    gf.writeline("for (i=0; i < argc; i++)")
    gf.writeline("{")

    context.token_action_map.write(gf)
    context.positional_action_map.write(gf)

    gf.writeline("else")
    gf.writeline("{")
    gf.writeline('fprintf(stderr,"Unknown command or option \\"%s\\"\\n\", argv[i]);')
    gf.writeline("return 0;")
    gf.writeline("}")
    gf.writeline("}")
    gf.writeline("return 1;")
    gf.writeline("}")
    gf.writeline()

    gf.writeline("static int parse_cli(int argc, char *argv[], struct cli *cli, parse_cli_options_t opts)")
    gf.writeline("{")
    gf.writeline("struct cli_aux aux;")
    gf.writeline("char *cmd = argv[0];")
    gf.writeline("memset(&aux, 0, sizeof(aux));")
    gf.writeline("argc--;")
    gf.writeline("argv++;")
    gf.writeline("if (!parse_cli_simple(argc, argv, cli, &aux))")
    gf.writeline("{")
    gf.writeline("return 0;")
    gf.writeline("}")
    gf.writeline("if (opts & POF_VALIDATE)")
    gf.writeline("{")
    gf.writeline("if (!validate_cli(cli, &aux))")
    gf.writeline("{")
    gf.writeline("return 0;")
    gf.writeline("}")
    gf.writeline("}")
    gf.writeline("if (opts & POF_USAGE)")
    gf.writeline("{")
    gf.writeline("return !usage_cli(cmd, cli);")
    gf.writeline("}")
    gf.writeline("return 1;")
    gf.writeline("}")
    gf.writeline()
    gf.flush()

def main():
    # type: ()->None
    lines = sys.stdin.readlines()
    if len(lines) < 1:
        sys.exit("Input must contain at least one line")
    genopts(lines)

if __name__ == "__main__":
    main()
