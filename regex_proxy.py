from regex import *
from regex import compile as raw_compile


_cache = {}


# Wrap regex.compile up so we have a global cache
def compile(s, *args, **kwargs):
    global _cache
    try:
        return _cache[s]
    except KeyError:
        r = raw_compile(s, *args, **kwargs)
        _cache[s] = r
        return r
