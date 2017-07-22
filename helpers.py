# coding=utf-8
import os
from collections import namedtuple
from datetime import datetime
from termcolor import colored

Response = namedtuple('Response', 'command_status message')


# Allows use of `environ_or_none("foo") or "default"` shorthand
# noinspection PyBroadException,PyMissingTypeHints
def environ_or_none(key):
    try:
        return os.environ[key]
    except:
        return None


# Checks that all items in a pattern-matching product name are unique
def all_matches_unique(match):
    return len(match[0][1::2]) == len(set(match[0][1::2]))


# noinspection PyMissingTypeHints
def log(log_level, *args):
    colors = {
        'debug': 'grey',
        'info': 'cyan',
        'warning': 'yellow',
        'error': 'red'
    }
    color = (colors[log_level] if log_level in colors else 'white')
    log_str = u"{} {}".format(colored("[{}]".format(datetime.now().isoformat()[11:-7]), color),
                              u"  ".join([str(x) for x in args]))
    print(log_str)


def only_blacklists_changed(diff):
    blacklist_files = ["bad_keywords.txt", "blacklisted_usernames.txt", "blacklisted_websites.txt",
                       "watched_keywords.txt"]
    files_changed = diff.split()
    non_blacklist_files = [f for f in files_changed if f not in blacklist_files]
    return not bool(non_blacklist_files)
