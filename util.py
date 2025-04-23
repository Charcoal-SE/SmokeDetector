#!/usr/bin/env python3
# coding=utf-8
# A CLI utility for various Smokey functions

import sys
import os
import shlex
import inspect

import helpers
helpers.log = lambda *args, **kwargs: None  # Override log() for less verbosity
import chatcommands


# A utility is "name: (description, func)"
utilities = {}


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


@utility("exit", "exit this utility (interactive mode)")
def util_exit():
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
