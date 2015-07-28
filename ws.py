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
import threading
from threading import Thread
import traceback
from bodyfetcher import BodyFetcher
from chatcommunicate import watcher
from continuousintegration import watch_ci
from datetime import datetime
from utcdate import UtcDate
from spamhandling import check_if_spam_json, handle_spam_json
from globalvars import GlobalVars
from datahandling import load_files, filter_auto_ignored_posts
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

load_files()
filter_auto_ignored_posts()

GlobalVars.bodyfetcher = BodyFetcher()
GlobalVars.wrap.login(username, password)
GlobalVars.wrapm.login(username, password)
GlobalVars.wrapso.login(username, password)
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
                        ") (running on" +\
                        GlobalVars.location +\
                        ")"

GlobalVars.charcoal_hq = GlobalVars.wrap.get_room(GlobalVars.charcoal_room_id)
tavern_id = GlobalVars.meta_tavern_room_id
GlobalVars.tavern_on_the_meta = GlobalVars.wrapm.get_room(tavern_id)
GlobalVars.socvr = GlobalVars.wrapso.get_room(GlobalVars.socvr_room_id)

GlobalVars.specialrooms = [{
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
                           "unwantedReasons": ["All-caps title",
                                               "Phone number detected",
                                               "Repeating characters in title",
                                               "Repeating characters in body",
                                               "Repeating characters in answer"]
                           }, {
                           "sites": ["puzzling.stackexchange.com"],
                           "room": GlobalVars.wrap.get_room("21276"),
                           "unwantedReasons": []
                           }]

GlobalVars.bayesian_testroom = GlobalVars.wrap.get_room("17251")
if "first_start" in sys.argv and GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s)
    GlobalVars.bayesian_testroom.send_message(GlobalVars.s)
elif "first_start" in sys.argv and not GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s_reverted)
    GlobalVars.bayesian_testroom.send_message(GlobalVars.s_reverted)


def restart_automatically(time_in_seconds):
    time.sleep(time_in_seconds)
    os._exit(1)

Thread(target=restart_automatically, args=(21600,)).start()

Thread(target=watch_ci, args=()).start()

ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
GlobalVars.charcoal_hq.join()
GlobalVars.tavern_on_the_meta.join()
GlobalVars.socvr.join()

GlobalVars.charcoal_hq.watch_socket(watcher)
GlobalVars.tavern_on_the_meta.watch_socket(watcher)
GlobalVars.socvr.watch_socket(watcher)
while True:
    try:
        a = ws.recv()
        if a is not None and a != "":
            is_spam, reason, why = check_if_spam_json(a)
            if is_spam:
                handle_spam_json(a, reason, why)
            else:
                t = Thread(target=GlobalVars.bodyfetcher.add_to_queue,
                           args=(a,))
                t.start()
                print("Active threads: " + str(threading.active_count()))
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
