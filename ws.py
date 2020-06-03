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
exit_mode = GlobalVars.exit_mode
from datahandling import _load_pickle, PICKLE_STORAGE, load_files, filter_auto_ignored_posts
from metasmoke import Metasmoke
from metasmoke_cache import MetasmokeCache
from deletionwatcher import DeletionWatcher
import json
import time
import requests
# noinspection PyPackageRequirements
from tld.utils import update_tld_names, TldIOError
from helpers import log, Helpers, log_exception
from flovis import Flovis
from tasks import Tasks

import chatcommands


MAX_SE_WEBSOCKET_RETRIES = 5

if os.path.isfile("plugin.py"):
    try:
        import plugin
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        error_msg = "{}: {}\n".format(exc_type.__name__, exc_obj, traceback.format_tb(exc_tb))
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
if tuple(int(x) for x in platform.python_version_tuple()) < (3, 5, 0):
    raise RuntimeError("SmokeDetector requires Python version 3.5 or newer to run.")

# However, we're considering the potential to deprecate 3.5 so we need to prepare
# from this with a warning in the logs about it.
if tuple(int(x) for x in platform.python_version_tuple()) < (3, 6, 0):
    log('warning', 'SmokeDetector may remove support for versions of Python before '
                   '3.6.0 in the future, please consider upgrading your instances of '
                   'SmokeDetector to use Python 3.6 or newer.')

if not GlobalVars.metasmoke_host:
    log('info', "metasmoke host not found. Set it as metasmoke_host in the config file. "
        "See https://github.com/Charcoal-SE/metasmoke.")
if not GlobalVars.metasmoke_key:
    log('info', "No metasmoke key found, which is okay if both are running on the same host")
if not GlobalVars.metasmoke_ws_host:
    log('info', "No metasmoke websocket host found, which is okay if you're anti-websocket")


# noinspection PyProtectedMember
def restart_automatically():
    Metasmoke.send_statistics()
    exit_mode("reboot")


def load_ms_cache_data():
    """
    Load cached data from a pickle file on disk. Should really only need to be called once, on startup.

    :returns: None
    """
    if os.path.isfile(os.path.join(PICKLE_STORAGE, 'metasmokeCacheData.p')):
        data = _load_pickle('metasmokeCacheData.p')
        MetasmokeCache._cache = data['cache']
        MetasmokeCache._expiries = data['expiries']


# Restart after 6 hours, put this thing here so it doesn't get stuck at updating TLD or logging in indefinitely
Tasks.later(restart_automatically, after=21600)

try:
    update_tld_names()
except TldIOError as ioerr:
    with open('errorLogs.txt', 'a', encoding="utf-8") as errlogs:
        if "permission denied:" in str(ioerr).lower():
            if "/usr/local/lib/python" in str(ioerr) and "/dist-packages/" in str(ioerr):
                errlogs.write("WARNING: Cannot update TLD names, due to `tld` being system-wide installed and not "
                              "user-level installed.  Skipping TLD names update. \n")

            if "/home/" in str(ioerr) and ".local/lib/python" in str(ioerr) and "/site-packages/tld/" in str(ioerr):
                errlogs.write("WARNING: Cannot read/write to user-space `tld` installation, check permissions on the "
                              "path.  Skipping TLD names update. \n")

            errlogs.close()
            pass

        elif "certificate verify failed" in str(ioerr).lower():
            # Ran into this error in testing on Windows, best to throw a warn if we get this...
            errlogs.write("WARNING: Cannot verify SSL connection for TLD names update; skipping TLD names update.")
            errlogs.close()
            pass

        else:
            # That we were unable to update the TLD names isn't actually a fatal error, so just log it and continue.
            error_text = str(ioerr)
            errlogs.write("WARNING: {}".format(error_text))
            errlogs.close()
            log('warning', error_text)
            pass

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


GlobalVars.standby_mode = "standby" in sys.argv
GlobalVars.no_se_activity_scan = 'no_se_activity_scan' in sys.argv

chatcommunicate.init(username, password)
Tasks.periodic(Metasmoke.send_status_ping_and_verify_scanning_if_active, interval=60)

if GlobalVars.standby_mode:
    chatcommunicate.tell_rooms_with("debug", GlobalVars.standby_message)
    Metasmoke.send_status_ping()

    while GlobalVars.standby_mode:
        time.sleep(3)

    chatcommunicate.join_command_rooms()


# noinspection PyProtectedMember
def check_socket_connections():
    for client in chatcommunicate._clients.values():
        if client.last_activity and (datetime.utcnow() - client.last_activity).total_seconds() >= 60:
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
        log('warning', 'WS failed to create websocket connection. Attempt {} of {}.'.format(attempt, max_attempts))
        return None


def init_se_websocket_or_reboot(max_tries, tell_debug_room_on_error=False):
    for tries in range(1, 1 + max_tries, 1):
        ws = setup_websocket(tries, max_tries)
        if ws:
            break
    else:
        error_message = 'SE WebSocket: Max retries exceeded. Exiting, maybe a restart will kick things.'
        log('error', error_message)
        if tell_debug_room_on_error:
            chatcommunicate.tell_rooms_with("debug", error_message)
            time.sleep(6)  # Make it more likely the message is actually sent to the rooms prior to rebooting.
        exit_mode("reboot")

    return ws


ws = init_se_websocket_or_reboot(MAX_SE_WEBSOCKET_RETRIES)

GlobalVars.deletion_watcher = DeletionWatcher()

if "first_start" in sys.argv:
    chatcommunicate.tell_rooms_with('debug', GlobalVars.s if GlobalVars.on_branch else GlobalVars.s_reverted)

Tasks.periodic(Metasmoke.send_statistics, interval=600)

metasmoke_ws_t = Thread(name="metasmoke websocket", target=Metasmoke.init_websocket)
metasmoke_ws_t.start()

while not GlobalVars.no_se_activity_scan:
    try:
        a = ws.recv()
        if a is not None and a != "":
            action = json.loads(a)["action"]
            if action == "hb":
                ws.send("hb")
            if action == "155-questions-active":
                if GlobalVars.flovis is not None:
                    data = json.loads(json.loads(a)['data'])
                    GlobalVars.flovis.stage('received', data['siteBaseHostAddress'], data['id'], json.loads(a))

                is_spam, reason, why = check_if_spam_json(a)

                t = Thread(name="bodyfetcher post enqueing",
                           target=GlobalVars.bodyfetcher.add_to_queue,
                           args=(a, True if is_spam else None))
                t.start()

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
        ws = init_se_websocket_or_reboot(MAX_SE_WEBSOCKET_RETRIES, tell_debug_room_on_error=True)

        chatcommunicate.tell_rooms_with("debug", "Recovered from `" + exception_only + "`")

while GlobalVars.no_se_activity_scan:
    # Sleep for longer than the automatic restart
    time.sleep(30000)
