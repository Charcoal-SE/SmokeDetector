from chatexchange import events
from chatexchange.messages import Message
from chatexchange_extension import Client
import collections
import itertools
import os.path
import pickle
import queue
import regex
import requests
import sys
import threading
import time
import yaml

import datahandling
import metasmoke
import classes.feedback
from helpers import log
from excepthook import log_exception
from globalvars import GlobalVars
from parsing import fetch_post_id_and_site_from_url, fetch_post_url_from_msg_content, fetch_owner_url_from_msg_content
from tasks import Tasks

LastMessages = collections.namedtuple("LastMessages", ["messages", "reports"])


class RoomData:
    def __init__(self, room, block_time, deletion_watcher):
        self.room = room
        self.block_time = block_time
        self.deletion_watcher = deletion_watcher


class CmdException(Exception):
    pass


_prefix_commands = {}
_reply_commands = {}

_clients = {
    "stackexchange.com": None,
    "stackoverflow.com": None,
    "meta.stackexchange.com": None
}

_command_rooms = set()
_watcher_rooms = set()
_room_roles = {}
_privileges = {}

_global_block = -1
_rooms = {}
_last_messages = LastMessages({}, collections.OrderedDict())
_msg_queue = queue.Queue()

_pickle_run = threading.Event()


def init(username, password):
    global _clients
    global _rooms
    global _room_data
    global _last_messages

    for site in _clients.keys():
        client = Client(site)

        for retry in range(10):
            try:
                client.login(username, password)
                break
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                log('debug', 'Login error {}: {}'.format(exc_type.__name__, exc_obj))
        else:
            raise Exception("Failed to log into " + site + ", max retries exceeded")

        _clients[site] = client

    if os.path.exists("rooms_custom.yml"):
        parse_room_config("rooms_custom.yml")
    else:
        parse_room_config("rooms.yml")

    if not GlobalVars.standby_mode:
        join_command_rooms()

    if os.path.isfile("messageData.p"):
        try:
            _last_messages = pickle.load(open("messageData.p", "rb"))
        except EOFError:
            pass

    threading.Thread(name="pickle ---rick--- runner", target=pickle_last_messages, daemon=True).start()
    threading.Thread(name="message sender", target=send_messages, daemon=True).start()


def join_command_rooms():
    for site, roomid in _command_rooms:
        room = _clients[site].get_room(roomid)
        deletion_watcher = (site, roomid) in _watcher_rooms

        room.join()
        room.watch_socket(on_msg)
        _rooms[(site, roomid)] = RoomData(room, -1, deletion_watcher)


def parse_room_config(path):
    with open(path, "r") as room_config:
        room_dict = yaml.load(room_config.read())

        for site, site_rooms in room_dict.items():
            for roomid, room in site_rooms.items():
                room_identifier = (site, roomid)
                _privileges[room_identifier] = set(room["privileges"]) if "privileges" in room else set()

                if "commands" in room and room["commands"]:
                    _command_rooms.add(room_identifier)

                if "watcher" in room and room["watcher"]:
                    _watcher_rooms.add(room_identifier)

                if "msg_types" in room:
                    add_room(room_identifier, room["msg_types"])


def add_room(room, roles):
    for role in roles:
        if role not in _room_roles:
            _room_roles[role] = set()

        _room_roles[role].add(room)


def pickle_last_messages():
    while True:
        _pickle_run.wait()
        _pickle_run.clear()

        with open("messageData.p", "wb") as pickle_file:
            pickle.dump(_last_messages, pickle_file)


def send_messages():
    while True:
        room, msg, report_data = _msg_queue.get()

        full_retries = 0

        while full_retries < 3:
            try:
                response = room.room._client._do_action_despite_throttling(("send", room.room.id, msg)).json()

                if "id" in response:
                    identifier = (room.room._client.host, room.room.id)
                    message_id = response["id"]

                    if identifier not in _last_messages.messages:
                        _last_messages.messages[identifier] = collections.deque((message_id,))
                    else:
                        last = _last_messages.messages[identifier]

                        if len(last) > 100:
                            last.popleft()

                        last.append(message_id)

                    if report_data:
                        _last_messages.reports[(room.room._client.host, message_id)] = report_data

                        if len(_last_messages.reports) > 50:
                            _last_messages.reports.popitem(last=False)

                        if room.deletion_watcher:
                            callback = room.room._client.get_message(message_id).delete

                            GlobalVars.deletion_watcher.subscribe(report_data[0], callback=callback, timeout=120)

                    _pickle_run.set()

                break
            except requests.exceptions.HTTPError:
                full_retries += 1

        _msg_queue.task_done()


