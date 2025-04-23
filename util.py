#!/usr/bin/env python3
# coding=utf-8
# A CLI utility for various Smokey functions

import shutil
import sys
import os
import shlex
import inspect
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


def utility(name, description):
    def wrapper(func):
        global utilities
        utilities[name] = (description, func)
        return func
    return wrapper


@utility("bisect", "finds out which blacklist/watchlist item matches a string")
def util_bisect(*args):
    for s in args:
        print(chatcommands.bisect.__func__(None, s) + "\n")


@utility("bisect-number", "finds out which number blacklist/watchlist item matches a number")
def util_bisect_number(*args):
    for s in args:
        print(chatcommands.bisect_number.__func__(None, s) + "\n")


@utility("deobfuscate-number", "homoglyph deobfuscate and normalize a number pattern")
def util_deobfuscate_number(*args):
    for s in args:
        print(chatcommands.deobfuscate_number.__func__(None, s) + "\n")


@utility("normalize-number", "show the number normalizations for a number pattern")
def util_normalize_number(*args):
    for s in args:
        print(chatcommands.normalize_number.__func__(None, s) + "\n")


@utility("test-question", "test if text would be automatically reported as a question body")
def util_test_question(*args):
    for s in args:
        print(chatcommands.test.__func__(s, alias_used='test-question') + "\n")


@utility("test-answer", "test if text would be automatically reported as an answer body")
def util_test_answer(*args):
    for s in args:
        print(chatcommands.test.__func__(s, alias_used='test-answer') + "\n")


@utility("test-user", "test if text would be automatically reported as username")
def util_test_user(*args):
    for s in args:
        print(chatcommands.test.__func__(s, alias_used='test-user') + "\n")


@utility("test-title", "test if text would be automatically reported as a question title")
def util_test_title(*args):
    for s in args:
        print(chatcommands.test.__func__(s, alias_used='test-title') + "\n")


@utility("test", "test if text would be automatically reported as a post, title, or username")
def util_test(*args):
    for s in args:
        print(chatcommands.test.__func__(s, alias_used='test') + "\n")


@utility("test-json", "test if post, given in JSON, would be automatically reported")
def util_test_json(*args):
    for s in args:
        print(chatcommands.test.__func__(s, alias_used='test-json') + "\n")


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
def util_blacklist_keyword(*args):
    ensure_blacklist_faked('KEYWORDS')
    blacklist = Blacklist(Blacklist.KEYWORDS)
    for s in args:
        blacklist.add(s)
    findspam.FindSpam.reload_blacklists()


@utility("blacklist-website", "pretend a website has been added to the blacklist")
def util_blacklist_website(*args):
    ensure_blacklist_faked('WEBSITES')
    blacklist = Blacklist(Blacklist.WEBSITES)
    for s in args:
        blacklist.add(s)
    findspam.FindSpam.reload_blacklists()


@utility("blacklist-username", "pretend a username has been added to the blacklist")
def util_blacklist_username(*args):
    ensure_blacklist_faked('USERNAMES')
    blacklist = Blacklist(Blacklist.USERNAMES)
    for s in args:
        blacklist.add(s)
    findspam.FindSpam.reload_blacklists()


@utility("blacklist-number", "pretend a number has been added to the blacklist")
def util_blacklist_number(*args):
    ensure_blacklist_faked('NUMBERS')
    blacklist = Blacklist(Blacklist.NUMBERS)
    for s in args:
        blacklist.add(s)
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
def util_unblacklist(*args):
    changes_made = False
    for s in args:
        removed_from = unblacklist(s)
        if removed_from is not None:
            print("Removed `{}` from {}.\n".format(s, removed_from))
            changes_made = True
        else:
            print("No such item `{}` in blacklist.\n".format(s))
    if changes_made:
        findspam.FindSpam.reload_blacklists()


@utility("exit", "exit this utility (interactive mode)")
def util_exit():
    # delete all temporary blacklist copies
    for path in tmp_blacklist_paths.values():
        os.unlink(path)
    exit()


@utility("help", "display a list of available sub-commands")
def util_help():
    cmds = [(n, v[0], v[1]) for n, v in utilities.items()]
    maxlen = max([len(x[0]) for x in cmds])
    template = "  {{:{}}}  {{}}".format(maxlen)
    print("List of available commands:\n" + "\n".join([template.format(n, d) for n, d, f in cmds]))


def main_start_interactive():
    try:
        import readline
    except ImportError:
        pass
    print("Smokey utility\nType \"help\" for a list of commands", file=sys.stderr)


def main_loop(args):
    try:
        name = args.pop(0)
    except IndexError:
        exit()
    if name not in utilities:
        print("Error: function {!r} is not defined".format(name), file=sys.stderr)
        return

    desc, func = utilities[name]
    func_args = inspect.getfullargspec(func)
    min_args = len(func_args[0] or "") - len(func_args[3] or "")
    if len(args) < min_args:
        print("Too few arguments")
    elif not func_args[1] and len(args) > len(func_args[0] or ""):
        print("Too many arguments")
    else:
        func(*args)


def get_input():
    try:
        s = ""
        s = input("$ ")
        while True:
            try:
                return shlex.split(s)
            except ValueError:
                s += input("> ")  # continue reading
    except EOFError:
        print()
        return [] if s else ["exit"]


if __name__ == "__main__":
    if len(sys.argv) == 1:
        main_start_interactive()
        while True:
            main_loop(get_input())
    else:
        main_loop(sys.argv[1:])
