# coding=utf-8
from chatexchange import client, events, rooms
import sys
from datetime import datetime
from helpers import log


class Room(rooms.Room):
    def watch_socket(self, event_callback):
        self._client.last_activity = datetime.utcnow()

        def on_activity(activity):
            self._client.last_activity = datetime.utcnow()

            for event in self._events_from_activity(activity, self.id):
                if isinstance(event, events.MessageEdited):
                    del event.message.content_source

                event_callback(event, self._client)

        return self._client._br.watch_room_socket(self.id, on_activity)


class Client(client.Client):
    def __init__(self, host):
        super().__init__(host)
        self.last_activity = None

    def get_room(self, room_id, **attrs_to_set):
        return self._get_and_set_deduplicated(
            Room, room_id, self._rooms, attrs_to_set)
