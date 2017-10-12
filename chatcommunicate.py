from ChatExchange.chatexchange import events
from ChatExchange.chatexchange.client import Client
from ChatExchange.chatexchange.messages import Message
import collections
import itertools
import json5
import os.path
import pickle
import regex
import threading
import time

import datahandling
from globalvars import GlobalVars
from parsing import fetch_post_url_from_msg_content, fetch_owner_url_from_msg_content


class RoomData:
    def __init__(self, room, lock, block_time, last_report_data):
        self.room = room
        self.lock = lock
        self.block_time = block_time
        self.last_report_data = last_report_data


LastMessages = collections.namedtuple("LastMessages", ["messages", "reports"])

_commands = {"reply": {}, "prefix": {}}

_clients = {
    "stackexchange.com": None,
    "stackoverflow.com": None,
    "meta.stackexchange.com": None
}

_room_roles = {"commands": set()}
_privileges = {}

_global_block = -1
_rooms = {}
_room_data = {}
_last_messages = LastMessages({}, {})

_pickle_run = threading.Event()


def init(username, password):
    global _clients
    global _rooms
    global _room_data
    global _last_messages

    for site in _clients.keys():
        client = Client(site)

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

    if not GlobalVars.standby_mode:
        for site, roomid in _room_roles["commands"]:
            room = _clients[site].get_room(roomid)

            room.join()
            room.watch_socket(lambda msg, client: on_msg(msg, client, room))
            _rooms[(site, roomid)] = RoomData(room, threading.Event(), -1, False)
            _rooms[(site, roomid)].lock.set()

    if os.path.isfile("messageData.p"):
        _last_messages = pickle.load(open("messageData.p", "rb"))

    threading.Thread(name="pickle ---rick--- runner", target=pickle_last_messages).start()


def parse_room_config():
    with open("rooms.json5", "r") as room_config:
        room_dict = json5.load(room_config)

        for site, site_rooms in room_dict.items():
            for roomid, room in site_rooms.items():
                room_identifier = (site, int(roomid))
                _privileges[room_identifier] = room["privileges"] if "privileges" in room else []

                if room["commands"]:
                    _room_roles["commands"].add(room_identifier)

                for perm in room["msg_types"]:
                    if perm not in _room_roles:
                        _room_roles[perm] = set()

                    _room_roles[perm].add(room_identifier)


def pickle_last_messages():
    while True:
        _pickle_run.wait()
        _pickle_run.clear()

        with open("messageData.p", "wb") as pickle_file:
            pickle.dump(_last_messages, pickle_file)


def on_msg(msg, client, room):
    if isinstance(msg, events.MessagePosted) or isinstance(msg, events.MessageEdited):
        message = msg.message

        if message.owner.id == client._br.user_id:
            identifier = (client.host, room.id)
            room_data = _rooms[identifier]

            room_data.lock.set()

            if identifier not in _last_messages.messages:
                _last_messages.messages[identifier] = collections.deque((message.id,))
            else:
                last = _last_messages.messages[identifier]

                if len(last) > 100:
                    last.popleft()

                last.append(message.id)

            if room_data.last_report_data is not None:
                _last_messages.reports[message.id] = room_data.last_report_data
                room_data.last_report_data = ()

            _pickle_run.set()
        elif message.parent and message.parent.owner.id == client._br.user_id:
            command = message.content.split(" ", 1)[1]
            result = dispatch_reply_command(message.parent, message, command, client)

            if result:
                message.reply(result)
        elif message.content.startswith("sd "):
            result = dispatch_shorthand_command(message, room, client)

            if result:
                message.reply(result)
        elif message.content.startswith("!!/"):
            result = dispatch_command(message, client)

            if result:
                message.reply(result)


def send_to_room(room, msg, report_data=()):
    timestamp = time.time()

    if room.block_time < timestamp and _global_block < timestamp:
        room.lock.wait()
        room.lock.clear()

        if report_data:
            room.last_report_data = report_data

        msg = msg.rstrip()

        room.room.send_message(msg)


def tell_rooms_with(prop, msg, notify_site="", report_data=()):
    tell_rooms(msg, (prop,), (), notify_site=notify_site, report_data=report_data)


def tell_rooms_without(prop, msg, notify_site="", report_data=()):
    tell_rooms(msg, (), (prop,), notify_site=notify_site, report_data=report_data)


