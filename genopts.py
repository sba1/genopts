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
import textwrap

from lib.parser import *

################################################################################

class Statement(object):
    def __init__(self):
        # type: () -> None
        pass

class DirectStatement(Statement):
    """A direct statement is a statement that is put literally into the code"""
    def __init__(self, st):
        # type: (str) -> None
        self.st = st

    def __repr__(self):
        # type: () -> str
        return self.st

class ReturnStatement(Statement):
    """A return statement emits an instruction to exit a function execution"""
    def __init__(self, val):
        # type: (int) -> None
        self.val = val

    def __repr__(self):
        # type: () -> str
        return "return {0};".format(self.val)

class LValue:
    def __init__(self, name, element):
        # type: (str, Variable) -> None
        self.name = name
        self.element = element

    def __lshift__(self, other):
        # type: (Union[Variable,int]) -> AssignmentStatement
        if isinstance(other, Variable):
            value = other.name
        else:
            value = str(other)
        return AssignmentStatement(self, value)

class AssignmentStatement(Statement):
    def __init__(self, left, right):
        # type: (LValue, str) -> None
        self.left = left
        self.right = right

    def __repr__(self):
        # type: () -> str
        return self.left.name + "->" + self.left.element.name + " = " + str(self.right) + ";"

class IfStatement(Statement):
    def __init__(self, cond, then, otherwise=None):
        # type: (str, ThenBlock, Block) -> None
        self.cond = cond
        self.then = then
        self.otherwise = otherwise

class Variable:
    def __init__(self, name, vtype, init = None):
        # type: (str, str, str) -> None
        self.name = name
        self.vtype = vtype
        self.init = init

# Shortcut
V = Variable

class Variables:
    """An abstraction of run time variabels needed during parsing."""
    def __init__(self, name = None):
        # type: (str) -> None
        self.variables = dict() # type: Dict[str, Variable]
        self.name = name

    def add(self, name, vtype, init = None):
        # type: (str, str, str) -> None
        self.variables[name] = Variable(name, vtype, init)

    def add_var(self, var):
        # type: (Variable) -> None
        self.variables[var.name] = var

    def __getitem__(self, key):
        # type: (str) -> Variable
        return self.variables[key]

class Block(object):
    def __init__(self):
        # type: ()->None
        # Stores the indendation level
        self.level = 0 # type: int
        self.generated_code = [] # type: List[Union[Function, Block, Statement]]
        self.locals = Variables()

    def add(self, node):
        # type: (Union[str, Function, Block, Statement]) -> Block
        if isinstance(node, basestring):
            node = DirectStatement(node)
        self.generated_code.append(node)
        return self

    def ret(self, val):
        # type: (int) -> None
        self.add(ReturnStatement(val))

    def iff(self, cond):
        # type: (str) -> IfStatement
        otherwise = Block()
        then = ThenBlock(otherwise)
        if_then_else = IfStatement(cond, then, otherwise)
        self.add(if_then_else)
        return if_then_else

class ThenBlock(Block):
    def __init__(self, otherwise_block):
        # type: (Block) -> None
        super(ThenBlock, self).__init__()
        self.otherwise_block = otherwise_block

    def otherwise(self):
        # type: () -> Block
        return self.otherwise_block

class Function(Block):
    def __init__(self, name, output , input):
        # type: (str, str, List[Variable]) -> None
        super(Function, self).__init__()
        self.name = name
        self.output = output
        self.input = input
################################################################################

