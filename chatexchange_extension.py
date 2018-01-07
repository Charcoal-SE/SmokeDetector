# coding=utf-8
from ChatExchange.chatexchange import browser, client, rooms
from datetime import datetime
import json
import os
import select
import threading
import websocket


class Room(rooms.Room):
    def watch_socket(self, event_callback):
        self._client.last_activity = datetime.utcnow()

        def on_activity(activity):
            self._client.last_activity = datetime.utcnow()

            for event in self._events_from_activity(activity, self.id):
                event_callback(event, self._client)

        return self._client._br.watch_room_socket(self.id, on_activity)


class Client(client.Client):
    def __init__(self, host):
        super().__init__(host)
        self.last_activity = None
        self._br = Browser()

    def _worker(self):
        pass

    def get_room(self, room_id, **attrs_to_set):
        return self._get_and_set_deduplicated(
            Room, room_id, self._rooms, attrs_to_set)


class Browser(browser.Browser):
    _poller = select.poll()
    _sockets_by_fd = {}

    _rid, _wid = os.pipe()
    _poller.register(_rid, select.POLLIN)

    @classmethod
    def _poll(cls):
        while True:
            for ready, event in cls._poller.poll():
                if ready == cls._rid:
                    os.read(cls._rid, 1)
                    continue

                sock, roomid, on_msg, on_hup = cls._sockets_by_fd[ready]

                if event & select.POLLHUP:
                    on_hup(roomid)
                else:
                    msg = sock.recv()

                    if msg:
                        on_msg(json.loads(msg))

    def leave_room(self, roomid):
        roomid = str(roomid)

        if roomid in self.sockets:
            fileno = self.sockets[roomid].fileno()

            Browser._sockets_by_fd.pop(fileno)
            self._poller.unregister(fileno)

        super().leave_room(roomid)
        os.write(self._wid, b"\x04")

    def watch_room_socket(self, roomid, callback):
        roomid = str(roomid)

        l = str(self.rooms[roomid]["eventtime"])
        ws_url = self.post_fkeyed("ws-auth", {"roomid": roomid}).json()["url"]

        sock = websocket.create_connection(ws_url + "?l=" + l, origin=self.chat_root)

        self.sockets[roomid] = sock
        Browser._sockets_by_fd[sock.fileno()] = (sock, roomid, callback, self._default_ws_recovery)
        Browser._poller.register(sock, select.POLLIN | select.POLLHUP)

        os.write(self._wid, b"\x04")

    def _default_ws_recovery(self, roomid):
        roomid = str(roomid)

        if roomid in self.sockets:
            super._default_ws_recovery(roomid)


threading.Thread(name="poller", target=Browser._poll, daemon=True).start()
