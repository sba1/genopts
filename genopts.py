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

if False: # For MyPy, see https://stackoverflow.com/questions/446052/how-can-i-check-for-python-version-in-a-program-that-uses-new-language-features
    from typing import TypeVar

    # For generic self inBlock
    T = TypeVar('T', bound='Block')

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

class ExpressionStatement(Statement):
    """A statement that consist of an expression"""
    def __init__(self, expr):
        # type: (Expression) -> None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return repr(self.expr) + ";"

class ReturnStatement(Statement):
    """A return statement emits an instruction to exit a function execution"""
    def __init__(self, expr):
        # type: (Expression) -> None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return "return {0};".format(repr(self.expr))

class BreakStatement(Statement):
    """A break statement emits an instruction to leave the most inner loop quickly"""
    def __init__(self):
        # type: () -> None
        pass

    def __repr__(self):
        # type: () -> str
        return "break;"

class PrintErrorStatement(Statement):
    """A statement to print an error message"""
    def __init__(self, msg, *args):
        # type: (str, Expression) -> None
        self.msg = msg
        self.args = args

    def __repr__(self):
        # type: () -> str
        args = ""
        if len(self.args):
            args = ", " + ", ".join([repr(e) for e in self.args])
        return "fprintf(stderr, \"{0}\"{1});".format(self.msg, args)

class IfStatement(Statement):
    def __init__(self, cond, then, otherwise=None):
        # type: (Expression, ThenBlock, Block) -> None
        self.cond = cond
        self.then = then
        self.otherwise = otherwise

class Expression:
    def __lshift__(self, other):
        # type: (Union[Expression, str, int]) -> AssignmentExpression
        return AssignmentExpression(self, make_expr(other))

    def __lt__(self, other):
        # type: (Union[Expression, str, int]) -> BinaryExpression
        return BinaryExpression(self, '<', make_expr(other))

    def __gt__(self, other):
        # type: (Union[Expression, str, int]) -> BinaryExpression
        return BinaryExpression(self, '>', make_expr(other))

    def __add__(self, other):
        # type: (Union[Expression, str, int]) -> BinaryExpression
        return BinaryExpression(self, '+', make_expr(other))

    def __sub__(self, other):
        # type: (Union[Expression, str, int]) -> BinaryExpression
        return BinaryExpression(self, '-', make_expr(other))

    # No proper overloading for now
    def eq(self, other):
        # type: (Union[Expression, str, int]) -> BinaryExpression
        return BinaryExpression(self, '==', make_expr(other))

    def eq_str(self, other):
        # type: (Union[Expression, str]) -> EqualsStrExpression
        if not isinstance(other, Expression):
            other = '"' + other + '"'
        return EqualsStrExpression(self, make_expr(other))

    # No proper overloading for now
    def ne(self, other):
        # type: (Union[Expression, str, int]) -> BinaryExpression
        return BinaryExpression(self, '!=', make_expr(other))

    def access(self, other):
        # type: (Variable) -> AccessMemberExpression
        return AccessMemberExpression(self, repr(other))

    def slice(self, index):
        # type: (Expression) -> SliceExpression
        return SliceExpression(self, index)

    def __getitem__(self, key):
        # type: (Union[int, Expression]) -> VectorElementExpression
        if isinstance(key, int):
            expr = DirectExpression(str(key)) # type: Expression
        else:
            expr = key;
        return VectorElementExpression(self, expr)

class AssignmentExpression(Expression):
    def __init__(self, left, right):
        # type: (Expression, Expression) -> None
        self.left = left
        self.right = right

    def __repr__(self):
        # type: () -> str
        return repr(self.left) + " = " + repr(self.right)

class BinaryExpression(Expression):
    def __init__(self, left, rel, right):
        # type: (Expression, str, Expression) -> None
        self.left = left
        self.rel = rel
        self.right = right

    def __repr__(self):
        # type: () -> str
        return '(' + repr(self.left) + ') ' + self.rel + ' (' + repr(self.right) + ')'

class SliceExpression(Expression):
    def __init__(self, expr, start_index):
        # type: (Expression, Expression) -> None
        self.expr = expr
        self.start_index = start_index

    def __repr__(self):
        # type: () -> str
        return '&' + repr(self.expr) + '[' + repr(self.start_index) + ']'

