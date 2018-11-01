import time
import random
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

    _incomplete_messages = {}
    _pings = []
    _switch_task = None
    _callbacks = {}

    @staticmethod
    def send(payload, single_message=True):
        encoded = msgpack.dumps(payload)

        if single_message:
            message_id = random.randint(0, 9999)
            content = ".\n\u0002{:04}{}\u0003".format(message_id, encoded)
            chatcommunicate.tell_rooms_with("direct", content)
        else:
            # Messages can be 500 chars, but we need to leave space for control and message ident
            chunk_size = 485
            chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]
            message_id = "{:04}".format(random.randint(0, 9999))

            chunks[0] = "\u0002" + message_id + chunks[0]
            chunks[-1] = chunks[-1] + message_id + "\u0003"
            for n in range(1, len(chunks) - 1):
                chunks[n] = "\u0016" + message_id + chunks[n]

            for chunk in chunks:
                chatcommunicate.tell_rooms_with("direct", chunk)

    @staticmethod
    def receive(content):
        global _incomplete_messages

        content = content.strip()

        # U+0002 STX START OF TEXT; U+0003 ETX END OF TEXT; U+0016 SYN SYNCHRONOUS IDLE
        if content.startswith("\u0002") and content.endswith("\u0003"):
            decoded = msgpack.loads(content[5:-5])
            SocketScience.handle(decoded)

        # STX indicates probably valid, but incomplete - wait for another message with content and ETX.
        elif content.startswith("\u0002") and not content.endswith("\u0003"):
            message_id = int(content[1:5])
            _incomplete_messages[message_id] = content

        # No STX but ends with ETX, so probably a completion of a previous message.
        elif not content.startswith("\u0002") and content.endswith("\u0003"):
            message_id = int(content[-5:-1])
            complete = _incomplete_messages[message_id] + content
            decoded = msgpack.loads(regex.sub(r"^\u0002\d{4}|\d{4}\u0003", "", complete))
            SocketScience.handle(decoded)

        # Starts with SYN and message ID - continuation but not completion of previous message.
        elif content.startswith("\u0016"):
            message_id = int(content[1:5])
            _incomplete_messages[message_id] += content[5:]

        # Single multiline message instead of chunked.
        elif content.startswith(".\n\u0002"):
            decoded = msgpack.loads(regex.sub(r"\d{4}\u0003.*", "", content[7:]))
            SocketScience.handle(decoded)

        else:
            log('warn', 'SocketScience received malformed direct message')
            log('debug', content)

    @staticmethod
    def register(prop, cb):
        global _callbacks

        if prop not in _callbacks:
            _callbacks[prop] = []

        _callbacks[prop].append(cb)

    @staticmethod
    def handle(content):
        global _pings
        global _switch_task
        global _callbacks

        for k, d in content.items():
            if k in _callbacks:
                for cb in _callbacks[k]:
                    cb(d)

        if "metasmoke_state" in content:
            if content["metasmoke_state"] == "down":
                log('info', "{} says metasmoke is down, switching to active ping monitoring."
                            .format(content["location"]))
                GlobalVars.metasmoke_down = True
                Tasks.later(SocketScience.check_recent_pings, after=90)

            if content["metasmoke_state"] == "up":
                log('info', '{} says metasmoke is up, disabling ping monitoring.'.format(content["location"]))
                GlobalVars.metasmoke_down = False

        if "ping" in content:
            _pings.append({"timestamp": content["ping"], "location": content["location"]})
            if _switch_task is not None:
                _switch_task.cancel()

    @staticmethod
    def check_recent_pings():
        global _pings
        global _switch_task

        recent = _pings.sort(key=lambda p: p["timestamp"]).reverse()
        if len(recent) >= 1:
            most_recent = recent[0]["timestamp"]
            now = time.time()

        if now - most_recent >= 90 or len(recent) == 0:
            # No active Smokeys. Wait a random number of seconds, then switch to active.
            sleep = random.randint(0, 30)
            _switch_task = Tasks.later(SocketScience.switch_to_active, after=sleep)

    @staticmethod
    def switch_to_active():
        GlobalVars.standby_mode = False
        chatcommunicate.tell_rooms_with("debug", GlobalVars.location + " entering autonomous failover.",
                                        notify_site="/failover")