def on_msg(msg, client):
    if not isinstance(msg, events.MessagePosted) and not isinstance(msg, events.MessageEdited):
        return

    message = msg.message
    if message.owner.id == client._br.user_id:
        return
    if message.content.startswith("<div class='partial'>"):
        message.content = message.content[21:]
        if message.content.endswith("</div>"):
            message.content = message.content[:-6]

    room_data = _rooms[(client.host, message.room.id)]

    if message.parent:
        try:
            if message.parent.owner.id == client._br.user_id:
                strip_mention = regex.sub("^(<span class=(\"|')mention(\"|')>)?@.*?(</span>)? ", "", message.content)
                cmd = GlobalVars.parser.unescape(strip_mention)

                result = dispatch_reply_command(message.parent, message, cmd)

                if result:
                    _msg_queue.put((room_data, ":{} {}".format(message.id, result), None))
        except ValueError:
            pass
    elif message.content.lower().startswith("sd "):
        result = dispatch_shorthand_command(message)

        if result:
            _msg_queue.put((room_data, ":{} {}".format(message.id, result), None))
    elif message.content.startswith("!!/"):
        result = dispatch_command(message)

        if result:
            _msg_queue.put((room_data, ":{} {}".format(message.id, result), None))
    elif classes.feedback.FEEDBACK_REGEX.search(message.content) \
            and is_privileged(message.owner, message.room) and datahandling.last_feedbacked:
            ids, expires_in = datahandling.last_feedbacked

            if time.time() < expires_in:
                Tasks.do(metasmoke.Metasmoke.post_auto_comment, message.content_source, message.owner, ids=ids)


def tell_rooms_with(prop, msg, notify_site="", report_data=None):
    tell_rooms(msg, (prop,), (), notify_site=notify_site, report_data=report_data)


def tell_rooms_without(prop, msg, notify_site="", report_data=None):
    tell_rooms(msg, (), (prop,), notify_site=notify_site, report_data=report_data)


def tell_rooms(msg, has, hasnt, notify_site="", report_data=None):
    global _rooms

    msg = msg.rstrip()
    target_rooms = set()

    for prop_has in has:
        if isinstance(prop_has, tuple):
            target_rooms.add(prop_has)

        if prop_has not in _room_roles:
            continue

        for room in _room_roles[prop_has]:
            if all(map(lambda prop: prop not in _room_roles or room not in _room_roles[prop], hasnt)):
                if room not in _rooms:
                    site, roomid = room
                    deletion_watcher = room in _watcher_rooms

                    new_room = _clients[site].get_room(roomid)
                    new_room.join()

                    _rooms[room] = RoomData(new_room, -1, deletion_watcher)

                target_rooms.add(room)

    for room_id in target_rooms:
        room = _rooms[room_id]

        if notify_site:
            pings = datahandling.get_user_names_on_notification_list(room.room._client.host,
                                                                     room.room.id,
                                                                     notify_site,
                                                                     room.room._client)

            msg_pings = datahandling.append_pings(msg, pings)
        else:
            msg_pings = msg

        timestamp = time.time()

        if room.block_time < timestamp and _global_block < timestamp:
            if report_data and "delay" in _room_roles and room_id in _room_roles["delay"]:
                def callback(room=room, msg=msg_pings):
                    post = fetch_post_id_and_site_from_url(report_data[0])[0:2]

                    if not datahandling.is_false_positive(post) and not datahandling.is_ignored_post(post):
                        _msg_queue.put((room, msg, report_data))

                task = Tasks.later(callback, after=300)

                GlobalVars.deletion_watcher.subscribe(report_data[0], callback=task.cancel)
            else:
                _msg_queue.put((room, msg_pings, report_data))


def get_last_messages(room, count):
    identifier = (room._client.host, room.id)

    if identifier not in _last_messages.messages:
        return

    for msg_id in itertools.islice(reversed(_last_messages.messages[identifier]), count):
        yield room._client.get_message(msg_id)


def get_report_data(message):
    identifier = (message._client.host, message.id)

    if identifier in _last_messages.reports:
        return _last_messages.reports[identifier]
    else:
        post_url = fetch_post_url_from_msg_content(message.content_source)

        if post_url:
            return (post_url, fetch_owner_url_from_msg_content(message.content_source))


