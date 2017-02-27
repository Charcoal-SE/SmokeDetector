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
from debugging import Debugging
if Debugging.enabled:
    # noinspection PyBroadException
    try:
        sys.path.append('pycharm-debug.egg')
        # noinspection PyUnresolvedReferences, PyPackageRequirements
        import pydevd
    except:
        print "Debugging enabled, but 'pydevd' is not available or not working."
        # noinspection PyProtectedMember
        os._exit(6)

    # noinspection PyBroadException
    try:
        print "Attaching Debugger..."
        pydevd.settrace(host=Debugging.pydev_host, port=Debugging.pydev_port, stdoutToServer=True, stderrToServer=True,
                        suspend=True)
    except Exception:
        print "Unable to attach to debugger."
        # noinspection PyProtectedMember
        os._exit(6)

else:
    pass  # We do nothing here if Debugger is not set, so go on.

# noinspection PyPackageRequirements
import websocket
import getpass
import threading
from threading import Thread
import traceback
from bodyfetcher import BodyFetcher
from chatcommunicate import watcher, special_room_watcher
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
from tld.utils import update_tld_names, TldIOError

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
    username = raw_input("Username: ")
if "ChatExchangeP" in os.environ:
    password = os.environ["ChatExchangeP"]
else:
    password = getpass.getpass("Password: ")

# We need an instance of bodyfetcher before load_files() is called
GlobalVars.bodyfetcher = BodyFetcher()

load_files()
filter_auto_ignored_posts()

# chat.stackexchange.com logon/wrapper
chatlogoncount = 0
for cl in range(1, 10):
    chatlogoncount += 1
    try:
        GlobalVars.wrap.login(username, password)
        GlobalVars.smokeDetector_user_id[GlobalVars.charcoal_room_id] = str(GlobalVars.wrap.get_me().id)
        break  # If we didn't error out horribly, we can be done with this loop
    except (ValueError, AssertionError):
        time.sleep(1)
        continue  # If we did error, we need to try this again.
if chatlogoncount >= 10:  # Handle "too many logon attempts" case to prevent infinite looping
    raise RuntimeError("Could not get Chat.SE logon.")

# chat.meta.stackexchange.com logon/wrapper
metalogoncount = 0
for cml in range(1, 10):
    metalogoncount += 1
    try:
        GlobalVars.wrapm.login(username, password)
        GlobalVars.smokeDetector_user_id[GlobalVars.meta_tavern_room_id] = str(GlobalVars.wrapm.get_me().id)
        break  # If we didn't error out horribly, we can be done with this loop
    except (ValueError, AssertionError):
        time.sleep(1)
        continue  # If we did error, we need to try this again.
if metalogoncount >= 10:  # Handle "too many logon attempts" case to prevent infinite looping
        raise RuntimeError("Could not get Chat.Meta.SE logon.")

# chat.stackoverflow.com logon/wrapper
sologoncount = 0
for sol in range(1, 10):
    sologoncount += 1
    try:
        GlobalVars.wrapso.login(username, password)
        GlobalVars.smokeDetector_user_id[GlobalVars.socvr_room_id] = str(GlobalVars.wrapso.get_me().id)
        break  # If we didn't error out horribly, we can be done with this loop
    except (ValueError, AssertionError):
        time.sleep(1)
        continue  # If we did error, we need to try this again.
if sologoncount >= 10:  # Handle "too many logon attempts" case to prevent infinite looping
    raise RuntimeError("Could not get Chat.SO logon.")

GlobalVars.s = "[ " + GlobalVars.chatmessage_prefix + " ] " \
               "SmokeDetector started at [rev " +\
               GlobalVars.commit_with_author +\
               "](" + GlobalVars.bot_repository + "/commit/" +\
               GlobalVars.commit +\
               ") (running on " +\
               GlobalVars.location +\
               ")"
GlobalVars.s_reverted = "[ " + GlobalVars.chatmessage_prefix + " ] " \
                        "SmokeDetector started in [reverted mode](" + \
                        GlobalVars.bot_repository + "/blob/master/RevertedMode.md) " \
                        "at [rev " + \
                        GlobalVars.commit_with_author + \
                        "](" + GlobalVars.bot_repository + "/commit/" + \
                        GlobalVars.commit + \
                        ") (running on " +\
                        GlobalVars.location +\
                        ")"
