import regex

from globalvars import GlobalVars
from helpers import log


def load_blacklists():
    with open("bad_keywords.txt", "r", encoding="utf-8") as f:
        GlobalVars.bad_keywords = [line.rstrip() for line in f if len(line.rstrip()) > 0]
    with open("blacklisted_websites.txt", "r", encoding="utf-8") as f:
        GlobalVars.blacklisted_websites = [line.rstrip() for line in f if len(line.rstrip()) > 0]
    with open("blacklisted_usernames.txt", "r", encoding="utf-8") as f:
        GlobalVars.blacklisted_usernames = [line.rstrip() for line in f if len(line.rstrip()) > 0]
    with open("watched_keywords.txt", "r", encoding="utf-8") as f:
        GlobalVars.watched_keywords = dict()
        for lineno, line in enumerate(f, 1):
            if regex.compile('^\s*(?:#|$)').match(line):
                continue
            try:
                when, by_whom, what = line.rstrip().split('\t')
            except ValueError as err:
                log('error', '{0}:{1}:{2}'.format(
                    'watched_keywords.txt', lineno, err))
                continue
            GlobalVars.watched_keywords[what] = {'when': when, 'by': by_whom}
