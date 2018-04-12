# coding=utf-8
import os
from datetime import datetime
from termcolor import colored
import requests


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


# FAIR WARNING: Sending HEAD requests to resolve a shortened link is generally okay - there aren't
# as many exploits that work on just HEAD responses. If you specify sending a GET request, you
# acknowledge that this will fetch the full, potentially unsafe response from the shortener.
def unshorten_link(url, request_type='HEAD', explicitly_ignore_security_warning=False):
    requesters = {
        'GET': requests.get,
        'HEAD': requests.head
    }
    if request_type not in requesters:
        raise KeyError('Unavailable request_type {}'.format(request_type))
    if request_type == 'GET' and not explicitly_ignore_security_warning:
        raise SecurityError('Potentially unsafe request type GET not acknowledged')

    requester = requesters[request_type]
    response_code = 301
    headers = {'User-Agent': 'SmokeDetector/git (+https://github.com/Charcoal-SE/SmokeDetector)'}
    while response_code in [301, 302, 303, 307, 308]:
        res = requester(url, headers=headers)
        response_code = res.status_code
        if 'Location' in res.headers:
            url = res.headers['Location']

    return url


class SecurityError(Exception):
    pass
