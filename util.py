#!/usr/bin/env python3
# coding=utf-8
# A CLI utility for various Smokey functions

import shutil
import sys
import os
import shlex
from tempfile import mkstemp

import helpers
helpers.log = lambda *args, **kwargs: None  # Override log() for less verbosity
import chatcommands
import findspam
from blacklists import Blacklist


# A utility is "name: (description, func)"
utilities = {}

# map from blacklist names to paths of temp files, to fake modifying them
tmp_blacklist_paths = {}


def utility(name_s, description):
    def wrapper(func):
        global utilities
        if isinstance(name_s, str):
            names = [name_s]
        else:
            names = list(name_s)
        for name in names:
            utilities[name] = (description, func)
        return func
    return wrapper


@utility("bisect", "finds out which blacklist/watchlist item matches a string")
def util_bisect(arg):
    print(chatcommands.bisect.__func__(None, arg) + "\n")


@utility("bisect-number", "finds out which number blacklist/watchlist item matches a number")
def util_bisect_number(arg):
    print(chatcommands.bisect_number.__func__(None, arg) + "\n")


@utility("deobfuscate-number", "homoglyph deobfuscate and normalize a number pattern")
def util_deobfuscate_number(arg):
    print(chatcommands.deobfuscate_number.__func__(None, arg) + "\n")


@utility("normalize-number", "show the number normalizations for a number pattern")
def util_normalize_number(arg):
    print(chatcommands.normalize_number.__func__(None, arg) + "\n")


@utility(["test-question", "test-q"], "test if text would be automatically reported as a question body")
def util_test_question(arg):
    print(chatcommands.test.__func__(arg, alias_used='test-question') + "\n")


@utility(["test-answer", "test-a"], "test if text would be automatically reported as an answer body")
def util_test_answer(arg):
    print(chatcommands.test.__func__(arg, alias_used='test-answer') + "\n")


@utility(["test-user", "test-u"], "test if text would be automatically reported as username")
def util_test_user(arg):
    print(chatcommands.test.__func__(arg, alias_used='test-user') + "\n")


@utility(["test-title", "test-t"], "test if text would be automatically reported as a question title")
def util_test_title(arg):
    print(chatcommands.test.__func__(arg, alias_used='test-title') + "\n")


@utility("test", "test if text would be automatically reported as a post, title, or username")
def util_test(arg):
    print(chatcommands.test.__func__(arg, alias_used='test') + "\n")


@utility(["test-json", "test-j"], "test if post, given in JSON, would be automatically reported")
def util_test_json(arg):
    print(chatcommands.test.__func__(arg, alias_used='test-json') + "\n")


# fake blacklist by copying it to a temporary file, so we can modify it
# blacklist name is the name of a blacklist from blacklists.Blacklist,
# i.e., "KEYWORDS" for blacklists.Blacklist.KEYWORDS
def ensure_blacklist_faked(blacklist_name: str):
    if blacklist_name not in tmp_blacklist_paths:
        # get old blacklist definition
        old_filename, blacklist_parser = getattr(Blacklist, blacklist_name)
        # create temporary file as a copy of the real one
        fd, path = mkstemp(prefix=old_filename)
        os.close(fd)
        shutil.copyfile(getattr(Blacklist, blacklist_name)[0], path)
        tmp_blacklist_paths[blacklist_name] = path
        # update blacklist definition to use temporary file instead of real file
        setattr(Blacklist,
                blacklist_name,
                (path, blacklist_parser))


@utility("blacklist-keyword", "pretend a keyword has been added to the blacklist")
def util_blacklist_keyword(arg):
    ensure_blacklist_faked('KEYWORDS')
    blacklist = Blacklist(Blacklist.KEYWORDS)
    blacklist.add(arg)
    findspam.FindSpam.reload_blacklists()


@utility("blacklist-website", "pretend a website has been added to the blacklist")
def util_blacklist_website(arg):
    ensure_blacklist_faked('WEBSITES')
    blacklist = Blacklist(Blacklist.WEBSITES)
    blacklist.add(arg)
    findspam.FindSpam.reload_blacklists()


@utility("blacklist-username", "pretend a username has been added to the blacklist")
def util_blacklist_username(arg):
    ensure_blacklist_faked('USERNAMES')
    blacklist = Blacklist(Blacklist.USERNAMES)
    blacklist.add(arg)
    findspam.FindSpam.reload_blacklists()


@utility("blacklist-number", "pretend a number has been added to the blacklist")
def util_blacklist_number(arg):
    ensure_blacklist_faked('NUMBERS')
    blacklist = Blacklist(Blacklist.NUMBERS)
    blacklist.add(arg)
    findspam.FindSpam.reload_blacklists()


def unblacklist(pattern):
    for blacklist_name in ['KEYWORDS', 'WEBSITES', 'USERNAMES', 'NUMBERS']:
        exists, _line = Blacklist(getattr(Blacklist, blacklist_name)).exists(pattern)
        if exists:
            ensure_blacklist_faked(blacklist_name)
            Blacklist(getattr(Blacklist, blacklist_name)).remove(pattern)
            return blacklist_name
    return None


@utility("unblacklist", "pretend it has been removed from the blacklists")
def util_unblacklist(s):
    removed_from = unblacklist(s)
    if removed_from is not None:
        print("Removed `{}` from {}.\n".format(s, removed_from))
        findspam.FindSpam.reload_blacklists()
    else:
        print("No such item `{}` in blacklist.\n".format(s))


