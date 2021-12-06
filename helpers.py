# coding=utf-8
import os
import sys
import traceback
from datetime import datetime
import importlib
import threading
# termcolor doesn't work properly in PowerShell or cmd on Windows, so use colorama.
import platform
platform_text = platform.platform().lower()
if 'windows' in platform_text and 'cygwin' not in platform_text:
    from colorama import init as colorama_init
    colorama_init()
from termcolor import colored
import requests
import regex
from glob import glob
import sqlite3
from urllib.parse import quote, quote_plus
from globalvars import GlobalVars
from homoglyphs import NumberHomoglyphs


def exit_mode(*args, code=0):
    args = set(args)

    if not (args & {'standby', 'no_standby'}):
        standby = 'standby' if GlobalVars.standby_mode else 'no_standby'
        args.add(standby)

    with open("exit.txt", "w", encoding="utf-8") as f:
        print("\n".join(args), file=f)
    log('debug', 'Exiting with args: {}'.format(', '.join(args) or 'None'))

    # Flush any buffered queue timing data
    import datahandling  # this must not be a top-level import in order to avoid a circular import
    datahandling.actually_add_queue_timings_data()

    # We have to use '_exit' here, because 'sys.exit' only exits the current
    # thread (not the current process).  Unfortunately, this results in
    # 'atexit' handlers not being called. All exit calls in SmokeDetector go
    # through this function, so any necessary cleanup can happen here (though
    # keep in mind that this function isn't called when terminating due to a
    # Ctrl-C or other signal).
    os._exit(code)


class ErrorLogs:
    DB_FILE = "errorLogs.db"
    # SQLite threading limitation !?!?!?

    db = sqlite3.connect(DB_FILE)
    if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='error_logs'").fetchone() is None:
        # Table 'error_logs' doesn't exist
        db.execute("CREATE TABLE error_logs (time REAL PRIMARY KEY ASC, classname TEXT, message TEXT, traceback TEXT)")
        db.commit()
    db.close()

    db_conns = {}

    @classmethod
    def get_db(cls):
        thread_id = threading.get_ident()
        if thread_id not in cls.db_conns:
            cls.db_conns[thread_id] = sqlite3.connect(cls.DB_FILE)
        return cls.db_conns[thread_id]

    @classmethod
    def add(cls, time, classname, message, traceback):
        classname = redact_passwords(classname)
        message = redact_passwords(message)
        traceback = redact_passwords(traceback)
        db = cls.get_db()
        db.execute("INSERT INTO error_logs VALUES (?, ?, ?, ?)",
                   (time, classname, message, traceback))
        db.commit()

    @classmethod
    def fetch_last(cls, n):
        db = cls.get_db()
        cursor = db.execute("SELECT * FROM error_logs ORDER BY time DESC LIMIT ?", (int(n),))
        data = cursor.fetchall()
        return data

    @classmethod
    def truncate(cls, n=100):
        """
        Truncate the DB and keep only N latest exceptions
        """
        db = cls.get_db()
        cursor = db.execute(
            "DELETE FROM error_logs WHERE time IN "
            "(SELECT time FROM error_logs ORDER BY time DESC LIMIT -1 OFFSET ?)", (int(n),))
        db.commit()
        data = cursor.fetchall()
        return data


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


def redact_text(text, redact_str, replace_with):
    if redact_str:
        return text.replace(redact_str, replace_with) \
                   .replace(quote(redact_str), replace_with) \
                   .replace(quote_plus(redact_str), replace_with)
    return text


def redact_passwords(value):
    value = str(value)
    # Generic redaction of URLs with http, https, and ftp schemes
    value = regex.sub(r"((?:https?|ftp):\/\/)[^@:\/]*:[^@:\/]*(?=@)", r"\1[REDACTED URL USERNAME AND PASSWORD]", value)
    # In case these are somewhere else.
    value = redact_text(value, GlobalVars.github_password, "[GITHUB PASSWORD REDACTED]")
    value = redact_text(value, GlobalVars.github_access_token, "[GITHUB ACCESS TOKEN REDACTED]")
    value = redact_text(value, GlobalVars.chatexchange_p, "[CHAT PASSWORD REDACTED]")
    value = redact_text(value, GlobalVars.metasmoke_key, "[METASMOKE KEY REDACTED]")
    value = redact_text(value, GlobalVars.perspective_key, "[PERSPECTIVE KEY REDACTED]")
    return value


# noinspection PyMissingTypeHints
def log(log_level, *args, f=False):
    levels = {
        'debug': [0, 'grey'],
        'info': [1, 'cyan'],
        'warning': [2, 'yellow'],
        'warn': [2, 'yellow'],
        'error': [3, 'red']
    }

    level = levels[log_level][0]
    if level < Helpers.min_log_level:
        return

    color = levels[log_level][1] if log_level in levels else 'white'
    log_str = "{} {}".format(colored("[{}]".format(datetime.utcnow().isoformat()[11:-3]),
                                     color, attrs=['bold']),
                             redact_passwords("  ".join([str(x) for x in args])))
    print(log_str, file=sys.stderr)

    if level == 3:
        exc_tb = sys.exc_info()[2]
        print(redact_passwords("".join(traceback.format_tb(exc_tb))), file=sys.stderr)

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

    log_str = redact_passwords("[{}] {}: {}".format(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                                                    log_level.upper(), "  ".join([str(x) for x in args])))
    with open("errorLogs.txt", "a", encoding="utf-8") as f:
        print(log_str, file=f)


