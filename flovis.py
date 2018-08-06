import websocket
import socket
import ssl
import json
import time
import uuid
from threading import Thread
from helpers import log


class Flovis:
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
            if 'action' in msg:
                if msg['action'] == 'ping':
                    ws.send(json.dumps({'action': 'pong'}))
                elif msg['action'] == 'response':
                    if msg['success'] is False:
                        log('warning', 'Flovis data send failed ({}): {}'.format(msg['event_id'], msg['code']))
            else:
                ws.send(json.dumps({'action': 'info', 'message': "LA LA LA I'M NOT LISTENING"}))

        def on_close(_ws):
            self._init_websocket()

        try:
            self.ws = websocket.WebSocketApp(self.host, on_message=on_message, on_close=on_close)

            def run():
                try:
                    self.ws.run_forever()
                except websocket._exceptions.WebSocketException as e:
                    if "socket is already opened" not in str(e):
                        raise
                except websocket._exceptions.WebSocketConnectionClosedException:
                    log('error', 'Flovis websocket closed unexpectedly, assuming problems and nullifying ws')
                except (AttributeError, OSError) as e:
                    log('error', str(e))
                finally:
                    try:
                        if self.ws and self.ws.sock:
                            self.ws.sock.close()
                    except websocket.WebSocketException:
                        pass

                    self.ws = None

            flovis_t = Thread(name='flovis_websocket', target=run)
            flovis_t.start()

            return True
        except (websocket._exceptions.WebSocketBadStatusException, socket.gaierror) as e:
            log('error', e)

            self.ws = None
            return False

    def stage(self, name, site, post_id, data=None):
        event_id = str(uuid.uuid4())
        msg_data = {'action': 'stage', 'name': name, 'site': site, 'post_id': post_id, 'event_id': event_id}

        if data is not None:
            msg_data['data'] = data

        for retries in range(1, 5):
            try:
                if self.ws is not None:
                    self.ws.send(json.dumps(msg_data))
                break
            except (websocket.WebSocketConnectionClosedException, ssl.SSLError):
                if retries == 5:
                    raise  # Actually raise the initial error if we've exceeded number of init retries
                self.ws = None
                self._init_websocket()
