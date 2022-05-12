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
from threading import Thread


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
    datahandling.flush_queue_timings_data()
    datahandling.store_recently_scanned_posts()

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
        try:
            db.execute("CREATE TABLE error_logs (time REAL PRIMARY KEY ASC, classname TEXT, message TEXT,"
                       " traceback TEXT)")
            db.commit()
        except (sqlite3.OperationalError):
            # In CI testing, it's possible for the table to be created in a different thread between when
            # we first test for the table's existanceand when we try to create the table.
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='error_logs'").fetchone() is None:
                # Table 'error_logs' still doesn't exist
                raise
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


def log_current_thread(log_level, prefix="", postfix=""):
    if prefix:
        prefix += '\t'
    if postfix:
        postfix = '\t' + postfix
    current_thread = threading.current_thread()
    log(log_level, "{}current thread: {}: {}{}".format(prefix, current_thread.name, current_thread.ident, postfix))


def append_to_current_thread_name(text):
    threading.current_thread().name += text


def files_changed(diff, file_set):
    changed = set(diff.split())
    return bool(len(changed & file_set))


core_files = {
    "apigetpost.py",
    "blacklists.py",
    "bodyfetcher.py",
    "chatcommands.py",
    "chatcommunicate.py",
    "chatexchange_extension.py",
    "datahandling.py",
    "deletionwatcher.py",
    "editwatcher.py",
    "excepthook.py",
    "flovis.py",
    "gitmanager.py",
    "globalvars.py",
    "helpers.py",
    "metasmoke.py",
    "metasmoke_cache.py",
    "nocrash.py",
    "number_homoglyphs.py",
    "parsing.py",
    "phone_numbers.py",
    "queue_timings.py",
    "recently_scanned_posts.py",
    "socketscience.py",
    "spamhandling.py",
    "tasks.py",
    "ws.py",

    "classes/feedback.py",
    "_Git_Windows.py",
    "classes/__init__.py",
    "classes/_Post.py",

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
    city_list = ['test']
    regex.cache_all(False)
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
                if 'numbers' not in bl_file:
                    try:
                        regex.compile(line, regex.UNICODE, city=city_list, ignore_unused=True)
                    except Exception:
                        (exctype, value, traceback_or_message) = sys.exc_info()
                        exception_only = ''.join(traceback.format_exception_only(exctype, value)).strip()
                        errors.append("{0}:{1}:Regex fails to compile:r'''{2}''':{3}".format(bl_file, lineno,
                                                                                             line.rstrip('\n'),
                                                                                             exception_only))
                line = pcre_comment.sub("", line)
                if line in seen:
                    errors.append('{0}:{1}:Duplicate entry {2} (also {3})'.format(
                        bl_file, lineno, line.rstrip('\n'), seen[line]))
                else:
                    seen[line] = '{0}:{1}'.format(bl_file, lineno)
    regex.cache_all(True)
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


def remove_end_regex_comments(regex_text):
    return regex.sub(r"(?:(?<!\\)\(\?\#[^\)]*\))+$", "", regex_text)


def get_only_digits(text):
    return regex.sub(r"(?a)\D", "", text)


def add_to_global_bodyfetcher_queue_in_new_thread(hostname, question_id, should_check_site=False, source=None):
    source_text = ""
    if source:
        source_text = " from {}".format(source)
    t = Thread(name="bodyfetcher post enqueuing: {}/{}{}".format(hostname, question_id, source_text),
               target=GlobalVars.bodyfetcher.add_to_queue,
               args=(hostname, question_id, should_check_site))
    t.start()


def convert_new_scan_to_spam_result_if_new_reasons(new_info, old_info):
    if type(old_info) is dict:
        old_is_spam = old_info.get('is_spam', None)
        old_results = old_info.get('results', None)
        old_why = old_info.get('why', None)
    elif type(old_info) is tuple:
        old_is_spam, old_results, old_why = old_info
    if not old_is_spam:
        return new_info
    new_is_spam, new_results, new_why = new_info
    if new_is_spam:
        return new_info
    if type(new_results) is tuple:
        # The scan was actually spam, but was declared non-spam for some reason external to the content.
        # For example, that it was recently reported.
        actual_new_results, actual_new_why = new_results
    else:
        # The new results did not actually indicate it was spam.
        return new_info
    if len(actual_new_results) > len(old_results) or not set(actual_new_results).issubset(set(old_results)):
        # There are new reasons the post would have been reported
        return (True, actual_new_results, actual_new_why)
    return new_info