class DirectExpression(Expression):
    def __init__(self, expr):
        # type: (str) -> None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return self.expr

def make_expr(expr):
    # type: (Union[str, int, Expression]) -> Expression
    if expr is None:
        return None
    if isinstance(expr, Expression):
        return expr
    else:
        return DirectExpression(str(expr))

class AccessMemberExpression(Expression):
    def __init__(self, obj, member):
        # type: (Expression, str) -> None
        self.obj = obj
        self.member = member

    def __repr__(self):
        # type: () -> str
        return repr(self.obj) + "->" + self.member

def AccessMember(obj, member):
    # type: (Union[str, Expression], str) -> AccessMemberExpression
    return AccessMemberExpression(make_expr(obj), member)

class IsFalseExpression(Expression):
    def __init__(self, expr):
        # type: (Expression) -> None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return "!"  + repr(self.expr)

class EqualsStrExpression(Expression):
    def __init__(self, arg1, arg2):
        # type: (Expression, Expression) -> None
        self.arg1 = arg1
        self.arg2 = arg2

    def __repr__(self):
        # type: () -> str
        return "!strcmp({0}, {1})".format(repr(self.arg1), repr(self.arg2))

def IsFalse(expr):
    # type: (Union[str, Expression]) -> IsFalseExpression
    return IsFalseExpression(make_expr(expr))

class Variable(Expression):
    def __init__(self, name, vtype, init = None):
        # type: (str, str, Union[Expression,str]) -> None
        self.name = name
        self.vtype = vtype
        self.init = make_expr(init)

    def __repr__(self):
         # type: () -> str
         return self.name

# Shortcut
V = Variable

class VectorElementExpression(Expression):
    def __init__(self, expr, element):
        # type: (Expression, Expression) -> None
        self.expr = expr
        self.element = element

    def __repr__(self):
        # type: () -> str
        return repr(self.expr) + "[" + repr(self.element) + "]"

class PostIncrementExpression(Expression):
    def __init__(self, expr):
        # type: (Expression) ->None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return repr(self.expr) + "++"

class PostDecrementExpression(Expression):
    def __init__(self, expr):
        # type: (Expression) ->None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return repr(self.expr) + "--"


class Variables:
    """An abstraction of run time variabels needed during parsing."""
    def __init__(self, name = None):
        # type: (str) -> None
        self.variables = dict() # type: Dict[str, Variable]
        self.name = name

    def add(self, name, vtype, init = None):
        # type: (str, str, Union[Expression,str]) -> Variable
        v = Variable(name, vtype, init)
        self.variables[name] = v
        return v

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
        # type: (T, Union[str, Function, Block, Statement, Expression]) -> T
        if isinstance(node, basestring):
            node = DirectStatement(node)
        elif isinstance(node, Expression):
            node = ExpressionStatement(node)
        self.generated_code.append(node)
        return self

    def printerr(self, msg, *args):
        # type: (T, str, Expression) -> T
        self.generated_code.append(PrintErrorStatement(msg, *args))
        return self

    def ret(self, expr):
        # type: (T, Union[int, str, Expression]) -> T
        if isinstance(expr, int):
            expr = str(expr) # FIXME: Use an int literal
        self.add(ReturnStatement(make_expr(expr)))
        return self

    def inc(self, expr):
        # type: (T, Expression) -> T
        self.add(ExpressionStatement(PostIncrementExpression(expr)))
        return self

    def dec(self, expr):
        # type: (T, Expression) -> T
        self.add(ExpressionStatement(PostDecrementExpression(expr)))
        return self

    def iff(self, cond):
        # type: (Union[str,Expression]) -> IfStatement
        otherwise = Block()
        then = ThenBlock(otherwise)
        if isinstance(cond, Expression):
            if_then_else = IfStatement(cond, then, otherwise)
        else:
            if_then_else = IfStatement(DirectExpression(cond), then, otherwise)
        self.add(if_then_else)
        return if_then_else

    def brk(self):
        # type: () -> None
        self.add(BreakStatement())

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
        self.description = None # type: str

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

        conds = DirectExpression(" + ".join("!!cli->{0}".format(makename(cmd)) for cmd in self.cmds))
        opts = [cmd.command for cmd in self.cmds]
        self.b.iff(conds > 1).then. \
            printerr("Only one of {0} may be given\\n".format(join_enum(opts, "or"))). \
            ret(0)

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

        b.iff(cond="aux->{0} != 0 && {1}".format(cur_command_name, " && ".join(conds))).then. \
            printerr("Option {0} may be given only for the {1}\\n".format(n.command, valid_commands_text)). \
            ret(0)

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
    def __init__(self, context):
        # type: (GeneratorContext) -> None
        self.context = context
        self.token_action_map = dict() # type: Dict[str,Block]
        self.token_requires_arg = set() # type: Set[str]

    def __contains__(self, item):
        # type: (str) -> bool
        return item in self.token_action_map

    def add(self, token, action=None, requires_arg=False):
        # type: (str, Union[str, Expression, Statement], bool) -> Block
        if token not in self.token_action_map:
            self.token_action_map[token] = Block()
        if action is not None:
            self.token_action_map[token].add(action)
        if requires_arg:
            self.token_requires_arg.add(token)
        return self.token_action_map[token]

    def write(self, b):
        # type: (Block) -> None
        sorted_tokens = sorted([t for t in self.token_action_map])

        then = None # type: ThenBlock
        first = True
        argv = self.context.backend.argv
        i = self.context.i_var
        for token in sorted_tokens:
            if first:
                parent_b = b
                first = False
            else:
                parent_b = then.otherwise()

            if token in self.token_requires_arg:
                token_len = len(token)
                then = parent_b.iff(make_expr('!strncmp("{0}", argv[i], {1}) && (argv[i][{1}]==\'=\' || !argv[i][{1}])'.format(token, token_len - 1 ))).then
            else:
                then = parent_b.iff(argv(i).eq_str(token)).then

            for s in self.token_action_map[token].generated_code:
                then.add(s)


