from __future__ import print_function

import collections

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
