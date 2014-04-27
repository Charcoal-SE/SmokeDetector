#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json,os,sys,getpass,time
from findspam import FindSpam
from ChatExchange.src.chatexchange.wrapper import *
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

wrap=SEChatWrapper("SE")
wrap.login(username,password)
wrapm=SEChatWrapper("MSE")
wrapm.login(username,password)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started"
wrap.sendMessage("11540",s)

def checkifspam(data):
  global lasthost,lastid
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
    reason=",".join(FindSpam.testpost(d["titleEncodedFancy"],d["siteBaseHostAddress"]))
    s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) on `%s`" % (reason,d["titleEncodedFancy"],d["url"],d["siteBaseHostAddress"])
    print parser.unescape(s).encode('ascii',errors='replace')
    wrap.sendMessage("11540",s)
    wrapm.sendMessage("89",s)
  except UnboundLocalError:
    print "NOP"
ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
wrap.joinRoom("11540")
def watcher(msg,wrap2):
  if(msg["content"].startswith("!!/stappit")):
    if(str(msg["user_id"]) in ["31768","103081","73046"]):
      wrap2.sendMessage("11540","Goodbye, cruel world")
      os._exit(1)

wrap.watchRoom("11540",watcher,300)
while True:
  a=ws.recv()
  if(a!= None and a!= ""):
    if(checkifspam(a)):
      threading.Thread(target=handlespam,args=(a,)).start()

s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
wrap.sendMessage("11540",s)