class PositionalActionMap:
    """
    Instances of this class represent positional arguments and their actions.
    """
    def __init__(self):
        # type: () -> None
        self.action_map = [] # type: List[Dict[int,Block]]
        self.last_is_variadic = False

    def add(self, pos, cmd_idx, action=None, variadic=False):
        # type: (int, int, Union[str, Expression, Statement], bool) -> Block
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
        if action is not None:
            self.action_map[pos][cmd_idx].add(action)
        self.last_is_variadic = variadic
        return self.action_map[pos][cmd_idx]

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
    def __init__(self, backend):
        # type: (Backend) -> None
        self.backend = backend
        self.cli_vars = Variables("cli")
        self.aux_vars = Variables("cli_aux")
        self.cur_command_var = Variable("cur_command", "int", "-1")
        self.cur_position_var = Variable('cur_position', 'int', '0')
        self.parent_map = ParentMap()
        self.command_index_map = CommandIndexMap()
        self.token_action_map = TokenActionMap(self)
        self.positional_action_map = PositionalActionMap()

        # Variables/Parameters used in some functions
        self.cli_arg_var = V('cli', 'struct cli *')
        self.aux_arg_var = V('aux', 'struct cli_aux *')

        self.i_var = V('i', 'int')

    def cli_var(self, name, vtype):
        # type: (str, str) -> Variable
        if vtype != None:
            self.cli_vars.add(name, vtype)
        return self.cli_vars[name]

    def aux_var(self, name, vtype):
        # type: (str, str) -> Variable
        if vtype != None:
            self.aux_vars.add(name, vtype)
        return self.aux_vars[name]

    def cli_access(self, name, type = None):
        # type: (str, str) -> Expression
        return self.cli_arg_var.access(self.cli_var(name, type))

    def aux_access(self, name, type = None):
        # type: (str, str) -> Expression
        return self.aux_arg_var.access(self.aux_var(name, type))

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
        self.cli_arg_var = context.cli_arg_var
        self.aux_arg_var = context.aux_arg_var

        # Start with 1 in case there options without commands and 0 means not
        # initialized
        self.cur_command = None # type: Command

        # Number of current positional argument
        self.cur_position = 0

    def remember_pos(self, token, field_name):
        # type: (str, str) -> None
        cur_command_name = field_name + "_cmd"
        aux_access = self.context.aux_access
        cur_command_var = self.context.cur_command_var
        self.token_action_map.add(token, aux_access(cur_command_name, "int") << cur_command_var)

    def visit_command(self, n):
        # type: (Command) -> None
        cmd = n.command
        cmd_requires_arg = n.arg != None

        cli_access = self.context.cli_arg_var.access
        aux_access = self.context.aux_arg_var.access

        field_name = makename(n)
        pos_name = field_name + "_pos"

        field_var = self.context.cli_var(field_name, "int")
        pos_var = self.context.aux_var(pos_name, "int")
        cur_command_var = self.context.cur_command_var
        arg_var = None # type: Variable
        i = self.context.i_var

        if cmd_requires_arg:
            arg_var = self.context.cli_var(makecname(n.arg), "char *")

        # Remember parent
        self.parent_map.add_command(n, self.cur_command)

        # This was a proper command, level up command index
        self.cur_command = n
        cur_command_idx = self.command_index_map.map(n)

        argv = self.context.backend.argv
        argc = self.context.backend.argc()

        if cmd not in self.token_action_map:
            self.token_action_map.add(cmd, cli_access(field_var) << 1, cmd_requires_arg)
            self.token_action_map.add(cmd, aux_access(pos_var) << i, cmd_requires_arg)
            self.token_action_map.add(cmd, cur_command_var << cur_command_idx, cmd_requires_arg)

            if cmd_requires_arg:
                self.token_action_map.add(cmd, "")
                if_no_direct_arg = self.token_action_map.add(cmd).iff(cond="!argv[i][{0}]".format(len(cmd) - 1)).then
                if_no_direct_arg.iff(i + 1 < argc).then. \
                    add(cli_access(arg_var) << argv(i + 1)). \
                    inc(i).\
                    otherwise(). \
                    printerr("Argument \\\"{0}\\\" requires a value\\n".format(cmd)). \
                    ret(0)
                if_no_direct_arg.otherwise().add(cli_access(arg_var) << argv(i).slice(make_expr(len(cmd))))

    def visit_option_with_arg(self, n):
        # type: (OptionWithArg) -> None

        cli = self.context.cli_access
        argv = self.context.backend.argv
        i = self.context.i_var

        # Remember parent
        self.parent_map.add_option(n, self.cur_command)

        option = n.command

        # Write token action if not already done before
        if option not in self.token_action_map:
            field_name = makename(n)
            if n.arg == None:
                self.token_action_map.add(option, cli(field_name, "int") << 1)
            else:
                self.token_action_map.add(option, "if (++i == argc) break;")
                self.token_action_map.add(option, cli(field_name, "char *") << argv(i))

            self.remember_pos(option, field_name)

    def visit_arg(self, n):
        # type: (Arg) -> None
        field_name = makecname(n.command)
        cur_command_idx = self.command_index_map.map(self.cur_command)

        aux = self.context.aux_access
        argc = self.context.backend.argc()
        argv = self.context.backend.argv
        i = self.context.i_var

        if n.variadic:
            count_field_name = field_name + "_count";

            self.context.cli_var(field_name, "char **")
            self.context.cli_var(count_field_name, "int")

            # Use helper fields, the real one will be set in the validation phase
            variadic_field_name = 'variadic_argv'

            self.context.aux_var(variadic_field_name, "char **")

            self.positional_action_map.add(self.cur_position, cur_command_idx). \
                add(aux(variadic_field_name) << argv().slice(i)). \
                add(aux("variadic_argc", "int") << argc - i). \
                brk()
        else:
            self.context.cli_var(field_name, "char *")

            # Use helper fields, the real one will be set in the validation phase
            positional_field_name = 'positional{0}'.format(self.cur_position)

            self.positional_action_map.add(self.cur_position, cur_command_idx). \
                add(aux(positional_field_name, "char *") << argv(i)). \
                inc(self.context.cur_command_var)

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
        # type: () -> None
        pass

    def write_variables(self, gf, variables):
        # type: (GenFile, Variables) -> None
        pass

    def write_header(self, gf):
        # type: (GenFile) -> None
        pass

    def write_footer(self, gf):
        # type: (GenFile) -> None
        pass

    def write_block(self, gf, block):
        # type: (GenFile, Block) -> None
        """Write the given block and its possible descendents to the file"""
        pass

    def write_multiline_comment(self, gf, comment):
        # type: (GenFile, str) -> None
        pass

    def write_print_statement(self, gf, msg, args):
        # type: (GenFile, str, List[str]) -> None
        pass

    def argc(self):
        # type: () -> Expression
        """Generate an expression to get the argc"""
        pass

    def argv(self, index = None):
        # type: (Union[int, Expression]) -> Expression
        """Generate an expression to get the index'th argument"""
        pass

