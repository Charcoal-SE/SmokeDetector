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
    cmds = [(n, v[0], v[1]) for n, v in utilities.items()]
    maxlen = max([len(x[0]) for x in cmds])
    template = "  {{:{}}}  {{}}".format(maxlen)
    print("List of available commands:\n" + "\n".join([template.format(n, d) for n, d, f in cmds]))


def interactive_loop():
    try:
        import readline
    except ImportError:
        pass
    print("Smokey utility\nType \"help\" for a list of commands", file=sys.stderr)
    while True:
        cmd = input_command()
        if cmd:
            run_command(*cmd)


def run_command(name, arg):
    if name not in utilities:
        print("Error: function {!r} is not defined".format(name), file=sys.stderr)
        return

    desc, func = utilities[name]
    func(arg)


def input_command():
    s = ""
    try:
        s = input("$ ")
        s_split = s.split(maxsplit=1)
        if not s_split:
            return None
        cmd, arg = s_split[0], s_split[1] if len(s_split) > 1 else ''
        if arg and arg[0] in ('"', "'"):
            arg = input_multiline_arg(arg)
        return cmd, arg
    except EOFError:
        print()
        return None if s else ("exit", "")


def input_multiline_arg(s):
    while True:
        try:
            return shlex.join(shlex.split(s))
        except ValueError:
            s += "\n" + input("> ")  # continue reading


if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive_loop()
    else:
        run_command(sys.argv[1], shlex.join(sys.argv[1:]))
