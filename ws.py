#requires https://pypi.python.org/pypi/websocket-client/
from excepthook import *
import websocket
import getpass
from ChatExchange.chatexchange.client import *
import traceback
from spamhandling import *
from chatcommunicate import *

# !! Important! Be careful when adding code before this point.
# Any errors thrown there won't be caught, so only insert code here if you are really sure it works fine.

sys.excepthook = uncaught_exception
installThreadExcepthook()

if("ChatExchangeU" in os.environ):
    username=os.environ["ChatExchangeU"]
else:
    print "Username: "
    username=raw_input()
if("ChatExchangeP" in os.environ):
    password=os.environ["ChatExchangeP"]
else:
    password=getpass.getpass("Password: ")

load_files()
filter_auto_ignored_posts()

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
    except Exception, e:
        now = datetime.utcnow()
        delta = now - UtcDate.startup_utc_date
        seconds = delta.total_seconds()
        tr = traceback.format_exc()
        print(tr)
        with open("errorLogs.txt", "a") as f:
            f.write(str(now) + " UTC" + os.linesep + tr + os.linesep + os.linesep)
        if seconds < 180:
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")
        exception_only = ''.join(traceback.format_exception_only(type(e), e)).strip()
        GlobalVars.charcoal_hq.send_message("Recovered from `" + exception_only + "`")

now = datetime.utcnow()
delta = UtcDate.startup_utc_date - now
seconds = delta.total_seconds()
if seconds < 60:
    os._exit(4)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
GlobalVars.charcoal_hq.send_message(s)