################################################################################

class AddressOfExpression(Expression):
    def __init__(self, expr):
        # type: (Expression) -> None
        self.expr = expr

    def __repr__(self):
        # type: () -> str
        return "&" + repr(self.expr)

################################################################################

def expand_var(var):
    # type: (Variable) -> str
    t = var.vtype
    space = ' '
    if t.endswith('*'):
        space = ''
    return '{0}{1}{2}'.format(t, space, var.name)

class CLikeMultilineCommentsBackend(Backend):
    def __init__(self):
        # type: () -> None
        super(CLikeMultilineCommentsBackend, self).__init__()

    def expand_var(self, var):
        # type: (Variable) -> str
        return expand_var(var)

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

class CBackend(CLikeMultilineCommentsBackend):
    def __init__(self):
        # type: () -> None
        super(CBackend, self).__init__()

    def write_header(self, gf):
        # type: (GenFile) -> None
        gf.writeline("#include <stdio.h>")
        gf.writeline("#include <string.h>")
        gf.writeline()

    def write_variables(self, gf, variables):
        # type: (GenFile, Variables) -> None
        sorted_field_names = sorted([k for k in variables.variables])

        gf.writeline("struct {0}".format(variables.name))
        gf.writeline("{")
        for k in sorted_field_names:
            gf.writeline("{0};".format(expand_var(variables.variables[k])))
        gf.writeline("};")

    def write_if(self, gf, iff, otherwise=False):
        # type: (GenFile, IfStatement, bool) -> None
        """Write a if statement, possibly connecting it with a previous else case"""
        gf.writeline('{0}if ({1})'.format("else " if otherwise else "", iff.cond)) # FIXME: This should involve the backend
        self.write_block(gf, iff.then)
        if iff.otherwise is not None and len(iff.otherwise.generated_code) != 0:
            if len(iff.otherwise.generated_code) == 1 and isinstance(iff.otherwise.generated_code[0], IfStatement):
                self.write_if(gf, iff.otherwise.generated_code[0], True)
            else:
                gf.writeline('else')
                self.write_block(gf, iff.otherwise)

    def write_block(self, gf, block):
        # type: (GenFile, Block) -> None
        """Write the given block and its possible descendents to the file"""

        if isinstance(block, Function):
            inputs = [] # type: List[str]
            if block.description is not None:
                self.write_multiline_comment(gf, block.description)

            for i in block.input:
                inputs.append(self.expand_var(i))
            gf.writeline("{0} {1}({2})".format(block.output, block.name, ", ".join(inputs)))
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
                self.write_if(gf, l)
            elif isinstance(l, DirectStatement):
                gf.writeline(l.st)
            elif isinstance(l, ReturnStatement):
                gf.writeline("return {0};".format(self.translate(l.expr)))
            elif isinstance(l, PrintErrorStatement):
                self.write_print_statement(gf, l.msg, [repr(e) for e in l.args])
            elif isinstance(l, ExpressionStatement):
                gf.writeline("{0};".format(self.translate(l.expr)))
            elif isinstance(l, Statement):
                gf.writeline(repr(l)) # FIXME: This should involve the backend
            elif isinstance(l, Block):
                self.write_block(gf, l)
            elif isinstance(l, Function):
                self.write_block(gf, l)

        gf.writeline('}')

    def write_print_statement(self, gf, msg, args):
        # type: (GenFile, str, List[str]) -> None
        cargs = ""
        if len(args):
            cargs = ", " + ", ".join(args)
        gf.writeline("fprintf(stderr, \"{0}\"{1});".format(msg, cargs))

    def translate(self, expr):
        # type: (Expression) -> str
        """Translates the given expresison to the langauage"""
        # TODO: Write proper translator
        return repr(expr)

    def argc(self):
        # type: () -> Expression
        return V('argc', 'int')

    def argv(self, index = None):
        # type: (Union[int, Expression]) -> Expression
        v = V('argv', 'char **')
        if index is None:
            return v
        return v[index]

