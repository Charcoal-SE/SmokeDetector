#requires https://pypi.python.org/pypi/websocket-client/
from excepthook import *
import websocket
import getpass
from ChatExchange.chatexchange.client import *
import traceback
from spamhandling import *
from bodyfetcher import *
from chatcommunicate import *

# !! Important! Be careful when adding code before this point.
# Our except hook will be installed here, so any errors before this point won't be caught if they're not in a
# try-except block. Hence, please avoid adding code before this comment, but if it's necessary,
# test it thoroughly.

sys.excepthook = uncaught_exception
installThreadExcepthook()

if "ChatExchangeU" in os.environ:
    username=os.environ["ChatExchangeU"]
else:
    print "Username: "
    username=raw_input()
if "ChatExchangeP" in os.environ:
    password=os.environ["ChatExchangeP"]
else:
    password=getpass.getpass("Password: ")

load_files()
filter_auto_ignored_posts()

GlobalVars.bodyfetcher=BodyFetcher()
GlobalVars.wrap.login(username, password)
GlobalVars.wrapm.login(username, password)
GlobalVars.s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started at [rev " + GlobalVars.commit_with_author + "](https://github.com/Charcoal-SE/SmokeDetector/commit/"+ GlobalVars.commit +") (hosted by Undo)"
GlobalVars.s_reverted = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started in [reverted mode](https://github.com/Charcoal-SE/SmokeDetector/blob/master/RevertedMode.md) at [rev " + GlobalVars.commit_with_author + "](https://github.com/Charcoal-SE/SmokeDetector/commit/"+ GlobalVars.commit +") (hosted by Undo)"
GlobalVars.charcoal_hq = GlobalVars.wrap.get_room(GlobalVars.charcoal_room_id)
GlobalVars.tavern_on_the_meta = GlobalVars.wrapm.get_room(GlobalVars.meta_tavern_room_id)

GlobalVars.specialrooms = [{ "sites": ["english.stackexchange.com"], "room": GlobalVars.wrap.get_room("95"), "unwantedReasons": [] }, { "sites": ["askubuntu.com"], "room": GlobalVars.wrap.get_room("201"), "unwantedReasons": ["All-caps title", "Phone number detected"] }]

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

threading.Thread(target=restart_automatically,args=(3600,)).start()


ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
GlobalVars.charcoal_hq.join()
GlobalVars.tavern_on_the_meta.join()

GlobalVars.charcoal_hq.watch_socket(watcher)
GlobalVars.tavern_on_the_meta.watch_socket(watcher)
while True:
    try:
        a = ws.recv()
        if a is not None and a != "":
            if checkifspam(a):
                threading.Thread(target=handlespam,args=(a,)).start()
            else:
                threading.Thread(target=GlobalVars.bodyfetcher.addToQueue,args=(a,)).start()
    except Exception, e:
        now = datetime.utcnow()
        delta = now - UtcDate.startup_utc_date
        seconds = delta.total_seconds()
        tr = traceback.format_exc()
        exception_only = ''.join(traceback.format_exception_only(type(e), e)).strip()
        logged_msg = str(now) + " UTC" + os.linesep + exception_only + os.linesep + tr + os.linesep + os.linesep
        print(logged_msg)
        with open("errorLogs.txt", "a") as f:
            f.write(logged_msg)
        if seconds < 180:
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")
        GlobalVars.charcoal_hq.send_message("Recovered from `" + exception_only + "`")

now = datetime.utcnow()
delta = UtcDate.startup_utc_date - now
seconds = delta.total_seconds()
if seconds < 60:
    os._exit(4)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
GlobalVars.charcoal_hq.send_message(s)
