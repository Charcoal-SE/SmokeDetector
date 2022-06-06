#!/usr/bin/env python3
# coding=utf-8
# requires https://pypi.python.org/pypi/websocket-client/

from excepthook import uncaught_exception, install_thread_excepthook
import sys
sys.excepthook = uncaught_exception
install_thread_excepthook()

# !! Important! Be careful when adding code/imports before this point.
# Our except hook is installed here, so any errors before this point
# won't be caught if they're not in a try-except block.
# Hence, please avoid adding code before this comment; if it's necessary,
# test it thoroughly.

import os
import platform
# noinspection PyPackageRequirements
import websocket
from threading import Thread
import traceback
from bodyfetcher import BodyFetcher
import chatcommunicate
from datetime import datetime
from spamhandling import check_if_spam_json
from globalvars import GlobalVars
from datahandling import (load_pickle, PICKLE_STORAGE, load_files, filter_auto_ignored_posts,
                          refresh_site_id_dict_if_needed_and_get_issues)
from metasmoke import Metasmoke
from metasmoke_cache import MetasmokeCache
from deletionwatcher import DeletionWatcher
from editwatcher import EditWatcher
import json
import time
import requests
import dns.resolver
# noinspection PyPackageRequirements
from tld.utils import update_tld_names, TldIOError
from helpers import exit_mode, log, Helpers, log_exception, add_to_global_bodyfetcher_queue_in_new_thread
from flovis import Flovis
from tasks import Tasks

import chatcommands


MAX_SE_WEBSOCKET_RETRIES = 5
MIN_PYTHON_VERSION = (3, 6, 0)
RECOMMENDED_PYTHON_VERSION = (3, 7, 0)
THIS_PYTHON_VERSION = tuple(map(int, platform.python_version_tuple()))
MIN_ELAPSED_SEND_SITE_ID_ISSUES_TO_CHAT = 2 * 60 * 60  # 2 hours in seconds

if os.path.isfile("plugin.py"):
    try:
        import plugin
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        error_msg = "{}: {}\n{}".format(exc_type.__name__, exc_obj, traceback.format_tb(exc_tb))
        log('warning', "Error while importing plugin:\n" + error_msg)
        # Ignore and move on

levels = {
    'debug': 0,
    'info': 1,
    'warning': 2,
    'error': 3
}
if any('--loglevel' in x for x in sys.argv):
    idx = ['--loglevel' in x for x in sys.argv].index(True)
    arg = sys.argv[idx].split('=')
    if len(arg) >= 2:
        Helpers.min_log_level = levels[arg[-1]]
    else:
        Helpers.min_log_level = 0
else:
    Helpers.min_log_level = 0

# Python 3.5.0 is the bare minimum needed to run SmokeDetector
if THIS_PYTHON_VERSION < MIN_PYTHON_VERSION:
    msg = "SmokeDetector requires Python version {0}.{1}.{2} or newer to run.".format(*MIN_PYTHON_VERSION)
    raise RuntimeError(msg)

# However, 3.5 is already deprecated so we need to prepare for this
# with a warning in the logs about it.
if THIS_PYTHON_VERSION < RECOMMENDED_PYTHON_VERSION:
    msg = 'SmokeDetector may remove support for versions of Python before ' \
          '{0}.{1}.{2} in the future, please consider upgrading your instances of ' \
          'SmokeDetector to use Python {0}.{1}.{2} or newer.'.format(*RECOMMENDED_PYTHON_VERSION)
    log('warning', msg)

if not GlobalVars.metasmoke_host:
    log('info', "metasmoke host not found. Set it as metasmoke_host in the config file. "
        "See https://github.com/Charcoal-SE/metasmoke.")
if not GlobalVars.metasmoke_key:
    log('info', "No metasmoke key found, which is okay if both are running on the same host")
if not GlobalVars.metasmoke_ws_host:
    log('info', "No metasmoke websocket host found, which is okay if you're anti-websocket")

# Initiate DNS
#
# Based on additional research, at this point in the code *nothing* has done anything from a
# DNS or network resolution perspective - not for WebSockets nor for dnspython and the
# default resolver in it.  Since this activates and initializes the DNS *long* before
# the chat or metasmoke websockets have been initiated, this is a 'safe space' to
# begin initialization of the DNS data.
if GlobalVars.dns_nameservers != 'system':
    dns.resolver.get_default_resolver().nameservers = GlobalVars.config.dns_nameservers.split(',')

if GlobalVars.dns_cache_enabled:
    dns.resolver.get_default_resolver().cache = dns.resolver.Cache(GlobalVars.dns_cache_interval)


