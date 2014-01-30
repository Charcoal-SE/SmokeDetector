#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import threading
import json
import FindSpam

def checkifspam(data):
  d=json.loads(json.loads(data)["data"])
  if (FindSpam.testtitle(d["titleEncodeFancy"]):
    return True
  return False


def handlespam(data):
  print data

ws = websocket.create_connection("ws://sockets.ny.stackexchange.com/")
ws.send("155-questions-active")
while True:
  a=ws.recv()
  if(a!= None and a!= ""):
    print "a found"
    if(checkifspam(a)):
      threading.Thread(target=handlespam,args=(a,)).start()

