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
# noinspection PyPackageRequirements
import websocket
import getpass
from threading import Thread
import traceback
from bodyfetcher import BodyFetcher
import chatcommunicate
from datetime import datetime
from utcdate import UtcDate
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
from helpers import log
from tasks import Tasks

import chatcommands

try:
    update_tld_names()
except TldIOError as ioerr:
    with open('errorLogs.txt', 'a') as errlogs:
        if "permission denied:" in str(ioerr).lower():
            if "/usr/local/lib/python2.7/dist-packages/" in str(ioerr):
                errlogs.write("WARNING: Cannot update TLD names, due to `tld` being system-wide installed and not "
                              "user-level installed.  Skipping TLD names update. \n")

            if "/home/" in str(ioerr) and ".local/lib/python2.7/site-packages/tld/" in str(ioerr):
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
    username = os.environ["ChatExchangeU"]
else:
    username = input("Username: ")
if "ChatExchangeP" in os.environ:
    password = os.environ["ChatExchangeP"]
else:
    password = getpass.getpass("Password: ")

# We need an instance of bodyfetcher before load_files() is called
GlobalVars.bodyfetcher = BodyFetcher()

load_files()
filter_auto_ignored_posts()


GlobalVars.s = "[ " + GlobalVars.chatmessage_prefix + " ] " \
               "SmokeDetector started at [rev " +\
               GlobalVars.commit_with_author +\
               "](" + GlobalVars.bot_repository + "/commit/" +\
               GlobalVars.commit['id'] +\
               ") (running on " +\
               GlobalVars.location +\
               ")"
GlobalVars.s_reverted = "[ " + GlobalVars.chatmessage_prefix + " ] " \
                        "SmokeDetector started in [reverted mode](" + \
                        "https://charcoal-se.org/smokey/SmokeDetector-Statuses#reverted-mode) " \
                        "at [rev " + \
                        GlobalVars.commit_with_author + \
                        "](" + GlobalVars.bot_repository + "/commit/" + \
                        GlobalVars.commit['id'] + \
                        ") (running on " +\
                        GlobalVars.location +\
                        ")"
GlobalVars.standby_message = "[ " + GlobalVars.chatmessage_prefix + " ] " \
                             "SmokeDetector started in [standby mode](" + \
                             "https://charcoal-se.org/smokey/SmokeDetector-Statuses#standby-mode) " + \
                             "at [rev " +\
                             GlobalVars.commit_with_author +\
                             "](" + GlobalVars.bot_repository + "/commit/" +\
                             GlobalVars.commit['id'] +\
                             ") (running on " +\
                             GlobalVars.location +\
                             ")"

GlobalVars.standby_mode = "standby" in sys.argv

chatcommunicate.init(username, password)

if GlobalVars.standby_mode:
    chatcommunicate.tell_rooms_with("debug", GlobalVars.standby_message)
    Metasmoke.send_status_ping()

    while GlobalVars.standby_mode:
        time.sleep(3)


# noinspection PyProtectedMember
def check_socket_connections():
    for client in chatcommunicate._clients.values():
        if client.last_activity and (datetime.utcnow() - client.last_activity).total_seconds() >= 60:
            os._exit(10)


# noinspection PyProtectedMember
def restart_automatically():
    Metasmoke.send_statistics()
    os._exit(1)


Tasks.periodic(check_socket_connections, interval=90)
Tasks.later(restart_automatically, after=21600)

log('info', GlobalVars.location)
log('info', GlobalVars.metasmoke_host)

DeletionWatcher.update_site_id_list()

ws = websocket.create_connection("wss://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")

if "first_start" in sys.argv and GlobalVars.on_master:
    chatcommunicate.tell_rooms_with("debug", GlobalVars.s)
elif "first_start" in sys.argv and not GlobalVars.on_master:
    chatcommunicate.tell_rooms_with("debug", GlobalVars.s_reverted)

Tasks.periodic(Metasmoke.send_status_ping, interval=60)
Tasks.periodic(Metasmoke.send_statistics, interval=600)
Tasks.periodic(Metasmoke.check_last_pingtime, interval=30)

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
                is_spam, reason, why = check_if_spam_json(a)
                t = Thread(name="bodyfetcher post enqueing",
                           target=GlobalVars.bodyfetcher.add_to_queue,
                           args=(a, True if is_spam else None))
                t.start()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        now = datetime.utcnow()
        delta = now - UtcDate.startup_utc_date
        seconds = delta.total_seconds()
        tr = traceback.format_exc()
        exception_only = ''.join(traceback.format_exception_only(type(e), e))\
                           .strip()
        n = os.linesep
        logged_msg = str(now) + " UTC" + n + exception_only + n + tr + n + n
        log('error', logged_msg)
        with open("errorLogs.txt", "a") as f:
            f.write(logged_msg)
        if seconds < 180 and exc_type != websocket.WebSocketConnectionClosedException\
                and exc_type != KeyboardInterrupt and exc_type != SystemExit and exc_type != requests.ConnectionError:
            # noinspection PyProtectedMember
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")

        chatcommunicate.tell_rooms_with("debug", "Recovered from `" + exception_only + "`")
