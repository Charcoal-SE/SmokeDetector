#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json,os,sys,getpass,time
from findspam import FindSpam
from ChatExchange.chatexchange.client import *
import HTMLParser

parser=HTMLParser.HTMLParser()

if("ChatExchangeU" in os.environ):
  username=os.environ["ChatExchangeU"]
else:
  print "Username: "
  username=raw_input()
if("ChatExchangeP" in os.environ):
  password=os.environ["ChatExchangeP"]
else:
  password=getpass.getpass("Password: ")

lasthost=None
lastid=None

wrap=Client("stackexchange.com")
wrap.login(username,password)
wrapm=Client("meta.stackexchange.com")
wrapm.login(username,password)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started at rev " + os.popen("git log --pretty=format:'%h' -n 1").read() + " (@Undo)"
room = wrap.get_room("11540")
roomm = wrapm.get_room("89")
room.send_message(s)
roomm.send_message(s)

def checkifspam(data):
  global lasthost,lastid # Make this take ~4 last hosts
  d=json.loads(json.loads(data)["data"])
  s= d["titleEncodedFancy"]
  print time.strftime("%Y-%m-%d %H:%M:%S"),parser.unescape(s).encode("ascii",errors="replace")
  site = d["siteBaseHostAddress"]
  site=site.encode("ascii",errors="replace")
  sys.stdout.flush()
  test=FindSpam.testpost(s,site)
  if (0<len(test)):
    if(lastid==d["id"] and lasthost == d["siteBaseHostAddress"]):
      return False # Don't repost. Reddit will hate you.
    lastid=d["id"]
    lasthost = d["siteBaseHostAddress"]
    return True
  return False


def handlespam(data):
  try:
    d=json.loads(json.loads(data)["data"])
    title = d["titleEncodedFancy"]
    reason=", ".join(FindSpam.testpost(title,d["siteBaseHostAddress"]))
    escapedTitle = re.sub(r"([_*\\`\[\]])", r"\\\1", title)
    s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) on `%s`" % (reason,escapedTitle,d["url"],d["siteBaseHostAddress"])
    print parser.unescape(s).encode('ascii',errors='replace')
    room.send_message(s)
    roomm.send_message(s)
  except UnboundLocalError:
    print "NOP"
ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
room.join()
def watcher(ev,wrap2):
  if ev.type_id != 1:
    return;
  if(ev.content.startswith("!!/stappit")):
    if(str(ev.data["user_id"]) in ["31768","103081","73046"]):
      room.send_message("Goodbye, cruel world")
      os._exit(1)

room.watch_socket(watcher)
try:
  while True:
    a=ws.recv()
    if(a!= None and a!= ""):
      if(checkifspam(a)):
        threading.Thread(target=handlespam,args=(a,)).start()
except Exception, e:
  print sys.exc_info()[0]
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
room.send_message(s)
