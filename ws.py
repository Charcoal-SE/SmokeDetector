#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json
from findspam import FindSpam
from ChatExchange.SEChatWrapper import *
username =""
password=""

wrap=SEChatWrapper("SE")
wrap.login(username,password)

def checkifspam(data):
  d=json.loads(json.loads(data)["data"])
  if (True or FindSpam.testtitle(d["titleEncodeFancy"])):
    return True
  return False


def handlespam(data):
  d=json.loads(json.loads(data)["data"])
  s="Possible spam: [%s](%s)" % (d["titleEncodeFancy"],d["url"])
  print s
  wrap.sendMessage("11540",s)

ws = websocket.create_connection("ws://sockets.ny.stackexchange.com/")
ws.send("155-questions-active")
while True:
  a=ws.recv()
  if(a!= None and a!= ""):
    print "a found"
    if(checkifspam(a)):
      threading.Thread(target=handlespam,args=(a,)).start()