class GenFile(object):
    def __init__(self, f=sys.stdout):
        # type: (IO[str])->None
        self.f = f
        # Stores the indendation level
        self.level = 0 # type: int
        self.generated_code = [] # type: List[str]

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

    def flush(self):
        # type: () -> None
        for l in self.generated_code:
            print(l, file=self.f)

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
    def __init__(self, b):
        # type: (Block) -> None
        self.cmds = [] # type: List[OptionWithArg]
        self.b = b

    def enter_optional(self, n):
        # type: (Optional) -> None
        self.cmds = [] # type: List[OptionWithArg]

    def leave_optional(self, n):
        # type: (Optional) -> None
        if len(self.cmds) < 2:
            return

        conds = " + ".join("!!cli->{0}".format(makename(cmd)) for cmd in self.cmds)
        opts = [cmd.command for cmd in self.cmds]
        self.b.add("if (({0}) > 1)".format(conds))
        self.b.add("{")
        self.b.add("fprintf(stderr, \"Only one of {0} may be given\\n\");".format(join_enum(opts, "or")))
        self.b.add("return 0;")
        self.b.add("}")

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

def write_command_validation(b, command_index_map, parent_map, option_with_args):
    # type: (Block, CommandIndexMap, ParentMap, List[OptionWithArg]) -> None
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

        b.add("if (aux->{0} != 0 && {1})".format(cur_command_name, " && ".join(conds)))
        b.add("{")
        b.add("fprintf(stderr,\"Option {0} may be given only for the {1}\\n\");".format(n.command, valid_commands_text))
        b.add("return 0;")
        b.add("}")

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
        self.token_action_map = dict() # type: Dict[str,Block]
        self.token_requires_arg = set() # type: Set[str]

    def __contains__(self, item):
        # type: (str) -> bool
        return item in self.token_action_map

    def add(self, token, action, requires_arg=False):
        # type: (str, Union[str, Statement], bool) -> None
        if token not in self.token_action_map:
            self.token_action_map[token] = Block()
        self.token_action_map[token].add(action)
        if requires_arg:
            self.token_requires_arg.add(token)

    def write(self, b):
        # type: (Block) -> None
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
                b.add('{0}if (!strncmp("{1}", argv[i], {2}) && (argv[i][{2}]==\'=\' || !argv[i][{2}]))'.format(el, token, token_len - 1))
            else:
                b.add('{0}if (!strcmp("{1}", argv[i]))'.format(el, token))

            b.add(self.token_action_map[token])

class PositionalActionMap:
    """
    Instances of this class represent positional arguments and their actions.
    """
    def __init__(self):
        # type: () -> None
        self.action_map = [] # type: List[Dict[int,Block]]
        self.last_is_variadic = False

    def add(self, pos, cmd_idx, action, variadic=False):
        # type: (int, int, Union[str, Statement], bool) -> None
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
            self.action_map[pos][cmd_idx] = Block()
        self.action_map[pos][cmd_idx].add(action)
        self.last_is_variadic = variadic

    def write(self, b, first=False):
        # type: (Block, bool) -> None
        for pos, cmd_maps in enumerate(self.action_map):
            for cmd_idx in cmd_maps:
                if first:
                    el = ''
                    first = False
                else:
                    el = 'else '
                b.add('{0}if (cur_position == {1} && cur_command == {2})'.format(el, pos, cmd_idx))

                b.add(cmd_maps[cmd_idx])

