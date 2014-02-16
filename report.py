#requires https://pypi.python.org/pypi/websocket-client/
import json,os,sys,getpass
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


#wrap=SEChatWrapper("SE")
wrap=SEChatWrapper("MSO")
wrap.login(username,password)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s" % sys.argv[1] 
print s
#wrap.sendMessage("11540",s)
wrap.sendMessage("89",s)
import time
time.sleep(2000)