@utility("exit", "exit this utility (interactive mode)")
def util_exit(_arg=''):
    # delete all temporary blacklist copies
    for path in tmp_blacklist_paths.values():
        os.unlink(path)
    exit()


@utility("help", "display a list of available sub-commands")
def util_help(_arg=''):
    print(command_help_text())


def command_help_text() -> str:
    cmds = [(n, v[0], v[1]) for n, v in utilities.items()]
    maxlen = max([len(x[0]) for x in cmds])
    template = "  {{:{}}}  {{}}".format(maxlen)
    return "List of available commands:\n" + "\n".join([template.format(n, d) for n, d, f in cmds])


def interactive_loop():
    try:
        import readline
    except ImportError:
        pass
    print("Smokey utility\nType \"help\" for a list of commands", file=sys.stderr)
    run_full_commands()


def run_full_commands(file=None, cmd=None):
    """Runs a number of commands from the given file, or interactively

    If file is None, runs interactively.
    If cmd is specified, the command's arguments only will come from file.
    """
    try:
        while True:
            full_cmd = get_full_command(cmd=cmd, file=file)
            if full_cmd:
                run_command(*full_cmd)
    except EOFError:
        pass


def run_command(name, arg):
    if name not in utilities:
        print("Error: function {!r} is not defined".format(name), file=sys.stderr)
        return
    desc, func = utilities[name]
    func(arg)


def get_full_command(file=None, cmd=None):
    """Gets a command from the given file, or interactively

    If file is None, gets the command and argument from interactive input.
    If cmd is specified, the command's argument only will come from file.

    Returns None if the input was blank.
    """
    arg = get_input(file)
    if cmd is None:
        arg_split = arg.split(maxsplit=1)
        if not arg_split:
            return None
        cmd, arg = arg_split[0], arg_split[1] if len(arg_split) > 1 else ''
    if arg and arg[0] in ('"', "'"):
        arg = get_multiline_arg(file, arg)
    return cmd, arg


def get_multiline_arg(file, arg):
    """Continues receiving a multiline argument from the given file, or interactively

    If file is None, gets lines of text from interactive input.
    """
    value_error = None
    try:
        while True:
            try:
                return shlex.join(shlex.split(arg))
            except ValueError as e:
                # Assume we have more input, so don't raise an error yet.
                value_error = e
                arg += "\n" + get_input(file, is_continuation=True)  # continue reading
    except EOFError as e:
        # Raise the ValueError if the argument was not terminated.
        raise value_error if value_error else e


def get_input(file=None, is_continuation=False):
    """Gets a line of input from the given file, or interactively

    If file is None, uses interactive input.
    If is_continuation is True, this is the continuation of a multi-line argument.

    Raises EOFError when there is no more input.
    """
    if file is None:
        return input("> " if is_continuation else "$ ")
    else:
        line = file.readline()
        if line:
            return line.rstrip('\n')
        else:
            raise EOFError


if __name__ == "__main__":
    import argparse

    def file_arg(file_type):
        """For storing all specified files in order, but remembering their type"""
        return lambda filename: (argparse.FileType('r')(filename), file_type)

    argv_parser = argparse.ArgumentParser(epilog=command_help_text(),
                                          formatter_class=argparse.RawTextHelpFormatter)
    argv_parser.add_argument("-c", "--cmd",
                             help="Name of command to run")
    argv_parser.add_argument("-i", "--interactive", action='store_true', default=None,
                             help="Interactive mode (the default if no command or files are specified)")
    argv_parser.add_argument("-S", "--single", action='store_true',
                             help="Join further command line arguments into a single command argument"
                                  + "\nOtherwise, they will be treated as individual arguments")
    argv_parser.add_argument("-f", "--file",
                             type=file_arg('f'), action='append',
                             help="Load commands or arguments from a file (guesses which you mean)")
    argv_parser.add_argument("-C", "--cmd-file", metavar='FILE',
                             type=file_arg('C'), action='append', dest='file',
                             help="Load commands from a file")
    argv_parser.add_argument("-A", "--arg-file", metavar='FILE',
                             type=file_arg('A'), action='append', dest='file',
                             help="Load arguments from a file")
    argv_parser.add_argument("args", nargs='*',
                             help="The command followed by its arguments"
                                  + "\nOr just the arguments if the command is specified with -c")

    options = argv_parser.parse_args()
    # load cmd from command line if not specified with an option
    if not options.cmd and options.args:
        options.cmd, options.args = options.args[0], options.args[1:]

    # default to interactive mode if it makes sense
    if options.interactive is None and options.file:
        for file, file_type in options.file:
            if file.name == '<stdin>':
                options.interactive = False
    if options.interactive is None and not options.cmd:
        options.interactive = True

    if options.single and options.args:
        options.args = [shlex.join(options.args)]

    if options.file and not options.cmd and any(file_type == 'A' for file, file_type in options.file):
        argv_parser.error("--arg-file specified, but no command specified")

    # Run command line commands
    if options.cmd:
        for arg in options.args:
            run_command(options.cmd, arg)

    # Run commands from files
    if options.file:
        for file, file_type in options.file:
            if file_type == 'f':
                file_type = 'A' if options.cmd else 'C'
            run_full_commands(file=file, cmd=options.cmd if file_type == 'A' else None)

    if options.interactive:
        interactive_loop()