class GeneratorContext:
    """
    The context of the parser generator
    """
    def __init__(self):
        # type: () -> None
        self.cli_vars = Variables("cli")
        self.aux_vars = Variables("cli_aux")
        self.cur_command_var = Variable("cur_command", "int", "-1")
        self.parent_map = ParentMap()
        self.command_index_map = CommandIndexMap()
        self.token_action_map = TokenActionMap()
        self.positional_action_map = PositionalActionMap()

    def cli_var(self, name, vtype):
        # type: (str, str) -> Variable
        self.cli_vars.add(name, vtype)
        return self.cli_vars[name]

    def aux_var(self, name, vtype):
        # type: (str, str) -> Variable
        self.aux_vars.add(name, vtype)
        return self.aux_vars[name]

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

        # Start with 1 in case there options without commands and 0 means not
        # initialized
        self.cur_command = None # type: Command

        # Number of current positional argument
        self.cur_position = 0

    def remember_pos(self, token, field_name):
        # type: (str, str) -> None
        cur_command_name = field_name + "_cmd"
        self.context.aux_var(cur_command_name, "int")
        self.token_action_map.add(token, "aux->{0} = cur_command;".format(cur_command_name))

    def visit_command(self, n):
        # type: (Command) -> None
        cmd = n.command
        cmd_requires_arg = n.arg != None

        field_name = makename(n)
        pos_name = field_name + "_pos"

        field = self.context.cli_var(field_name, "int")
        pos = self.context.aux_var(pos_name, "int")

        if cmd_requires_arg:
            self.context.cli_var(makecname(n.arg), "char *")

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
                self.context.cli_var(field_name, "int")
                self.token_action_map.add(option, "cli->{0} = 1;".format(field_name))
            else:
                self.context.cli_var(field_name, "char *")
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

            self.context.cli_var(field_name, "char **")
            self.context.cli_var(count_field_name, "int")

            # Use helper fields, the real one will be set in the validation phase
            variadic_field_name = 'variadic_argv'
            variadic_count_field_name = 'variadic_argc'

            self.context.aux_var(variadic_field_name, "char **")
            self.context.aux_var(variadic_count_field_name, "int")

            self.positional_action_map.add(self.cur_position, cur_command_idx, "aux->{0} = &argv[i];".format(variadic_field_name))
            self.positional_action_map.add(self.cur_position, cur_command_idx, "aux->{0} = argc - i;".format(variadic_count_field_name))
            self.positional_action_map.add(self.cur_position, cur_command_idx, "break;")
        else:
            self.context.cli_var(field_name, "char *")

            # Use helper fields, the real one will be set in the validation phase
            positional_field_name = 'positional{0}'.format(self.cur_position)
            self.context.aux_var(positional_field_name, "char *")

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

################################################################################

class Backend(object):
    def __init__(self):
        #type: () -> None
        pass

    def write_variables(self, gf, variables):
        #type: (GenFile, Variables) -> None
        pass

    def write_block(self, gf, block):
        # type: (GenFile, Block) -> None
        """Write the given block and its possible descendents to the file"""
        pass

    def write_multiline_comment(self, gf, comment):
        # type: (GenFile, str) -> None
        pass

################################################################################

def expand_var(var):
    # type: (Variable) -> str
    t = var.vtype
    space = ' '
    if t.endswith('*'):
        space = ''
    return '{0}{1}{2}'.format(t, space, var.name)

class CBackend(Backend):
    def __init__(self):
        #type: () -> None
        super(CBackend, self).__init__()

    def write_variables(self, gf, variables):
        #type: (GenFile, Variables) -> None
        sorted_field_names = sorted([k for k in variables.variables])

        gf.writeline("struct {0}".format(variables.name))
        gf.writeline("{")
        for k in sorted_field_names:
            gf.writeline("{0};".format(expand_var(variables.variables[k])))
        gf.writeline("};")

    def write_block(self, gf, block):
        # type: (GenFile, Block) -> None
        """Write the given block and its possible descendents to the file"""

        if isinstance(block, Function):
            inputs = [] # type: List[str]
            for i in block.input:
                inputs.append(expand_var(i))
            gf.writeline("{0} {1}({2})".format(block.output, block.name, ", ".join(inputs)))
            gf.writeline('{')
        elif isinstance(block, Block):
            gf.writeline('{')

        for vname in block.locals.variables:
            v = block.locals[vname]
            vtype = v.vtype
            if not vtype.endswith('*'):
                vtype = vtype + " "
            if v.init is not None:
                gf.writeline("{0}{1} = {2};".format(vtype, vname, v.init))
            else:
                gf.writeline("{0}{1};".format(vtype, vname))

        for l in block.generated_code:
            if isinstance(l, IfStatement):
                gf.writeline('if ({0})'.format(l.cond)) # FIXME: This should involve the backend
                self.write_block(gf, l.then)
                if l.otherwise is not None and len(l.otherwise.generated_code) != 0:
                    gf.writeline('else')
                    self.write_block(gf, l.otherwise)
            elif isinstance(l, Statement):
                gf.writeline(repr(l)) # FIXME: This should involve the backend
            elif isinstance(l, Block):
                self.write_block(gf, l)
            elif isinstance(l, Function):
                self.write_block(gf, l)

        if isinstance(block, Function) or isinstance(block, Block):
            gf.writeline('}')

    def write_multiline_comment(self, gf, comment):
        # type: (GenFile, str) -> None
        """Write a multiline comment to the given file"""
        comment = textwrap.dedent(comment)
        gf.writeline("/**")
        for l in comment.split("\n"):
            l = l.strip()
            if len(l) != 0:
                gf.writeline(" * " + l)
            else:
                gf.writeline(" *")
        gf.writeline(" */")