################################################################################

def expand_java_var(var):
    # type: (Variable) -> str
    t = var.vtype
    space = ' '
    if t == 'char *':
        t = 'String'
    elif t == 'char **':
        t = 'String []'
    elif t.startswith('struct ') and t.endswith('*'):
        t = t[7:-2]
    return '{0}{1}{2}'.format(t, space, var.name)


# TODO: For now we inherit from CBackend and overwrite some methods, we will
# change that later
class JavaBackend(CBackend):
    def __init__(self):
        # type: () -> None
        super(JavaBackend, self).__init__()

    def expand_var(self, var):
        # type: (Variable) -> str
        return expand_java_var(var)

    def write_header(self, gf):
        # type: (GenFile) -> None
        gf.writeline("public class CliParser")
        gf.writeline("{")

    def write_footer(self, gf):
        # type: (GenFile) -> None
        gf.writeline("}")

    def write_variables(self, gf, variables):
        # type: (GenFile, Variables) -> None
        sorted_field_names = sorted([k for k in variables.variables])

        gf.writeline("public static class {0}".format(variables.name))
        gf.writeline("{")
        for k in sorted_field_names:
            gf.writeline("{0};".format(expand_java_var(variables.variables[k])))
        gf.writeline("};")

    def write_print_statement(self, gf, msg, args):
        # type: (GenFile, str, List[str]) -> None
        cargs = ""
        if len(args):
            cargs = ", " + ", ".join(args)
        gf.writeline("System.err.print(\"{0}\"{1});".format(msg, cargs))

    def translate(self, expr):
        # type: (Expression) -> str
        """Translates the given expresison to the langauage"""
        if isinstance(expr, AccessMemberExpression):
            return '{0}.{1}'.format(self.translate(expr.obj), expr.member)
        elif isinstance(expr, AssignmentExpression):
            return '{0} = {1}'.format(self.translate(expr.left), self.translate(expr.right))
        else:
            return repr(expr)

