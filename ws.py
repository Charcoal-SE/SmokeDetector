#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json,os,sys,getpass,time
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

lasthost=None
lastid=None
lasttime=time.time()

wrap=SEChatWrapper("SE")
wrap.login(username,password)
wrapm=SEChatWrapper("MSO")
wrapm.login(username,password)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started"
wrap.sendMessage("11540",s)

def checkifspam(data):
  global lasthost,lastid
  d=json.loads(json.loads(data)["data"])
  s= d["titleEncodedFancy"]
  s=s.encode("ascii",errors="xmlcharrefreplace")
  print time.strftime("%Y-%m-%d %H:%M:%S"),s
  site = d["siteBaseHostAddress"]
  site=site.encode("ascii",errors="xmlcharrefreplace")
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
    s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s)" % (reason,d["titleEncodedFancy"].encode("ascii","xmlcharrefreplace"),d["url"])
    print s
    wrap.sendMessage("11540",s)
    wrapm.sendMessage("89",s)
  except UnboundLocalError:
    print "NOP"                              
    
def handlesocket:
  global lasttime
  ws = websocket.create_connection("ws://sockets.ny.stackexchange.com/")
  ws.send("155-questions-active")
  while True:
    a=ws.recv()
    lasttime = time.time()
    if(a!= None and a!= ""):
      if(checkifspam(a)):
        threading.Thread(target=handlespam,args=(a,)).start()


while True:
  threading.Thread(target=handlesocket).start()
  while True:
    timeout = (lasttime + 60) - time.time();
    if timeout <= 0: break
    time.sleep(timeout)
  
  
    

s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
wrap.sendMessage("11540",s)