################################################################################

def genopts(patterns):
    # type: (List[str])->None
    parse_trees = [parse_pattern(p.strip()) for p in patterns]
    template = Template(parse_trees)
    #print(template)

    context = GeneratorContext()
    navigate(template, GenerateParserVisitor(context))

    cur_command = context.cur_command_var
    cur_position = V('cur_position', 'int', '0')

    if "--help" not in context.token_action_map:
        help = LValue("cli", context.cli_var("help", "int"))
        help_cmd = LValue("aux", context.aux_var("help_cmd", "int"))

        context.token_action_map.add("--help", help << 1) # << means assignment
        context.token_action_map.add("--help", help_cmd << cur_command) # << means assignment

    option_with_args = [] # type: List[OptionWithArg]
    all_commands = [] # type: List[Tuple[List[Command], List[Arg], Set[str]]]
    navigate(template, OptionWithArgExtractorVisitor(True, option_with_args))
    navigate(template, CommandListExtractorVisitor(all_commands))

    gf = GenFile()

    backend = CBackend()

    backend.write_multiline_comment(gf, "Automatically generated file, please don't edit!")

    gf.writeline("#include <stdio.h>")
    gf.writeline("#include <string.h>")
    gf.writeline()

    backend.write_variables(gf, context.cli_vars)
    gf.writeline()
    backend.write_variables(gf, context.aux_vars)
    gf.writeline()

    gf.writeline("typedef enum")
    gf.writeline("{")
    gf.writeline("POF_VALIDATE = (1<<0),")
    gf.writeline("POF_USAGE = (1<<1)")
    gf.writeline("} parse_cli_options_t;")
    gf.writeline()

    # Generates the validation function
    vc = Function(
        output="static int",
        name="validate_cli",
        input=[V('cli', 'struct cli *'), V('aux', 'struct cli_aux *')])
    vc.add("if (cli->help)")
    vc.add("{")
    vc.ret(1)
    vc.add("}")
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
        vc.add("{0} ({1})".format("if" if first else "else if", " && ".join(conds)))
        vc.add("{")

        all_args = commands[1] # type: List[Arg]
        optional_args = commands[2] # type: Set[str]

        # FIXME: Generalize
        if not any(a.variadic for a in all_args) and len(all_args) == 2 and len(optional_args) == 1 and all_args[0].command in optional_args:
            vc.add("if (aux->positional{0} != NULL)".format(1))
            vc.add("{")
            for pos, arg in enumerate(commands[1]):
                vc.add("cli->{0} = aux->positional{1};".format(makecname(arg.command), pos))
            vc.add("}")
            vc.add("else")
            vc.add("{")
            vc.add("cli->{0} = aux->positional{1};".format(makecname(all_args[1].command), 0))
            vc.add("}")
        else:
            # Resolve positional arguments
            for pos, arg in enumerate(commands[1]):
                if arg.variadic:
                    vc.add("cli->{0}_count = aux->variadic_argc;".format(makecname(arg.command)))
                    vc.add("cli->{0} = aux->variadic_argv;".format(makecname(arg.command)))
                else:
                    vc.add("cli->{0} = aux->positional{1};".format(makecname(arg.command), pos))

        for a in all_args:
            if a.command not in optional_args:
                vc.add("if (!cli->{0})".format(makecname(a.command)))
                vc.add("{")
                vc.add("fprintf(stderr, \"Required argument \\\"{0}\\\" is missing. Use --help for usage\\n\");".format(a.command))
                vc.ret(0)
                vc.add("}")

        vc.add("}")
        first = False
    if not first:
        vc.add("else")
        vc.add("{")
        vc.add('fprintf(stderr,"Please specify a proper command. Use --help for usage.\\n");')
        vc.ret(0)
        vc.add("}")

    vc.ret(1)
    backend.write_block(gf, vc)

    gf.writeline()
    backend.write_multiline_comment(gf, """
        Print usage for the given cli.

        @return 1 if usage has been printed, 0 otherwise.
        """)

    uc = Function(
        output="static int",
        name = "usage_cli",
        input = [V('cmd', 'char *'), V('cli', 'struct cli *')])

    uc.add("if (!cli->help)")
    uc.add("{")
    uc.ret(0)
    uc.add("}")
    uc.add('fprintf(stderr, "usage: %s <command> [<options>]\\n", cmd);'.format(patterns[0].strip()))
    for pattern in sorted(patterns):
        uc.add('fprintf(stderr, "{0}\\n");'.format(pattern.strip()))
    uc.ret(1)
    backend.write_block(gf, uc)

    # Generate a function that parses the command line and populates
    # the struct cli. It does not yet make verification
    gf.writeline()

    # Construct parse_cli_simple() function
    pcs = Function(
        output="static int",
        name="parse_cli_simple",
        input=[V('argc', 'int'), V('argv', 'char **'), V('cli', 'struct cli *'), V('aux', 'struct cli_aux *')])

    pcs.locals.add('i', 'int')
    pcs.locals.add_var(cur_command)
    pcs.locals.add_var(cur_position)

    pcs.add("for (i=0; i < argc; i++)")
    pcs.add("{")

    context.token_action_map.write(pcs)
    context.positional_action_map.write(pcs)

    pcs.add("else")
    pcs.add("{")
    pcs.add('fprintf(stderr,"Unknown command or option \\"%s\\"\\n\", argv[i]);')
    pcs.ret(0)
    pcs.add("}")
    pcs.add("}")
    pcs.ret(1)
    backend.write_block(gf, pcs)

    gf.writeline()

    backend.write_multiline_comment(gf, """
        Parse the given arguments and fill the struct cli accordingly.

        @param argc as in main()
        @param argv as in main()
        @param cli the filled struct
        @param opts some options to modify the behaviour of the function.
        @return 1 if parsing was successful, 0 otherwise.
        """)

    pc = Function(
        output="static int",
        name="parse_cli",
        input=[V('argc', 'int'), V('argv', 'char **'), V('cli', 'struct cli *'), V('opts', 'parse_cli_options_t')])

    pc.locals.add("aux", "struct cli_aux")
    pc.locals.add("cmd", "char *", "argv[0]")
    pc.add("memset(&aux, 0, sizeof(aux));")
    pc.add("argc--;")
    pc.add("argv++;")
    pc.iff(cond="!parse_cli_simple(argc, argv, cli, &aux)").then.ret(0)
    pc.iff(cond="opts & POF_VALIDATE").then. \
        iff(cond="!validate_cli(cli, &aux)").then.ret(0)
    pc.iff(cond="opts & POF_USAGE").then.add("return !usage_cli(cmd, cli);")
    pc.ret(1)
    backend.write_block(gf, pc)

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
