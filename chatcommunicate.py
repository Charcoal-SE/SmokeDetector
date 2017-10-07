from ChatExchange.chatexchange import client as chatclient, events as events, messages.Message as Message
import collections
import itertools
import json5
import os.path
import pickle
import regex
import threading

from globalvars import GlobalVars
from helpers import environ_or_none


RoomData = collections.namedtuple("RoomData", ["room", "lock", "block_time", "is_report"])

_commands = {"reply": {}, "prefix": {}}

_clients = {
    "stackexchange.com": None,
    "stackoverflow.com": None,
    "meta.stackexchange.com": None
}

_my_ids = {}
_room_roles = {}
_privileges = {}

_rooms = {}
_room_data = {}
_last_messages = {}

_pickle_run = threading.Event()


def init(username, password):
    global _clients
    global _rooms
    global _room_data

    for site in _clients.keys():
        client = chatclient.Client(site)

        for _ in range(10):
            try:
                client.login(username, password)
                break
            except:
                pass
        else:
            raise Exception("Failed to log into " + site)

        _clients[site] = client

    parse_room_config()

    for site, roomid in _room_roles["commands"]:
        room = _clients[site].get_room(roomid)

        room.join()
        room.watch(lambda msg, client: on_msg(msg, client, room))
        _rooms[(site, roomid)] = RoomData(room, threading.Event(), -1, False)

    if os.path.isfile("messageData.p"):
        _last_messages = pickle.load(open("messageData.p", "rb"))

    threading.Thread(name="pickle ---rick--- runner", target=pickle_last_messages).start()


def parse_room_config():
    with open("rooms.json5", "r") as room_config:
        room_dict = json5.load(room_config)

        for site, site_rooms in room_dict.items():
            for roomid, room in site_rooms.items():
                if roomid == "id":
                    _myids[site] = room
                else:
                    room_identifier = (site, roomid)

                    _privileges[room] = room["privileges"] if "privileges" in room else None

                    for perm in room["msg_types"]:
                        if perm not in _rooms_roles:
                            _room_roles[perm] = set()

                        _room_roles[perm].add(room_identifier)


def pickle_last_messages():
    while True:
        _pickle_run.wait()
        _pickle_run.clear()

        with open("../pickles/last_messages.pck", "wb") as pickle_file:
            pickle.dump(_last_messages, pickle_file)


def on_msg(msg, client, room):
    if isinstance(msg, events.MessagePosted) or isinstance(msg, events.MessageEdited):
        message = msg.message

        if message.owner.id == client._br.user_id:
            identifier = (client.host, room.id)

            _rooms[identifier].lock.clear()

            if identifier not in _last_messages:
                _last_messages[identifier] = collections.deque((message.id,))
            else:
                if len(_last_messages[identifier]) > 50:
                    _last_messages[identifier].popleft()

                _last_messages[identifier].append(message.id)

            _pickle_run.set()
        elif message.parent and message.parent.owner.id in config.my_ids:
            command = message.content.split(" ", 1)[1]

            message.reply(dispatch_reply_command(message.parent, message, command, client))
        elif message.content.startswith("sd "):
            message.reply(dispatch_shorthand_command(message, room, client))
        elif message.content.startswith("!!/"):
            message.reply(dispatch_command(message, client))


def send_to_room(room, msg, prefix=False):
    _rooms[(room.host, room)].lock.wait()

    msg = msg.rstrip()

    if prefix:
        msg = GlobalVars.chatmessage_prefix + msg

    _rooms[(room.host, room)].lock.set()
    room.send_message(msg)


def tell_rooms_with(prop, msg, prefix=False):
    tell_rooms(msg, (prop,), (), prefix=prefix)


def tell_rooms_without(prop, msg, prefix=False):
    tell_rooms(msg, (), (prop,), prefix=prefix)


def tell_rooms(msg, has, hasnt, prefix=False):
    global _rooms

    target_rooms = set()

    for prop_has in has:
        for room in _room_roles[prop_has]:
            if all(map(lambda prop_hasnt: room not in _room_roles[prop_hasnt], hasnt)):
                if room not in _rooms:
                    site, roomid = room

                    new_room = _clients[site].get_room(roomid)
                    new_room.join()

                    _rooms[room] = RoomData(new_room, threading.Event(), -1, False)

                target_rooms.add(_rooms[room].room)

    for room in target_rooms:
        send_to_room(room, msg, prefix=prefix)


def get_last_messages(room, count):
    for msg_id in itertools.islice(reversed(_last_messages[(room._client.host, room.id)]), count):
        yield room._client.get_message(msg_id)


def command(*type_signature, reply=False, whole_msg=False, privileged=False, arity=None, aliases=None, give_name=False):
    if aliases is None:
        aliases = []

    def decorator(func):
        def f(*args, original_msg=None, alias_used=None):
            try:
                processed_args = [get_type(arg) if arg else arg for get_type, arg in zip(type_signature, args)]
            except Exception as e:
                return str(e)

            if privileged and original_msg.user.id not in _privileges[original_msg.room.id]:
                return GlobalVars.not_privileged_warning

            if whole_msg:
                if give_name:
                    return func(original_msg, *processed_args, alias=alias_used)
                else:
                    return func(original_msg, *processed_args)
            else:
                if give_name:
                    return func(*processed_args, alias=alias_used)
                else:
                    return func(*processed_args)

        cmd = (f, arity if arity else (len(type_signature), len(type_signature)))

        if reply:
            _commands["reply"][func.__name__] = cmd

            for alias in aliases:
                _commands["reply"][alias] = command
        else:
            _commands["prefix"][func.__name__] = cmd

            for alias in aliases:
                _commands["prefix"][alias] = cmd

        return f

    return decorator


def message(msg):
    assert isinstance(msg, Message)
    return msg


def dispatch_command(msg, client):
    command_parts = msg.content.split(" ", 1)

    if len(command_parts) == 2:
        cmd, args = command_parts
    else:
        cmd, = command_parts
        args = ""

    command_name = cmd[len(config.command_prefix):].lower()

    if command_name not in _commands["prefix"]:
        return "No such command %s." % command_name
    else:
        func, min_arity, max_arity = _commands["prefix"][command_name]

        if max_arity == 0:
            return func(original_msg=msg)
        elif max_arity == 1:
            return func(args, original_msg=msg)
        else:
            args = args.split() 
            args.extend([None] * (max_arity - len(args)))

            if len(args) < min_arity:
                return "Too few arguments."
            elif len(args) > max_arity:
                return "Too many arguments."
            else:
                return func(*args, original_msg=msg)


def dispatch_reply_command(msg, reply, cmd, client):
    cmd = cmd.lower()

    if cmd not in _commands["reply"]:
        return "No such command {}.".format(cmd)
    else:
        func, arity = _commands["reply"][cmd]

        assert arity == 1

        return func(msg, original_msg=reply)


def dispatch_shorthand_command(msg, room, client):
    commands = msg.content[len(config.shorthand_prefix):].split()

    output = []
    processed_commands = []

    for cmd in commands:
        count, cmd = regex.match(r"^(\d*)(.*)", cmd).groups()

        for _ in range(int(count) if count else 1):
            processed_commands.append(cmd)

    for current_command, message in zip(processed_commands, get_last_messages(room, len(processed_commands))):
        if current_command != "-":
            output.append("[:{}] {}".format 
                          dispatch_reply_command(message, msg, current_command) or "<processed without return value>")

    return "\n".join(output)