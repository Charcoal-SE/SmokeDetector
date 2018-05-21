import websocket
import socket
import json
import time
from threading import Thread
from helpers import log


class Flovis:
    ws = None

    def __init__(self, host):
        self.host = host
        initialized = False
        attempts = 0
        while not initialized and attempts < 5:
            initialized = self._init_websocket()
            if not initialized:
                time.sleep(1)
                attempts += 1

    def _init_websocket(self):
        def on_message(ws, frame):
            msg = json.loads(frame)
            if 'action' in msg and msg['action'] == 'ping':
                ws.send(json.dumps({'action': 'pong'}))
            else:
                ws.send(json.dumps({'action': 'info', 'message': "LA LA LA I'M NOT LISTENING"}))

        def on_close(_ws):
            self._init_websocket()

        try:
            self.ws = websocket.WebSocketApp(self.host, on_message=on_message, on_close=on_close)
            def run():
                self.ws.run_forever()

            flovis_t = Thread(name='flovis_websocket', target=run)
            flovis_t.start()

            return True
        except (websocket._exceptions.WebSocketBadStatusException, socket.gaierror) as e:
            log('error', e)
            self.ws = None
            return False

    def stage(self, name, site, post_id, data=None):
        msg_data = {'action': 'stage', 'name': name, 'site': site, 'post_id': post_id}

        if data is not None:
            msg_data['data'] = data

        self.ws.send(json.dumps(msg_data))

