# -*- coding: utf-8 -*-

import os
from datetime import datetime
from html.parser import HTMLParser
from html import unescape
from hashlib import md5
from configparser import NoOptionError, RawConfigParser
from helpers import environ_or_none, log
import threading
# noinspection PyCompatibility
import regex
import subprocess as sp
from dulwich.repo import Repo
import platform


def git_commit_info():
    git = Repo('.')
    commit = git.get_object(git.head())
    return {'id': commit.id.decode("utf-8")[0:7], 'id_full': commit.id.decode("utf-8"),
            'author': regex.findall("(.*?) <(.*?)>", commit.author.decode("utf-8"))[0],
            'message': commit.message.decode("utf-8").strip('\r\n').split('\n')[0]}


def git_status():
    if 'windows' in platform.platform().lower():
        data = sp.Popen(['git', 'status'], shell=True, cwd=os.getcwd(), stderr=sp.PIPE, stdout=sp.PIPE).communicate()
    else:
        data = sp.Popen(['git status'], shell=True, cwd=os.getcwd(), stderr=sp.PIPE, stdout=sp.PIPE).communicate()
    if not data[1]:
        return data[0].decode('utf-8').strip('\n')
    else:
        raise OSError("Git error!")


# This is needed later on for properly 'stripping' unicode weirdness out of git log data.
# Otherwise, we can't properly work with git log data.
def strip_escape_chars(line):
    line = str(line)
    ansi_escape = regex.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', line).strip('=\r\r\x1b>\n"')


# noinspection PyClassHasNoInit,PyDeprecation,PyUnresolvedReferences
class GlobalVars:
    false_positives = []
    whitelisted_users = []
    blacklisted_users = []
    blacklisted_usernames = []
    blacklisted_websites = []
    bad_keywords = []
    so_bad_keywords = []
    watched_keywords = {}
    ignored_posts = []
    auto_ignored_posts = []
    startup_utc = datetime.utcnow().strftime("%H:%M:%S")
    latest_questions = []
    api_backoff_time = 0

    metasmoke_last_ping_time = datetime.now()
    not_privileged_warning = """
    You are not a privileged user. Please see
    [the privileges wiki page](https://charcoal-se.org/smokey/Privileges) for
    information on what privileges are and what is expected of privileged users.
    """.strip().replace("\n", " ")

    experimental_reasons = {  # Don't widely report these
        "potentially bad keyword in answer",
        "potentially bad keyword in body",
        "potentially bad keyword in title",
        "potentially bad keyword in username"}

    parser = HTMLParser()
    parser.unescape = unescape

    code_privileged_users = None
    censored_committer_names = {"3f4ed0f38df010ce300dba362fa63a62": "Undo1"}

    commit = git_commit_info()
    if md5(commit['author'][0].encode('utf-8')).hexdigest() in censored_committer_names:
        commit['author'] = censored_committer_names[md5(commit['author'][0].encode('utf-8')).hexdigest()]

    commit_with_author = "%s (%s: *%s*)" % (commit['id'],
                                            commit['author'][0] if type(commit['author']) in [list, tuple]
                                            else commit['author'],
                                            commit['message'])

    on_master = "HEAD detached" not in git_status()

    s = ""
    s_reverted = ""
    apiquota = -1
    bodyfetcher = None
    se_sites = []
    why_data = []
    notifications = []
    listen_to_these_if_edited = []
    multiple_reporters = []
    api_calls_per_site = {}

    standby_message = ""
    standby_mode = False

    api_request_lock = threading.Lock()

    num_posts_scanned = 0
    post_scan_time = 0
    posts_scan_stats_lock = threading.Lock()

    config = RawConfigParser()

    if os.path.isfile('config'):
        config.read('config')
    else:
        config.read('config.ci')

    # environ_or_none defined in helpers.py
    bot_name = environ_or_none("SMOKEDETECTOR_NAME") or "SmokeDetector"
    bot_repository = environ_or_none("SMOKEDETECTOR_REPO") or "//github.com/Charcoal-SE/SmokeDetector"
    chatmessage_prefix = "[{}]({})".format(bot_name, bot_repository)

    site_id_dict = {}
    post_site_id_to_question = {}

    location = config.get("Config", "location")

    metasmoke_ws = None

    try:
        metasmoke_host = config.get("Config", "metasmoke_host")
    except NoOptionError:
        metasmoke_host = None
        log('info', "metasmoke host not found. Set it as metasmoke_host in the config file."
            "See https://github.com/Charcoal-SE/metasmoke.")

    try:
        metasmoke_key = config.get("Config", "metasmoke_key")
    except NoOptionError:
        metasmoke_key = ""
        log('info', "No metasmoke key found, which is okay if both are running on the same host")

    try:
        metasmoke_ws_host = config.get("Config", "metasmoke_ws_host")
    except NoOptionError:
        metasmoke_ws_host = ""
        log('info', "No metasmoke websocket host found, which is okay if you're anti-websocket")

    try:
        github_username = config.get("Config", "github_username")
        github_password = config.get("Config", "github_password")
    except NoOptionError:
        github_username = None
        github_password = None
