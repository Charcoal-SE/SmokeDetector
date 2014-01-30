#requires https://pypi.python.org/pypi/websocket-client/
import websocket
ws = websocket.create_connection("ws://sockets.ny.stackexchange.com/")
ws.send("155-questions-active")
while True:
  print ws.recv()
