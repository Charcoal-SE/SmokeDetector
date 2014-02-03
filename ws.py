#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json,os,sys,getpass
from findspam import FindSpam
from ChatExchange.SEChatWrapper import *

if("ChatExchangeU" in os.environ):
  username=os.environ["ChatExchangeU"]
else:
  print "Username: "
  username=raw_input()
if("ChatExchangeP" in os.environ):
  password=os.environ["ChatExchangeP"]
else:
  password=getpass.getpass("Password: ")

lasthost=""
lastid=""

wrap=SEChatWrapper("SE")
wrap.login(username,password)
wrapm=SEChatWrapper("MSO")
wrapm.login(username,password)

def checkifspam(data):
  d=json.loads(json.loads(data)["data"])
  s= d["titleEncodedFancy"]
  s=s.encode("ascii",errors="xmlcharrefreplace")
  print s
  sys.stdout.flush()
  test=FindSpam.testtitle(s)
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
    reason=",".join(FindSpam.testtitle(d["titleEncodedFancy"]))
    s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s)" % (reason,d["titleEncodedFancy"].encode("ascii","xmlcharrefreplace"),d["url"])
    print s
    wrap.sendMessage("11540",s)
    wrapm.sendMessage("89",s)
  except UnboundLocalError:
    print "NOP"
ws = websocket.create_connection("ws://sockets.ny.stackexchange.com/")
ws.send("155-questions-active")
while True:
  a=ws.recv()
  if(a!= None and a!= ""):
    if(checkifspam(a)):
      threading.Thread(target=handlespam,args=(a,)).start()