def tell_rooms(msg, has, hasnt, notify_site="", report_data=()):
    global _rooms

    target_rooms = set()

    for prop_has in has:
        if prop_has not in _room_roles:
            continue

        for room in _room_roles[prop_has]:
            if all(map(lambda prop: prop not in _room_roles or room not in _room_roles[prop], hasnt)):
                if room not in _rooms:
                    site, roomid = room

                    new_room = _clients[site].get_room(roomid)
                    new_room.join()

                    _rooms[room] = RoomData(new_room, threading.Event(), -1, False)
                    _rooms[room].lock.set()

                target_rooms.add(_rooms[room])

    for room in target_rooms:
        if notify_site:
            pings = datahandling.get_user_names_on_notification_list(room.room._client.host,
                                                                     room.room.id,
                                                                     notify_site,
                                                                     room.room._client)

            msg = datahandling.append_pings(msg, pings)

        send_to_room(room, msg, report_data=report_data)


def get_last_messages(room, count):
    for msg_id in itertools.islice(reversed(_last_messages.messages[(room._client.host, room.id)]), count):
        yield room._client.get_message(msg_id)


def get_report_data(message):
    if message.id in _last_messages.reports:
        return _last_messages.reports[message.id]
    else:
        return (fetch_post_url_from_msg_content(message.content), fetch_owner_url_from_msg_content(message.content))


def is_privileged(user, room):
    return user.id in _privileges[(room._client.host, room.id)] or user.is_moderator


def block_room(room_id, site, time):
    if room_id is None:
        _global_block = time
    else:
        _room_data[(site, room_id)].block_time = time


def command(*type_signature, reply=False, whole_msg=False, privileged=False, arity=None, aliases=None, give_name=False):
    if aliases is None:
        aliases = []

    def decorator(func):
        def f(*args, original_msg=None, alias_used=None, quiet_action=False):
            if privileged and not is_privileged(original_msg.owner, original_msg.room):
                return GlobalVars.not_privileged_warning

            if whole_msg:
                processed_args = [original_msg]
            else:
                processed_args = []

            try:
                processed_args.extend([get_type(arg) if arg else arg for get_type, arg in zip(type_signature, args)])

                result = func(*processed_args, **({"alias_used": alias_used} if give_name else {}))
                return result if not quiet_action else ""
            except Exception as e:
                return str(e)

        cmd = (f, arity if arity else (len(type_signature), len(type_signature)))

        if reply:
            _commands["reply"][func.__name__] = cmd

            for alias in aliases:
                _commands["reply"][alias] = cmd
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

    command_name = cmd[3:].lower()

    quiet_action = command_name[-1] == "-"
    command_name = regex.sub(r"\W*$", "", command_name)

    if command_name not in _commands["prefix"]:
        return "No such command {}.".format(command_name)
    else:
        func, (min_arity, max_arity) = _commands["prefix"][command_name]

        if max_arity == 0:
            return func(original_msg=msg, alias_used=command_name, quiet_action=quiet_action)
        elif max_arity == 1:
            return func(args, original_msg=msg, alias_used=command_name, quiet_action=quiet_action)
        else:
            args = args.split() 
            args.extend([None] * (max_arity - len(args)))

            if len(args) < min_arity:
                return "Too few arguments."
            elif len(args) > max_arity:
                return "Too many arguments."
            else:
                return func(*args, original_msg=msg, alias_used=command_name, quiet_action=quiet_action)


def dispatch_reply_command(msg, reply, cmd, client):
    cmd = cmd.lower()

    quiet_action = cmd[-1] == "-"
    cmd = regex.sub(r"\W*$", "", cmd)

    if cmd not in _commands["reply"]:
        return "No such command {}.".format(cmd)
    else:
        func, arity = _commands["reply"][cmd]

        assert arity == (1, 1)

        return func(msg, original_msg=reply, alias_used=cmd, quiet_action=quiet_action)


def dispatch_shorthand_command(msg, room, client):
    commands = msg.content[3:].split()

    output = []
    processed_commands = []

    for cmd in commands:
        count, cmd = regex.match(r"^(\d*)(.*)", cmd).groups()

        for _ in range(int(count) if count else 1):
            processed_commands.append(cmd)

    should_return_output = False

    for current_command, message in zip(processed_commands, get_last_messages(room, len(processed_commands))):
        if current_command != "-":
            result = dispatch_reply_command(message, msg, current_command)

            if result:
                should_return_output = True
                output.append("[:{}] {}".format(message.id, result))
            else:
                output.append("[:{}] <processed without return value>".format(message.id))

    return "\n".join(output) if should_return_output else ""
