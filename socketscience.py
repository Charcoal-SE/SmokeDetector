# coding=utf-8
import time
import random
import base64
import msgpack
import regex
import chatcommunicate
from globalvars import GlobalVars
from helpers import log
from tasks import Tasks


class SocketScience:
    """
    Use this class to send application data directly to other Smokey instances. This is intended for configuration or
    co-ordination data, etc - it is not for human-readable messages.

    Call SocketScience.send(payload) to send data. payload is a dict; use a key for each type of data (so, for example,
    you could send {'ping': time.time(), 'metasmoke_status': 'down'} to send two distinct message types in one payload.
    Clients can register callbacks for these message types to be notified and perform actions when they come in.

    Code example:

        def ping_callback(ping_data):
            log('debug', '{} pinged at {}'.format(ping_data['location'], ping_data['time'])

        SocketScience.register('ping', ping_callback)

        SocketScience.send({'ping': {'location': GlobalVars.location, 'time': time.time()}})
    """

    _pings = []
    _switch_task = None
    _callbacks = {}

    @classmethod
    def send(cls, payload, single_message=True):
        encoded = base64.b64encode(msgpack.dumps(payload)).decode("utf-8")

        message_id = random.randint(0, 9999)
        content = ".\n\u0002{:04}{}\u0003".format(message_id, encoded)
        chatcommunicate.tell_rooms_with("direct", content)

    @classmethod
    def receive(cls, content):
        content = content.strip()

        if content.startswith(".\n\u0002"):
            decoded = msgpack.loads(base64.b64decode(content[7:-1]))
            SocketScience.handle(decoded)

        else:
            log('warn', 'SocketScience received malformed direct message')
            log('debug', content)

    @classmethod
    def register(cls, prop, cb):
        if prop not in cls._callbacks:
            cls._callbacks[prop] = []

        cls._callbacks[prop].append(cb)

    @classmethod
    def handle(cls, content):
        for k, d in content.items():
            if k in cls._callbacks:
                for cb in cls._callbacks[k]:
                    cb(d)

        if "metasmoke_state" in content:
            if content["metasmoke_state"] == "down":
                log('info', "{} says metasmoke is down, switching to active ping monitoring."
                            .format(content["location"]))
                chatcommunicate.tell_rooms_with("debug", "{} says metasmoke is down,".format(content["location"]) +
                                                         " switching to active ping monitoring.")
                # This is an exception, to prevent circular import.
                # Other classes should not do the same. Always use Metasmoke.ms_down(). (20 May 2020)
                GlobalVars.MSStatus.set_down()
                Tasks.later(SocketScience.check_recent_pings, after=90)

            if content["metasmoke_state"] == "up":
                log('info', '{} says metasmoke is up, disabling ping monitoring.'.format(content["location"]))
                chatcommunicate.tell_rooms_with("debug", "{} says metasmoke is up,".format(content["location"]) +
                                                         " disabling ping monitoring.")
                # This is an exception, to prevent circular import.
                # Other classes should not do the same. Always use Metasmoke.ms_up(). (20 May 2020)
                GlobalVars.MSStatus.set_up()

        if "ping" in content:
            cls._pings.append({"timestamp": content["ping"], "location": content["location"]})
            if cls._switch_task is not None:
                cls._switch_task.cancel()

    @classmethod
    def check_recent_pings(cls):
        recent = cls._pings.sort(key=lambda p: p["timestamp"]).reverse()
        if len(recent) >= 1:
            most_recent = recent[0]["timestamp"]
            now = time.time()

        if now - most_recent >= 90 or len(recent) == 0:
            # No active Smokeys. Wait a random number of seconds, then switch to active.
            sleep = random.randint(0, 30)
            cls._switch_task = Tasks.later(SocketScience.switch_to_active, after=sleep)

    @staticmethod
    def switch_to_active():
        with GlobalVars.standby_mode_lock:
            GlobalVars.standby_mode = False
        chatcommunicate.tell_rooms_with("debug", GlobalVars.location + " entering autonomous failover.",
                                        notify_site="/failover")
