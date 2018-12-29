#!/usr/bin/env python3
# A CLI utility for various Smokey functions

import sys
import os
import shlex

import helpers
helpers.log = lambda *args, **kwargs: None  # Override log() for less verbosity
import chatcommands


# A utility is "name: (description, func)"
utilities = {}


def utility(name, description):
    def wrapper(func):
        global utilities
        utilities[name] = (description, func)
    return wrapper


@utility("bisect", "finds out which blacklist/watchlist item matches a string")
def util_bisect(*args):
    for s in args:
        print(chatcommands.bisect.__func__(s) + "\n")


@utility("exit", None)
def util_exit():
    exit()


def main_start():
    pass


def main_loop(args):
    name = args.pop(0)
    if name not in utilities:
        print("Error: function {!r} is not defined".format(name), file=sys.stderr)

    desc, func = utilities[name]
    func(*args)


def get_input():
    s = input(">>> ")
    while True:
        try:
            return shlex.split(s)
        except ValueError:
            s += input("... ")  # continue reading


if __name__ == "__main__":
    main_start()
    if len(sys.argv) == 1:
        while True:
            main_loop(get_input())
    else:
        main_loop(sys.argv[1:])