# noinspection PyProtectedMember
def restart_automatically():
    Metasmoke.send_statistics()
    chatcommunicate.tell_rooms_with("debug", "{}: Executing automatic scheduled reboot.".format(GlobalVars.location))
    time.sleep(6)
    exit_mode("reboot")


def load_ms_cache_data():
    """
    Load cached data from a pickle file on disk. Should really only need to be called once, on startup.

    :returns: None
    """
    if os.path.isfile(os.path.join(PICKLE_STORAGE, 'metasmokeCacheData.p')):
        data = load_pickle('metasmokeCacheData.p')
        MetasmokeCache._cache = data['cache']
        MetasmokeCache._expiries = data['expiries']


# Restart after 6 hours, put this thing here so it doesn't get stuck at updating TLD or logging in indefinitely
Tasks.later(restart_automatically, after=21600)

try:
    update_tld_names()
except TldIOError as ioerr:
    # That we were unable to update the TLD names isn't actually a fatal error, so just log it and continue.
    strerror = str(ioerr)
    if "permission denied:" in strerror.lower():
        if "/usr/local/lib/python" in strerror and "/dist-packages/" in strerror:
            err_msg = "WARNING: Cannot update TLD names, due to `tld` being system-wide installed and not " \
                      "user-level installed.  Skipping TLD names update. \n"

        if "/home/" in strerror and ".local/lib/python" in strerror and "/site-packages/tld/" in strerror:
            err_msg = "WARNING: Cannot read/write to user-space `tld` installation, check permissions on the " \
                      "path.  Skipping TLD names update. \n"

        else:
            err_msg = strerror

    elif "certificate verify failed" in strerror.lower():
        # Ran into this error in testing on Windows, best to throw a warn if we get this...
        err_msg = "WARNING: Cannot verify SSL connection for TLD names update; skipping TLD names update."

    else:
        err_msg = strerror
    log_exception(type(ioerr), ioerr, err_msg, True, level="warning")

if "ChatExchangeU" in os.environ:
    log('debug', "ChatExchange username loaded from environment")
    username = os.environ["ChatExchangeU"]
elif GlobalVars.chatexchange_u:
    log('debug', "ChatExchange username loaded from config")
    username = GlobalVars.chatexchange_u
else:
    log('error', "No ChatExchange username provided. Set it in config or provide it via environment variable")
    exit_mode("shutdown")

if "ChatExchangeP" in os.environ:
    log('debug', "ChatExchange password loaded from environment")
    password = os.environ["ChatExchangeP"]
elif GlobalVars.chatexchange_p:
    log('debug', "ChatExchange password loaded from config")
    password = GlobalVars.chatexchange_p
else:
    log('error', "No ChatExchange password provided. Set it in config or provide it via environment variable")
    exit_mode("shutdown")

# We need an instance of bodyfetcher before load_files() is called
GlobalVars.bodyfetcher = BodyFetcher()
if GlobalVars.flovis_host:
    GlobalVars.flovis = Flovis(GlobalVars.flovis_host)

load_files()
load_ms_cache_data()
filter_auto_ignored_posts()


with GlobalVars.standby_mode_lock:
    GlobalVars.standby_mode = "standby" in sys.argv
GlobalVars.no_se_activity_scan = 'no_se_activity_scan' in sys.argv
GlobalVars.no_deletion_watcher = 'no_deletion_watcher' in sys.argv
GlobalVars.no_edit_watcher = 'no_edit_watcher' in sys.argv

chatcommunicate.init(username, password)
Tasks.periodic(Metasmoke.send_status_ping_and_verify_scanning_if_active, interval=60)

with GlobalVars.standby_mode_lock:
    globalvars_standby_mode = GlobalVars.standby_mode
if globalvars_standby_mode:
    with GlobalVars.globalvars_reload_lock:
        globalvars_standby_message = GlobalVars.standby_message
    chatcommunicate.tell_rooms_with("debug", globalvars_standby_message)
    Metasmoke.send_status_ping()

    while globalvars_standby_mode:
        time.sleep(3)
        with GlobalVars.standby_mode_lock:
            globalvars_standby_mode = GlobalVars.standby_mode

    chatcommunicate.join_command_rooms()

se_site_id_issues = refresh_site_id_dict_if_needed_and_get_issues()
if (se_site_id_issues):
    send_se_site_id_issues_to_chat = False
    with GlobalVars.site_id_dict_lock:
        if GlobalVars.site_id_dict_issues_into_chat_timestamp + MIN_ELAPSED_SEND_SITE_ID_ISSUES_TO_CHAT >= time.time():
            GlobalVars.site_id_dict_issues_into_chat_timestamp = time.time()
            send_se_site_id_issues_to_chat = True
    if send_se_site_id_issues_to_chat:
        chatcommunicate.tell_rooms_with("debug", " ".join(se_site_id_issues))


