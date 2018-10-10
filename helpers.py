# coding=utf-8
import os
import sys
import traceback
from datetime import datetime
import importlib
from termcolor import colored
import requests
import regex
from glob import glob


class Helpers:
    min_log_level = 0


def escape_format(s):
    return s.replace("{", "{{").replace("}", "}}")


def expand_shorthand_link(s):
    s = s.lower()
    if s.endswith("so"):
        s = s[:-2] + "stackoverflow.com"
    elif s.endswith("se"):
        s = s[:-2] + "stackexchange.com"
    elif s.endswith("su"):
        s = s[:-2] + "superuser.com"
    elif s.endswith("sf"):
        s = s[:-2] + "serverfault.com"
    elif s.endswith("au"):
        s = s[:-2] + "askubuntu.com"
    return s


# noinspection PyMissingTypeHints
def log(log_level, *args, f=False):
    levels = {
        'debug': [0, 'grey'],
        'info': [1, 'cyan'],
        'warning': [2, 'yellow'],
        'error': [3, 'red']
    }

    level = levels[log_level][0]
    if level < Helpers.min_log_level:
        return

    color = levels[log_level][1] if log_level in levels else 'white'
    log_str = "{} {}".format(colored("[{}]".format(datetime.now().isoformat()[11:-3]),
                                     color),
                             "  ".join([str(x) for x in args]))
    print(log_str, file=sys.stderr)

    if f:  # Also to file
        log_file(log_level, *args)


def log_file(log_level, *args):
    levels = {
        'debug': 0,
        'info': 1,
        'warning': 2,
        'error': 3,
    }
    if levels[log_level] < Helpers.min_log_level:
        return

    log_str = "[{}] {}: {}".format(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), log_level.upper(),
                                   "  ".join([str(x) for x in args]))
    with open("errorLogs.txt", "a", encoding="utf-8") as f:
        print(log_str, file=f)


def log_exception(exctype, value, tb, f=False):
    now = datetime.utcnow()
    tr = '\n'.join(traceback.format_tb(tb))
    exception_only = ''.join(traceback.format_exception_only(exctype, value)).strip()
    logged_msg = "{exception}\n{now} UTC\n{row}\n\n".format(exception=exception_only, now=now, row=tr)
    log('error', logged_msg, f=f)
    with open("errorLogs.txt", "a") as fp:
        fp.write(logged_msg)


def files_changed(diff, file_set):
    changed = set(diff.split())
    return bool(len(changed & file_set))


core_files = {
    "apigetpost.py", "blacklists.py", "bodyfetcher.py", "chatcommands.py", "chatcommunicate.py",
    "chatexchange_extension.py", "datahandling.py", "deletionwatcher.py", "excepthook.py", "flovis.py",
    "gitmanager.py", "globalvars.py", "helpers.py", "metasmoke.py", "nocrash.py", "parsing.py", "spamhandling.py",
    "tasks.py", "ws.py",

    "classes/feedback.py", "classes/_Git_Windows.py", "classes/__init__.py", "classes/_Post.py",

    # Before these are made reloadable
    "rooms.yml",
}
reloadable_modules = {
    "findspam.py",
}
module_files = core_files | reloadable_modules


def only_blacklists_changed(diff):
    return not files_changed(diff, module_files)


def only_modules_changed(diff):
    return not files_changed(diff, core_files)


def reload_modules():
    result = True
    for s in reloadable_modules:
        s = s.replace(".py", "")  # Relying on our naming convention
        try:
            # Some reliable approach
            importlib.reload(sys.modules[s])
        except (KeyError, ImportError):
            result = False
    return result


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
    while response_code in {301, 302, 303, 307, 308}:
        res = requester(url, headers=headers)
        response_code = res.status_code
        if 'Location' in res.headers:
            url = res.headers['Location']

    return url


pcre_comment = regex.compile(r"\(\?#(?<!(?:[^\\]|^)(?:\\\\)*\\\(\?#)[^)]*\)")


def blacklist_integrity_check():
    bl_files = glob('bad_*.txt') + glob('blacklisted_*.txt') + glob('watched_*.txt')
    seen = dict()
    errors = []
    for bl_file in bl_files:
        with open(bl_file, 'r') as lines:
            for lineno, line in enumerate(lines, 1):
                if line.endswith('\r\n'):
                    errors.append('{0}:{1}:DOS line ending'.format(bl_file, lineno))
                elif not line.endswith('\n'):
                    errors.append('{0}:{1}:No newline'.format(bl_file, lineno))
                elif line == '\n':
                    errors.append('{0}:{1}:Empty line'.format(bl_file, lineno))
                elif bl_file == 'watched_keywords.txt':
                    line = line.split('\t')[2]

                line = pcre_comment.sub("", line)
                if line in seen:
                    errors.append('{0}:{1}:Duplicate entry {2} (also {3})'.format(
                        bl_file, lineno, line.rstrip('\n'), seen[line]))
                else:
                    seen[line] = '{0}:{1}'.format(bl_file, lineno)
    return errors


class SecurityError(Exception):
    pass
