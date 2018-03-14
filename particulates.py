from websocket_server import WebsocketServer
import threading
import json

class Particulates:
    socket_lock = threading.Lock()

    PORT=9001
    server = None

    def post_ingested(self, site, title, post_id):
        def f():
            self.socket_lock.acquire()
            self.server.send_message_to_all(json.dumps({"action": "new", "site": site, "post_id": post_id, "title": title}))
            self.socket_lock.release()

        t = threading.Thread(name="Particulate - Ingested: " + str(post_id), target=f).start()

    def in_stage(self, post_id, site, stage):
        def f():
            self.socket_lock.acquire()
            self.server.send_message_to_all(json.dumps({"action": "moved", "stage": stage, "post_id": post_id, "site": site}))
            self.socket_lock.release()

        t = threading.Thread(name="Particulate - Staged: " + str(post_id), target=f).start()

    def dropped(self, post_id, site):
        def f():
            self.socket_lock.acquire()
            self.server.send_message_to_all(json.dumps({"action": "dropped", "post_id": post_id, "site": site}))
            self.socket_lock.release()

        t = threading.Thread(name="Particulate - Dropped: " + str(post_id), target=f).start()

    def start_server(self):
        # Called for every client connecting (after handshake)
        def new_client(client, server):
            print("Particulate client connected")


        # Called for every client disconnecting
        def client_left(client, server):
            print("Particulate lient disconnected")

        self.server = WebsocketServer(self.PORT)
        self.server.set_fn_new_client(new_client)
        self.server.set_fn_client_left(client_left)

        particulate_server_t = threading.Thread(name="metasmoke websocket", target=self.server.run_forever)
        particulate_server_t.start()
