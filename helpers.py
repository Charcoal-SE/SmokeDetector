import os
from collections import namedtuple

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