def log_exception(exctype, value, traceback_or_message, f=False, *, level='error'):
    now = datetime.utcnow()
    if isinstance(traceback_or_message, str):
        tr = traceback_or_message
    else:
        tr = ''.join(traceback.format_tb(traceback_or_message))
    exception_only = ''.join(traceback.format_exception_only(exctype, value)).strip()
    logged_msg = "{exception}\n{now} UTC\n{row}\n\n".format(exception=exception_only, now=now, row=tr)
    # Redacting passwords happens in log() and ErrorLogs.add().
    log(level, logged_msg, f=f)
    ErrorLogs.add(now.timestamp(), exctype.__name__, str(value), tr)


def log_current_exception(f=False):
    log_exception(*sys.exc_info(), f)


def files_changed(diff, file_set):
    changed = set(diff.split())
    return bool(len(changed & file_set))


core_files = {
    "apigetpost.py", "blacklists.py", "bodyfetcher.py", "chatcommands.py", "chatcommunicate.py",
    "chatexchange_extension.py", "datahandling.py", "deletionwatcher.py", "excepthook.py", "flovis.py",
    "gitmanager.py", "globalvars.py", "helpers.py", "metasmoke.py", "nocrash.py", "parsing.py",
    "spamhandling.py", "socketscience.py", "tasks.py", "ws.py",

    "classes/feedback.py", "_Git_Windows.py", "classes/__init__.py", "classes/_Post.py",

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


def unshorten_link(url, request_type='GET', depth=10):
    orig_url = url
    response_code = 301
    headers = {'User-Agent': 'SmokeDetector/git (+https://github.com/Charcoal-SE/SmokeDetector)'}
    for tries in range(depth):
        if response_code not in {301, 302, 303, 307, 308}:
            break
        res = requests.request(request_type, url, headers=headers, stream=True, allow_redirects=False)
        res.connection.close()  # Discard response body for GET requests
        response_code = res.status_code
        if 'Location' not in res.headers:
            # No more redirects, stop
            break
        url = res.headers['Location']
    else:
        raise ValueError("Too many redirects ({}) for URL {!r}".format(depth, orig_url))
    return url


pcre_comment = regex.compile(r"\(\?#(?<!(?:[^\\]|^)(?:\\\\)*\\\(\?#)[^)]*\)")


def blacklist_integrity_check():
    bl_files = glob('bad_*.txt') + glob('blacklisted_*.txt') + glob('watched_*.txt')
    seen = dict()
    errors = []
    for bl_file in bl_files:
        with open(bl_file, 'r', encoding="utf-8") as lines:
            for lineno, line in enumerate(lines, 1):
                if line.endswith('\r\n'):
                    errors.append('{0}:{1}:DOS line ending'.format(bl_file, lineno))
                elif not line.endswith('\n'):
                    errors.append('{0}:{1}:No newline'.format(bl_file, lineno))
                elif line == '\n':
                    errors.append('{0}:{1}:Empty line'.format(bl_file, lineno))
                elif bl_file.startswith('watched_'):
                    line = line.split('\t')[2]

                line = pcre_comment.sub("", line)
                if line in seen:
                    errors.append('{0}:{1}:Duplicate entry {2} (also {3})'.format(
                        bl_file, lineno, line.rstrip('\n'), seen[line]))
                else:
                    seen[line] = '{0}:{1}'.format(bl_file, lineno)
    return errors


def chunk_list(list_in, chunk_size):
    """
    Split a list into chunks.
    """
    return [list_in[i:i + chunk_size] for i in range(0, len(list_in), chunk_size)]


class SecurityError(Exception):
    pass


def not_regex_search_ascii_and_unicode(regex_dict, test_text):
    return not regex_dict['ascii'].search(test_text) and not regex_dict['unicode'].search(test_text)


def remove_regex_comments(regex_text):
    return regex.sub(r"(?<!\\)\(\?\#[^\)]*\)", "", regex_text)


def remove_end_regex_comment(regex_text):
    return regex.sub(r"(?<!\\)\(\?\#[^\)]*\)$", "", regex_text)


def get_only_digits(text):
    return regex.sub(r"(?a)\D", "", text)


# North American phone numbers with fairly strict formatting
# The goal here is to be sure about identification, even if that leaves ones which are not identified.
# Without a 1. It must have a separator between the 334 groupings, like \d{3}\D\d{3}\D\d{4}, but with more
# than just a single \D permited. The start can be our normal mix.
NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX = r'(?<=\D)[2-9]\d{2}(?:[\W_]*+|\D(?=\d))(?<=\D)\d{4})$'
NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE = r'[2-9]\d{2}(?:[\W_]*+|\D(?=\d))\d{4})$'
NA_NUMBER_WITHOUT_ONE_REGEX_START = r'^((?:[(+{[]{1,2}[2-9]|[2-9](?<=[^\d(+{[][2-9]|^[2-9]))\d{2}' + \
                                    r'(?:[\W_]*+|\D(?:(?=\d)|(?<=\d\D)))'
NA_NUMBER_WITHOUT_ONE_REGEX = NA_NUMBER_WITHOUT_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX
NA_NUMBER_WITHOUT_ONE_LOOSE = NA_NUMBER_WITHOUT_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE
# With a 1. It must have a separator between the 334 groupings, like 1\d{3}\D\d{3}\D\d{4}, but with more
# than just a single \D permited and a separator is permitted after the 1. The start can be our normal mix.
NA_NUMBER_WITH_ONE_REGEX_START = r'^(?:[(+{[]{1,2}1|1(?<=[^\d(+{[]1|^1))(?:[\W_]*+|\D(?=\d))' + \
                                 r'([2-9]\d{2}(?:[\W_]*+|\D(?=\d))'
NA_NUMBER_WITH_ONE_REGEX = NA_NUMBER_WITH_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX
NA_NUMBER_WITH_ONE_LOOSE = NA_NUMBER_WITH_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE


def is_north_american_phone_number_with_one(text):
    return regex.match(NA_NUMBER_WITH_ONE_REGEX, text) is not None


def is_north_american_phone_number_without_one(text):
    return regex.match(NA_NUMBER_WITHOUT_ONE_REGEX, text) is not None


def is_north_american_phone_number_with_one_loose(text):
    return regex.match(NA_NUMBER_WITH_ONE_LOOSE, text) is not None


def is_north_american_phone_number_without_one_loose(text):
    return regex.match(NA_NUMBER_WITHOUT_ONE_LOOSE, text) is not None


def process_numlist(numlist, processed=None, normalized=None):
    processed = processed if processed is not None else set()
    normalized = normalized if normalized is not None else set()
    unique_normalized = set()
    duplicate_normalized = set()
    for entry in numlist:
        this_entry_normalized = set()
        without_comment = remove_end_regex_comment(entry)
        processed.add(without_comment)
        comment = entry.replace(without_comment, '')
        no_north_american = 'no noram' in comment.lower() or 'NO NA' in comment
        is_north_american = 'is noram' in comment.lower() or 'IS NA' in comment
        # normalized to only digits
        this_entry_normalized.add(get_only_digits(without_comment))
        deobfuscated = NumberHomoglyphs.normalize(without_comment)
        # deobfuscated and normalized: We don't look for the non-normalized deobfuscated
        this_entry_normalized.add(get_only_digits(deobfuscated))
        normalized_deobfuscated = get_only_digits(deobfuscated)
        report_text = 'Number entry: {}'.format(entry)
        north_american_extra = ''
        north_american_add_type = ''
        maybe_north_american_extra = ''
        maybe_north_american_add_type = ''
        if not no_north_american:
            if is_north_american_phone_number_with_one(deobfuscated):
                # Add a version without a one
                north_american_extra = normalized_deobfuscated[1:]
                north_american_add_type = 'non-1'
            elif is_north_american_phone_number_without_one(deobfuscated):
                # Add a version with a one
                north_american_extra = '1' + normalized_deobfuscated
                north_american_add_type = 'non-1'
            elif is_north_american_phone_number_with_one_loose(deobfuscated):
                # Add a version without a one
                maybe_north_american_extra = normalized_deobfuscated[1:]
                maybe_north_american_add_type = 'non-1'
            elif is_north_american_phone_number_without_one_loose(deobfuscated):
                # Add a version with a one
                maybe_north_american_extra = '1' + normalized_deobfuscated
                maybe_north_american_add_type = 'non-1'
        if is_north_american and maybe_north_american_extra:
            north_american_extra = maybe_north_american_extra
            north_american_add_type = maybe_north_american_add_type
            maybe_north_american_extra = ''
            maybe_north_american_add_type = ''
        if north_american_extra:
            this_entry_normalized.add(north_american_extra)
            report_text += ': NorAm {} normalized: {}'.format(north_american_add_type, north_american_extra)
        if maybe_north_american_extra:
            report_text += ': MAYBE NorAm {} normalized: {} (NOT ADDED)'.format(maybe_north_american_add_type,
                                                                                maybe_north_american_extra)
        this_unique_normalized = this_entry_normalized - normalized
        unique_normalized |= this_unique_normalized
        duplicate_normalized |= this_entry_normalized - this_unique_normalized
        normalized |= this_unique_normalized
        # normalized += normalized.union(this_unique_normalized)
        if unique_normalized:
            report_text += ': adding normalized: {}'.format(unique_normalized)
        else:
            # There are no unique normalized forms for this entry (i.e. it's redundant)
            report_text += ': all normalized forms already in list: {}'.format(this_entry_normalized)
        # print(report_text)
    return processed, normalized, unique_normalized, duplicate_normalized
