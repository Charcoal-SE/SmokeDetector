#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json,os,sys
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
    return True
  return False


def handlespam(data):
  d=json.loads(json.loads(data)["data"])
  s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Possible spam: [%s](%s)" % (d["titleEncodedFancy"].encode("ascii","xmlcharrefreplace"),d["url"])
  print s
  wrap.sendMessage("11540",s)
  wrapm.sendMessage("89",s)

ws = websocket.create_connection("ws://sockets.ny.stackexchange.com/")
ws.send("155-questions-active")
while True:
  a=ws.recv()
  if(a!= None and a!= ""):
    if(checkifspam(a)):
      threading.Thread(target=handlespam,args=(a,)).start()