# noinspection PyProtectedMember
def check_socket_connections():
    socket_failure = False
    with chatcommunicate._clients_lock:
        for client in chatcommunicate._clients.values():
            if client.last_activity and (datetime.utcnow() - client.last_activity).total_seconds() >= 60:
                socket_failure = True
    if socket_failure:
        exit_mode("socket_failure")


Tasks.periodic(check_socket_connections, interval=90)

log('info', '{} active'.format(GlobalVars.location))
log('info', 'MS host: {}'.format(GlobalVars.metasmoke_host))


def setup_websocket(attempt, max_attempts):
    try:
        ws = websocket.create_connection("wss://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")
        return ws
    except websocket.WebSocketException:
        log('warning', 'WS failed to create SE websocket connection. Attempt {} of {}.'.format(attempt, max_attempts))
        return None


def init_se_websocket_or_reboot(max_tries, tell_debug_room_on_error=False):
    for tries in range(1, 1 + max_tries, 1):
        ws = setup_websocket(tries, max_tries)
        if ws:
            break
        else:
            # Wait and hopefully network issues will be solved
            time.sleep(10)
    else:
        error_message = 'SE WebSocket: Max retries exceeded. Exiting, maybe a restart will kick things.'
        log('error', error_message)
        if tell_debug_room_on_error:
            chatcommunicate.tell_rooms_with("debug", error_message)
            time.sleep(6)  # Make it more likely the message is actually sent to the rooms prior to rebooting.
        exit_mode("reboot")

    return ws


if not GlobalVars.no_se_activity_scan:
    ws = init_se_websocket_or_reboot(MAX_SE_WEBSOCKET_RETRIES)

GlobalVars.deletion_watcher = DeletionWatcher()
GlobalVars.edit_watcher = EditWatcher()

if "first_start" in sys.argv:
    with GlobalVars.globalvars_reload_lock:
        first_strat_debug_tell_text = GlobalVars.s if GlobalVars.on_branch else GlobalVars.s_reverted
    chatcommunicate.tell_rooms_with('debug', first_strat_debug_tell_text)

Tasks.periodic(Metasmoke.send_statistics, interval=600)

metasmoke_ws_t = Thread(name="metasmoke websocket", target=Metasmoke.init_websocket)
metasmoke_ws_t.start()

while not GlobalVars.no_se_activity_scan:
    try:
        a = ws.recv()
        if a is not None and a != "":
            message = json.loads(a)
            action = message["action"]
            if action == "hb":
                ws.send("hb")
            if action == "155-questions-active":
                data = json.loads(message['data'])
                hostname = data['siteBaseHostAddress']
                question_id = data['id']
                if GlobalVars.flovis is not None:
                    GlobalVars.flovis.stage('received', hostname, question_id, json.loads(a))

                is_spam = False
                if GlobalVars.bodyfetcher.threshold == 1 and hostname not in GlobalVars.bodyfetcher.special_cases:
                    # If the queue threshold depth is 1 and there are no special cases, then there's not
                    # much benefit to pre-testing, as there isn't a wait for the queue to fill to the threshold.
                    # The site will, however, be behind any site which is already queued.
                    is_spam, reason, why = check_if_spam_json(a)

                add_to_global_bodyfetcher_queue_in_new_thread(hostname, question_id, True if is_spam else None,
                                                              source="155-questions-active")
                GlobalVars.edit_watcher.subscribe(hostname=hostname, question_id=question_id)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        now = datetime.utcnow()
        delta = now - GlobalVars.startup_utc_date
        seconds = delta.total_seconds()
        tr = traceback.format_exc()
        exception_only = ''.join(traceback.format_exception_only(type(e), e))\
                           .strip()
        n = os.linesep
        logged_msg = str(now) + " UTC" + n + exception_only + n + tr + n + n
        log('error', logged_msg)
        log_exception(exc_type, exc_obj, exc_tb)
        if seconds < 180 and exc_type not in {websocket.WebSocketConnectionClosedException, requests.ConnectionError}:
            # noinspection PyProtectedMember
            exit_mode("early_exception")
        if not GlobalVars.no_se_activity_scan:
            ws = init_se_websocket_or_reboot(MAX_SE_WEBSOCKET_RETRIES, tell_debug_room_on_error=True)

        chatcommunicate.tell_rooms_with("debug", "{}: SE WebSocket: recovered from `{}`"
                                                 .format(GlobalVars.location, exception_only))

while GlobalVars.no_se_activity_scan:
    # Sleep for longer than the automatic restart
    time.sleep(30000)