################################################################################

def genopts(patterns, backend):
    # type: (List[str], Backend)->None
    parse_trees = [parse_pattern(p.strip()) for p in patterns]
    template = Template(parse_trees)
    #print(template)

    context = GeneratorContext(backend)
    cli_var = context.cli_arg_var
    cli_access = context.cli_access
    aux_var = context.aux_arg_var
    aux_access = context.aux_access
    navigate(template, GenerateParserVisitor(context))

    cur_command = context.cur_command_var
    cur_position = context.cur_position_var

    if "--help" not in context.token_action_map:
        help = cli_access("help", "int")
        help_cmd = aux_access("help_cmd", "int")

        # << means assignment
        context.token_action_map.add("--help").\
            add(help << 1).\
            add(help_cmd << cur_command)

    option_with_args = [] # type: List[OptionWithArg]
    all_commands = [] # type: List[Tuple[List[Command], List[Arg], Set[str]]]
    navigate(template, OptionWithArgExtractorVisitor(True, option_with_args))
    navigate(template, CommandListExtractorVisitor(all_commands))

    gf = GenFile()

    backend.write_multiline_comment(gf, "Automatically generated file, please don't edit!")

    backend.write_header(gf)

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
        input=[cli_var, aux_var])
    vc.iff(cli_access("help")).then.ret(1)
    write_command_validation(vc, context.command_index_map, context.parent_map, option_with_args)
    navigate(template, GenerateMXValidatorVisitor(vc))

    # Determine the maximal number of commands for all patterns
    max_commands = max(len(context.command_index_map.map_list(key[0])) for key in all_commands)

    def all_commands_key(key):
        # type: (Tuple[List[Command], List[Arg], Set[str]]) -> List[int]
        """
        The function that turns a Tuple into a key that is suitable for sorting.
        We basical return the int list mapped from the commands filled up with
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
            # Resolve cases with optional first positional arguments, for now
            # only in case of two arguments, e.g., [optional] required

            # Check if second positional arg has been set
            then = vc.iff(aux_access("positional1")).then

            # In this case, we can assign them as indented, i.e., subsequently
            for pos, arg in enumerate(commands[1]):
                cmd_name = makecname(arg.command)

                then.add(cli_access(cmd_name) << aux_access("positional{0}".format(pos)))

            # But if the second positional arg is not set, the actual first given
            # positional arg is meant to be the second positional one in the template
            then.otherwise().add(cli_access(makecname(all_args[1].command)) << aux_access("positional0"))
        else:
            # Resolve positional arguments
            for pos, arg in enumerate(commands[1]):
                cmd_name = makecname(arg.command)

                if arg.variadic:
                    vc.add(cli_access(cmd_name + "_count") << aux_access("variadic_argc"))
                    vc.add(cli_access(cmd_name) << aux_access("variadic_argv"))
                else:
                    vc.add(cli_access(cmd_name) << aux_access("positional{0}".format(pos)))

        for a in all_args:
            if a.command not in optional_args:
                vc.iff(IsFalse(cli_access(makecname(a.command)))).then. \
                    printerr("Required argument \\\"{0}\\\" is missing. Use --help for usage\\n".format(a.command)). \
                    ret(0)

        vc.add("}")
        first = False
    if not first:
        vc.add("else")
        vc.add("{")
        vc.printerr('Please specify a proper command. Use --help for usage.\\n')
        vc.ret(0)
        vc.add("}")

    vc.ret(1)
    backend.write_block(gf, vc)

    gf.writeline()

    cmd_var = V('cmd', 'char *')
    uc = Function(
        output="static int",
        name = "usage_cli",
        input = [cmd_var, V('cli', 'struct cli *')])
    uc.description = """
        Print usage for the given cli.

        @return 1 if usage has been printed, 0 otherwise.
        """

    uc.iff(IsFalse(cli_access("help", "int"))).then.ret(0)
    uc.printerr("usage: %s <command> [<options>]\\n", cmd_var)
    for pattern in sorted(patterns):
        uc.printerr("{0}\\n".format(pattern.strip()))
    uc.ret(1)
    backend.write_block(gf, uc)

    # Generate a function that parses the command line and populates
    # the struct cli. It does not yet make verification
    gf.writeline()

    argc_var = V('argc', 'int')
    argv_var = V('argv', 'char **')

    # Construct parse_cli_simple() function
    pcs = Function(
        output="static int",
        name="parse_cli_simple",
        input=[argc_var, argv_var, cli_var, aux_var])

    i_var = context.i_var
    pcs.locals.add_var(i_var)
    pcs.locals.add_var(cur_command)
    pcs.locals.add_var(cur_position)

    pcs.add("for (i=0; i < argc; i++)")
    pcs.add("{")

    context.token_action_map.write(pcs)
    context.positional_action_map.write(pcs)

    pcs.add("else")
    pcs.add("{")
    pcs.printerr('Unknown command or option \\"%s\\"\\n', backend.argv(i_var))
    pcs.ret(0)
    pcs.add("}")
    pcs.add("}")
    pcs.ret(1)
    backend.write_block(gf, pcs)

    gf.writeline()

    opts_var = V('opts', 'parse_cli_options_t')
    pc = Function(
        output="static int",
        name="parse_cli",
        input=[argc_var, argv_var, cli_var, opts_var])
    pc.description = """
        Parse the given arguments and fill the struct cli accordingly.

        @param argc as in main()
        @param argv as in main()
        @param cli the filled struct
        @param opts some options to modify the behaviour of the function.
        @return 1 if parsing was successful, 0 otherwise.
        """

    aux_var = pc.locals.add("aux", "struct cli_aux", "{0}")
    cmd_var = pc.locals.add("cmd", "char *", argv_var[0])
    pc.dec(argc_var)
    pc.inc(argv_var)
    pc.iff(cond="!parse_cli_simple(argc, argv, cli, &aux)").then.ret(0)
    pc.iff(cond="opts & POF_VALIDATE").then. \
        iff(cond="!validate_cli(cli, &aux)").then.ret(0)
    pc.iff(cond="opts & POF_USAGE").then.ret("!usage_cli(cmd, cli)")
    pc.ret(1)
    backend.write_block(gf, pc)

    gf.writeline()
    backend.write_footer(gf)
    gf.flush()

def main():
    # type: ()->None
    lines = sys.stdin.readlines()
    if len(lines) < 1:
        sys.exit("Input must contain at least one line")
    backend = None # type: Backend
    if len(sys.argv) > 1 and sys.argv[1] == '--java':
        backend = JavaBackend()
    else:
        backend = CBackend()
    genopts(lines, backend)

if __name__ == "__main__":
    main()
