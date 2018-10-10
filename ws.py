#!/usr/bin/env python3
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
# noinspection PyPackageRequirements
import websocket
from threading import Thread
import traceback
from bodyfetcher import BodyFetcher
import chatcommunicate
from datetime import datetime
from spamhandling import check_if_spam_json
from globalvars import GlobalVars
from datahandling import load_files, filter_auto_ignored_posts
from metasmoke import Metasmoke
from deletionwatcher import DeletionWatcher
import json
import time
import requests
# noinspection PyPackageRequirements
from tld.utils import update_tld_names, TldIOError
from helpers import log, Helpers
from flovis import Flovis
from tasks import Tasks

import chatcommands

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

if not GlobalVars.metasmoke_host:
    log('info', "metasmoke host not found. Set it as metasmoke_host in the config file. "
        "See https://github.com/Charcoal-SE/metasmoke.")
if not GlobalVars.metasmoke_key:
    log('info', "No metasmoke key found, which is okay if both are running on the same host")
if not GlobalVars.metasmoke_ws_host:
    log('info', "No metasmoke websocket host found, which is okay if you're anti-websocket")

try:
    update_tld_names()
except TldIOError as ioerr:
    with open('errorLogs.txt', 'a') as errlogs:
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
            raise ioerr

if "ChatExchangeU" in os.environ:
    log('debug', "ChatExchange username loaded from environment")
    username = os.environ["ChatExchangeU"]
elif GlobalVars.chatexchange_u:
    log('debug', "ChatExchange username loaded from config")
    username = GlobalVars.chatexchange_u
else:
    log('error', "No ChatExchange username provided. Set it in config or provide it via environment variable")
    os._exit(6)

if "ChatExchangeP" in os.environ:
    log('debug', "ChatExchange password loaded from environment")
    password = os.environ["ChatExchangeP"]
elif GlobalVars.chatexchange_p:
    log('debug', "ChatExchange password loaded from config")
    password = GlobalVars.chatexchange_p
else:
    log('error', "No ChatExchange password provided. Set it in config or provide it via environment variable")
    os._exit(6)

# We need an instance of bodyfetcher before load_files() is called
GlobalVars.bodyfetcher = BodyFetcher()
if GlobalVars.flovis_host:
    GlobalVars.flovis = Flovis(GlobalVars.flovis_host)

load_files()
filter_auto_ignored_posts()


GlobalVars.standby_mode = "standby" in sys.argv

chatcommunicate.init(username, password)
Tasks.periodic(Metasmoke.send_status_ping, interval=60)
Tasks.periodic(Metasmoke.check_last_pingtime, interval=30)

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
            os._exit(10)


# noinspection PyProtectedMember
def restart_automatically():
    Metasmoke.send_statistics()
    os._exit(5)


Tasks.periodic(check_socket_connections, interval=90)
Tasks.later(restart_automatically, after=21600)

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


max_tries = 5
for tries in range(1, 1 + max_tries, 1):
    ws = setup_websocket(tries, max_tries)
    if ws:
        break
else:
    log('error', 'Max retries exceeded. Exiting, maybe a restart will kick things.')
    os._exit(5)

GlobalVars.deletion_watcher = DeletionWatcher()

if "first_start" in sys.argv:
    chatcommunicate.tell_rooms_with('debug', GlobalVars.s if GlobalVars.on_master else GlobalVars.s_reverted)

Tasks.periodic(Metasmoke.send_statistics, interval=600)

metasmoke_ws_t = Thread(name="metasmoke websocket", target=Metasmoke.init_websocket)
metasmoke_ws_t.start()

while True:
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
        with open("errorLogs.txt", "a") as f:
            f.write(logged_msg)
        if seconds < 180 and exc_type not in {websocket.WebSocketConnectionClosedException, requests.ConnectionError}:
            # noinspection PyProtectedMember
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")

        chatcommunicate.tell_rooms_with("debug", "Recovered from `" + exception_only + "`")
