# requires https://pypi.python.org/pypi/websocket-client/

from excepthook import uncaught_exception, install_thread_excepthook
import sys
sys.excepthook = uncaught_exception
install_thread_excepthook()

# !! Important! Be careful when adding code/imports before this point.
# Our except hook is installed here, so any errors before this point
# won't be caught if they're not in a try-except block.
# Hence, please avoid adding code before this comment, but if it's necessary,
# test it thoroughly.

import websocket
import getpass
from threading import Thread
import traceback
from bodyfetcher import BodyFetcher
from chatcommunicate import watcher, special_room_watcher
from continuousintegration import watch_ci
from datetime import datetime
from utcdate import UtcDate
from spamhandling import check_if_spam_json
from globalvars import GlobalVars
from datahandling import load_files, filter_auto_ignored_posts
from metasmoke import Metasmoke
from deletionwatcher import DeletionWatcher
import os
import time
import requests

if "ChatExchangeU" in os.environ:
    username = os.environ["ChatExchangeU"]
else:
    print "Username: "
    username = raw_input()
if "ChatExchangeP" in os.environ:
    password = os.environ["ChatExchangeP"]
else:
    password = getpass.getpass("Password: ")

# We need an instance of bodyfetcher before load_files() is called
GlobalVars.bodyfetcher = BodyFetcher()

load_files()
filter_auto_ignored_posts()

GlobalVars.wrap.login(username, password)
GlobalVars.wrapm.login(username, password)
GlobalVars.wrapso.login(username, password)
GlobalVars.smokeDetector_user_id[GlobalVars.charcoal_room_id] = str(GlobalVars.wrap.get_me().id)
GlobalVars.smokeDetector_user_id[GlobalVars.meta_tavern_room_id] = str(GlobalVars.wrapm.get_me().id)
GlobalVars.smokeDetector_user_id[GlobalVars.socvr_room_id] = str(GlobalVars.wrapso.get_me().id)
GlobalVars.s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] " \
               "SmokeDetector started at [rev " +\
               GlobalVars.commit_with_author +\
               "](https://github.com/Charcoal-SE/SmokeDetector/commit/" +\
               GlobalVars.commit +\
               ") (running on " +\
               GlobalVars.location +\
               ")"
GlobalVars.s_reverted = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] " \
                        "SmokeDetector started in [reverted mode](https://github.com/Charcoal-SE/SmokeDetector/blob/master/RevertedMode.md) " \
                        "at [rev " + \
                        GlobalVars.commit_with_author + \
                        "](https://github.com/Charcoal-SE/SmokeDetector/commit/" + \
                        GlobalVars.commit + \
                        ") (running on " +\
                        GlobalVars.location +\
                        ")"

GlobalVars.charcoal_hq = GlobalVars.wrap.get_room(GlobalVars.charcoal_room_id)
tavern_id = GlobalVars.meta_tavern_room_id
GlobalVars.tavern_on_the_meta = GlobalVars.wrapm.get_room(tavern_id)
GlobalVars.socvr = GlobalVars.wrapso.get_room(GlobalVars.socvr_room_id)

GlobalVars.specialrooms = [{
                           # If you change these sites, please also update the wiki at
                           # https://github.com/Charcoal-SE/SmokeDetector/wiki/Chat-Rooms
                           "sites": ["math.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("2165"),
                           "unwantedReasons": []
                           }, {
                           "sites": ["english.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("95"),
                           "unwantedReasons": []
                           }, {
                           "sites": ["askubuntu.com"],
                           "room": GlobalVars.wrap.get_room("201"),
                           "unwantedReasons": ["All-caps title",   # these should be in uppercased form
                                               "All-caps body",
                                               "All-caps answer",
                                               "Phone number detected",
                                               "Repeating characters in title",
                                               "Repeating characters in body",
                                               "Repeating characters in answer",
                                               "Link at end of answer"],
                           "watcher": True
                           }, {
                           "sites": ["parenting.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("21625"),
                           "unwantedReasons": []
                           }, {
                           "sites": ["bitcoin.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("8089"),
                           "unwantedReasons": []
                           }, {
                           "sites": ["judaism.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("468"),
                           "unwantedReasons": []
                           }, {
                           "sites": ["money.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("35068"),
                           "unwantedReasons": ["All-caps title", "All-caps body", "All-caps answer"]
                           }
                           ]


def restart_automatically(time_in_seconds):
    time.sleep(time_in_seconds)
    os._exit(1)

Thread(target=restart_automatically, args=(21600,)).start()

Thread(target=watch_ci, args=()).start()

DeletionWatcher.update_site_id_list()

ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
GlobalVars.charcoal_hq.join()
GlobalVars.tavern_on_the_meta.join()
GlobalVars.socvr.join()

GlobalVars.charcoal_hq.watch_socket(watcher)
GlobalVars.tavern_on_the_meta.watch_socket(watcher)
GlobalVars.socvr.watch_socket(watcher)
for room in GlobalVars.specialrooms:
    if "watcher" in room:
        room.watch_socket(special_room_watcher)

if "first_start" in sys.argv and GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s)
elif "first_start" in sys.argv and not GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s_reverted)

Metasmoke.send_status_ping()  # This will call itself every minute or so

while True:
    try:
        a = ws.recv()
        if a is not None and a != "":
            is_spam, reason, why = check_if_spam_json(a)
            if is_spam:
                t = Thread(target=GlobalVars.bodyfetcher.add_to_queue,
                           args=(a, True))
                t.start()
            else:
                t = Thread(target=GlobalVars.bodyfetcher.add_to_queue,
                           args=(a,))
                t.start()
    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        now = datetime.utcnow()
        delta = now - UtcDate.startup_utc_date
        seconds = delta.total_seconds()
        tr = traceback.format_exc()
        exception_only = ''.join(traceback.format_exception_only(type(e), e))\
                           .strip()
        n = os.linesep
        logged_msg = str(now) + " UTC" + n + exception_only + n + tr + n + n
        print(logged_msg)
        with open("errorLogs.txt", "a") as f:
            f.write(logged_msg)
        if seconds < 180 and exc_type != websocket.WebSocketConnectionClosedException\
                and exc_type != KeyboardInterrupt and exc_type != SystemExit and exc_type != requests.ConnectionError:
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")
        GlobalVars.charcoal_hq.send_message("Recovered from `" + exception_only + "`")

now = datetime.utcnow()
delta = UtcDate.startup_utc_date - now
seconds = delta.total_seconds()
if seconds < 60:
    os._exit(4)
s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
GlobalVars.charcoal_hq.send_message(s)
