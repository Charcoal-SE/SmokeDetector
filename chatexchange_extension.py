from ChatExchange.chatexchange import client, rooms
import sys
from helpers import log


class Room(rooms.Room):
    def send_message(self, text, length_check=True):
        if "no-chat" in sys.argv:
            log('info', "Blocked message to {0} due to no-chat setting: {1}".format(self.name, text))
            return

        if "charcoal-hq-only" not in sys.argv or int(self.id) == 11540:
            return rooms.Room.send_message(self, text, length_check)
        else:
            log('info', "Blocked message to {0} due to charcoal-hq-only setting: {1}".format(self.name, text))

    def watch_socket(self, event_callback):
        if "no-chat" in sys.argv:
            log('info', "Blocked socket connection to {0} due to no-chat setting".format(self.name))
            return

        if "charcoal-hq-only" not in sys.argv or int(self.id) == 11540:
            return rooms.Room.watch_socket(self, event_callback)
        else:
            log('info', "Blocked socket connection to {0} due to charcoal-hq-only setting".format(self.name))


class Client(client.Client):
    def get_room(self, room_id, **attrs_to_set):
        return self._get_and_set_deduplicated(
            Room, room_id, self._rooms, attrs_to_set)