GlobalVars.standby_message = "[ " + GlobalVars.chatmessage_prefix + " ] " \
                             "SmokeDetector started in [standby mode](" + \
                             GlobalVars.bot_repository + "/blob/master/StandbyMode.md) " + \
                             "at [rev " +\
                             GlobalVars.commit_with_author +\
                             "](" + GlobalVars.bot_repository + "/commit/" +\
                             GlobalVars.commit +\
                             ") (running on " +\
                             GlobalVars.location +\
                             ")"

GlobalVars.charcoal_hq = GlobalVars.wrap.get_room(GlobalVars.charcoal_room_id)

if "standby" in sys.argv:
    GlobalVars.charcoal_hq.send_message(GlobalVars.standby_message)
    GlobalVars.standby_mode = True
    Metasmoke.send_status_ping()

    while GlobalVars.standby_mode:
        time.sleep(3)

tavern_id = GlobalVars.meta_tavern_room_id
GlobalVars.tavern_on_the_meta = GlobalVars.wrapm.get_room(tavern_id)
GlobalVars.socvr = GlobalVars.wrapso.get_room(GlobalVars.socvr_room_id)

# If you change these sites, please also update the wiki at
# https://github.com/Charcoal-SE/SmokeDetector/wiki/Chat-Rooms

GlobalVars.specialrooms = [
    {
        "sites": ["math.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("2165"),
        "unwantedReasons": []
    },
    {
        "sites": ["english.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("95"),
        "unwantedReasons": []
    },
    {
        "sites": ["askubuntu.com"],
        "room": GlobalVars.wrap.get_room("201"),
        "unwantedReasons": [
            "All-caps title",   # these should be in uppercased form
            "All-caps body",
            "All-caps answer",
            "Phone number detected",
            "Repeating characters in title",
            "Repeating characters in body",
            "Repeating characters in answer",
            "Link at end of answer"
        ],
        "watcher": True
    },
    {
        "sites": ["parenting.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("388"),
        "unwantedReasons": []
    },
    {
        "sites": ["bitcoin.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("8089"),
        "unwantedReasons": []
    },
    {
        "sites": ["judaism.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("468"),
        "unwantedReasons": []
    },
    {
        "sites": ["money.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("35068"),
        "unwantedReasons": ["All-caps title", "All-caps body", "All-caps answer"]
    },
    {
        "sites": ["movies.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("40705"),
        "unwantedReasons": []
    },
    {
        "sites": ["ethereum.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("34620"),
        "unwantedReasons": []
    },
    {
        "sites": ["ru.stackoverflow.com"],
        "room": GlobalVars.wrap.get_room("22462"),
        "unwantedReasons": []
    },
    {
        "sites": ["magento.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("47869"),
        "unwantedReasons": []
    },
    {
        "sites": ["rpg.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("11"),
        "unwantedReasons": []
    },
    {
        "sites": ["ell.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("24938"),
        "unwantedReasons": []
    },
    {
        "sites": ["bricks.stackexchange.com"],
        "room": GlobalVars.wrap.get_room("1964"),
        "unwantedReasons": []
    }
]


# noinspection PyProtectedMember
def restart_automatically(time_in_seconds):
    time.sleep(time_in_seconds)
    Metasmoke.send_statistics(False)  # false indicates not to auto-repeat
    os._exit(1)


Thread(name="auto restart thread", target=restart_automatically, args=(21600,)).start()

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
        room["room"].join()
        room["room"].watch_socket(special_room_watcher)

if "first_start" in sys.argv and GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s)
elif "first_start" in sys.argv and not GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s_reverted)

Metasmoke.send_status_ping()  # This will call itself every minute or so
threading.Timer(600, Metasmoke.send_statistics).start()

metasmoke_ws_t = Thread(name="metasmoke websocket", target=Metasmoke.init_websocket)
metasmoke_ws_t.start()

Metasmoke.check_last_pingtime()  # This will call itself every 10 seconds or so

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
            # noinspection PyProtectedMember
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")
        GlobalVars.charcoal_hq.send_message("Recovered from `" + exception_only + "`")
