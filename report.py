#requires https://pypi.python.org/pypi/websocket-client/
import json,os,sys,getpass
from ChatExchange.chatexchange.client import *

if("ChatExchangeU" in os.environ):
  username=os.environ["ChatExchangeU"]
else:
  print "Username: "
  username=raw_input()
if("ChatExchangeP" in os.environ):
  password=os.environ["ChatExchangeP"]
else:
  password=getpass.getpass("Password: ")


#wrap=SEChatWrapper("MSO")
wrap=Client("stackexchange.com")
wrap.login(username,password)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s" % sys.argv[1] 
print s
wrap.get_room("11540").send_message(s)
#wrap.sendMessage("89",s)
import time
time.sleep(5)