def is_privileged(user, room):
    return user.id in _privileges[(room._client.host, room.id)] or user.is_moderator


def block_room(room_id, site, time):
    global _global_block

    if room_id is None:
        _global_block = time
    else:
        _rooms[(site, room_id)].block_time = time


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
                try:
                    processed_args.extend([coerce(arg) if arg else arg for coerce, arg in zip(type_signature, args)])
                except ValueError as e:
                    return "Invalid input type given for an argument"

                if give_name:
                    result = func(*processed_args, alias_used=alias_used)
                else:
                    result = func(*processed_args)

                return result if not quiet_action else ""
            except CmdException as e:
                return str(e)
            except Exception:  # Everything else
                log_exception(*sys.exc_info())
                return "I hit an error while trying to run that command; run `!!/errorlogs` for details."

        cmd = (f, arity if arity else (len(type_signature), len(type_signature)))

        if reply:
            _reply_commands[func.__name__] = cmd

            for alias in aliases:
                _reply_commands[alias] = cmd
        else:
            _prefix_commands[func.__name__] = cmd

            for alias in aliases:
                _prefix_commands[alias] = cmd

        return f

    return decorator


def message(msg):
    assert isinstance(msg, Message)
    return msg


def dispatch_command(msg):
    command_parts = GlobalVars.parser.unescape(msg.content).split(" ", 1)

    if len(command_parts) == 2:
        cmd, args = command_parts
    else:
        cmd, = command_parts
        args = ""

    if len(cmd) == 3:
        return

    command_name = cmd[3:].lower()

    quiet_action = command_name[-1] == "-"
    command_name = regex.sub(r"[[:punct:]]*$", "", command_name)

    if command_name not in _prefix_commands:
        return "No such command '{}'.".format(command_name)
    else:
        func, (min_arity, max_arity) = _prefix_commands[command_name]

        if max_arity == 0:
            return func(original_msg=msg, alias_used=command_name, quiet_action=quiet_action)
        elif max_arity == 1:
            if min_arity == 1 and not args:
                return "Missing an argument."

            return func(args or None, original_msg=msg, alias_used=command_name, quiet_action=quiet_action)
        else:
            args = args.split()

            if len(args) < min_arity:
                return "Too few arguments."
            elif len(args) > max_arity:
                return "Too many arguments."
            else:
                args.extend([None] * (max_arity - len(args)))
                return func(*args, original_msg=msg, alias_used=command_name, quiet_action=quiet_action)


def dispatch_reply_command(msg, reply, full_cmd):
    command_parts = full_cmd.lower().split(" ", 1)

    if len(command_parts) == 2:
        cmd, args = command_parts
    else:
        cmd, = command_parts
        args = ""

    quiet_action = cmd[-1] == "-"
    cmd = regex.sub(r"\W*$", "", cmd)

    if cmd in _reply_commands:
        func, (min_arity, max_arity) = _reply_commands[cmd]

        assert min_arity == 1

        if max_arity == 1:
            return func(msg, original_msg=reply, alias_used=cmd, quiet_action=quiet_action)
        elif max_arity == 2:
            return func(msg, args, original_msg=reply, alias_used=cmd, quiet_action=quiet_action)
        else:
            args = args.split()
            args.extend([None] * (max_arity - len(args)))

            return func(msg, *args, original_msg=reply, alias_used=cmd, quiet_action=quiet_action)
    elif is_privileged(reply.owner, reply.room):
        post_data = get_report_data(msg)

        if post_data:
            Tasks.do(metasmoke.Metasmoke.post_auto_comment, full_cmd, reply.owner, url=post_data[0])


def dispatch_shorthand_command(msg):
    commands = GlobalVars.parser.unescape(msg.content[3:]).lower().split()

    if len(commands) == 0:
        return

    output = []
    processed_commands = []

    for cmd in commands:
        count, cmd = regex.match(r"^(\d*)(.*)", cmd).groups()

        for _ in range(int(count) if count else 1):
            processed_commands.append(cmd)

    should_return_output = False

    for current_command, message in zip(processed_commands, get_last_messages(msg.room, len(processed_commands))):
        if current_command == "-":
            output.append("[:{}] <skipped>".format(message.id))
        else:
            result = dispatch_reply_command(message, msg, current_command)

            if result:
                should_return_output = True
                output.append("[:{}] {}".format(message.id, result))
            else:
                output.append("[:{}] <processed without return value>".format(message.id))

    return "\n".join(output) if should_return_output else ""
