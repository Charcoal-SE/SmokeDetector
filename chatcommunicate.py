# coding=utf-8
import collections
import itertools
import os
import os.path
import pickle
import queue
import regex
import requests
import sys
import threading
import time
import yaml
import shlex

from chatexchange import events
from chatexchange.browser import LoginError
from chatexchange.messages import Message
from chatexchange_extension import Client

import datahandling
import metasmoke
import classes.feedback
from helpers import log
from excepthook import log_exception
from globalvars import GlobalVars
from parsing import fetch_post_id_and_site_from_url, fetch_post_url_from_msg_content, fetch_owner_url_from_msg_content
from tasks import Tasks
from socketscience import SocketScience


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


def init(username, password, try_cookies=True):
    global _clients
    global _rooms
    global _room_data
    global _last_messages

    for site in _clients.keys():
        client = Client(site)
        logged_in = False

        if try_cookies:
            if GlobalVars.cookies is None:
                datahandling._remove_pickle("cookies.p")
                GlobalVars.cookies = {}
            else:
                cookies = GlobalVars.cookies
                try:
                    if site in cookies and cookies[site] is not None:
                        client.login_with_cookie(cookies[site])
                        logged_in = True
                        log('debug', 'chat.{}: Logged in using cached cookies'.format(site))
                except LoginError as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    log('debug', 'chat.{}: Login error {}: {}'.format(site, exc_type.__name__, exc_obj))
                    log('debug', 'chat.{}: Falling back to credential-based login'.format(site))
                    del cookies[site]
                    datahandling.dump_cookies()

        if not logged_in:
            for retry in range(3):
                try:
                    GlobalVars.cookies[site] = client.login(username, password)
                    break
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    log('debug', 'chat.{}: Login error {}: {}'.format(site, exc_type.__name__, exc_obj))
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
        with open("messageData.p", "rb") as messages_file:
            try:
                _last_messages = pickle.load(messages_file)
            except EOFError:
                pass

    threading.Thread(name="pickle ---rick--- runner", target=pickle_last_messages, daemon=True).start()
    threading.Thread(name="message sender", target=send_messages, daemon=True).start()

    if try_cookies:
        datahandling.dump_cookies()


def join_command_rooms():
    for site, roomid in _command_rooms:
        room = _clients[site].get_room(roomid)
        deletion_watcher = (site, roomid) in _watcher_rooms

        room.join()
        room.watch_socket(on_msg)
        _rooms[(site, roomid)] = RoomData(room, -1, deletion_watcher)


def parse_room_config(path):
    with open(path, "r", encoding="utf-8") as room_config:
        room_dict = yaml.safe_load(room_config.read())

    with open("users.yml", "r", encoding="utf-8") as user_config:
        user_data = yaml.safe_load(user_config.read())

    inherits = []
    rooms = {}
    host_fields = {'stackexchange.com': 1, 'meta.stackexchange.com': 2, 'stackoverflow.com': 3}

    for site, site_rooms in room_dict.items():
        for roomid, room in site_rooms.items():
            room_identifier = (site, roomid)
            # print("Process {}".format(room_identifier))
            rooms[room_identifier] = room
            if "privileges" in room and "inherit" in room["privileges"]:
                inherits.append({'from': (room["privileges"]["inherit"]["site"],
                                          room["privileges"]["inherit"]["room"]), 'to': room_identifier})
                if "additional" in room["privileges"]:
                    _privileges[room_identifier] =\
                        set([user_data[x][host_fields[site]] for x in room["privileges"]["additional"]])
            elif "privileges" in room:
                _privileges[room_identifier] = set([user_data[x][host_fields[site]] for x in room["privileges"]])
            else:
                _privileges[room_identifier] = set()

            if "commands" in room and room["commands"]:
                _command_rooms.add(room_identifier)

            if "watcher" in room and room["watcher"]:
                _watcher_rooms.add(room_identifier)

            if "msg_types" in room:
                add_room(room_identifier, room["msg_types"])

    for inherit in inherits:
        if inherit["from"] in rooms:
            from_privs = _privileges[inherit["from"]]
            from_accounts = [k for k, v in user_data.items() if v[host_fields[inherit["from"][0]]] in from_privs]
            inherit_from = set([user_data[x][host_fields[inherit["to"][0]]] for x in from_accounts])

            if inherit["to"] in _privileges:
                before = _privileges[inherit["to"]]
                _privileges[inherit["to"]] = _privileges[inherit["to"]] | inherit_from
                # log('debug', '{} inheriting privs from {} with additional: before {}, after {}'.format(
                #     inherit["to"], inherit["from"], before, _privileges[inherit["to"]]))
            else:
                _privileges[inherit["to"]] = inherit_from
        else:
            log('warn', 'Room {} on {} specified privilege inheritance from {}, but no such room exists'.format(
                inherit["to"][1], inherit["to"][1], inherit["from"][1]))


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
        if len(msg) > 500 and "\n" not in msg:
            log('warn', 'Discarded the following message because it was over 500 characters')
            log('warn', msg)
            _msg_queue.task_done()
            continue

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
    global _room_roles

    if not isinstance(msg, events.MessagePosted) and not isinstance(msg, events.MessageEdited):
        return

    message = msg.message
    room_ident = (client.host, message.room.id)
    room_data = _rooms[room_ident]

    if message.owner.id == client._br.user_id:
        if 'direct' in _room_roles and room_ident in _room_roles['direct']:
            SocketScience.receive(message.content_source.replace("\u200B", "").replace("\u200C", ""))

        return

    if message.content.startswith("<div class='partial'>"):
        message.content = message.content[21:]
        if message.content.endswith("</div>"):
            message.content = message.content[:-6]

    if message.parent:
        try:
            if message.parent.owner.id == client._br.user_id:
                strip_mention = regex.sub("^(<span class=(\"|')mention(\"|')>)?@.*?(</span>)? ", "", message.content)
                cmd = GlobalVars.parser.unescape(strip_mention)

                result = dispatch_reply_command(message.parent, message, cmd)

                if result:
                    s = ":{}\n{}" if "\n" not in result and len(result) >= 488 else ":{} {}"
                    _msg_queue.put((room_data, s.format(message.id, result), None))
        except ValueError:
            pass
    elif message.content.lower().startswith("sd "):
        result = dispatch_shorthand_command(message)

        if result:
            s = ":{}\n{}" if "\n" not in result and len(result) >= 488 else ":{} {}"
            _msg_queue.put((room_data, s.format(message.id, result), None))
    elif message.content.startswith("!!/") or message.content.lower().startswith("sdc "):
        result = dispatch_command(message)

        if result:
            s = ":{}\n{}" if "\n" not in result and len(result) >= 488 else ":{} {}"
            _msg_queue.put((room_data, s.format(message.id, result), None))
    elif classes.feedback.FEEDBACK_REGEX.search(message.content) \
            and is_privileged(message.owner, message.room) and datahandling.last_feedbacked:
        ids, expires_in = datahandling.last_feedbacked

        if time.time() < expires_in:
            Tasks.do(metasmoke.Metasmoke.post_auto_comment, message.content_source, message.owner, ids=ids)
    elif 'direct' in _room_roles and room_ident in _room_roles['direct']:
        SocketScience.receive(message.content_source.replace("\u200B", "").replace("\u200C", ""))


def tell_rooms_with(prop, msg, notify_site="", report_data=None):
    tell_rooms(msg, (prop,), (), notify_site=notify_site, report_data=report_data)


def tell_rooms_without(prop, msg, notify_site="", report_data=None):
    tell_rooms(msg, (), (prop,), notify_site=notify_site, report_data=report_data)


def tell_rooms(msg, has, hasnt, notify_site="", report_data=None):
    global _rooms

    msg = msg.rstrip()
    target_rooms = set()

    # Go through the list of properties in "has" and add all rooms which have any of those properties
    # to the target_rooms set. _room_roles contains a list of rooms for each property.
    for prop_has in has:
        if isinstance(prop_has, tuple):
            # If the current prop_has is a tuple, then it's assumed to be a descriptor of a specific room.
            # The format is: (_client.host, room.id)
            target_rooms.add(prop_has)

        if prop_has not in _room_roles:
            # No rooms have this property.
            continue

        for room in _room_roles[prop_has]:
            if all(map(lambda prop: prop not in _room_roles or room not in _room_roles[prop], hasnt)):
                if room not in _rooms:
                    # If SD is not already in the room, then join the room.
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
    # print(_privileges)
    return user.id in _privileges[(room._client.host, room.id)] or (user.is_moderator and user.id != 435118)


def block_room(room_id, site, time):
    global _global_block

    if room_id is None:
        _global_block = time
    else:
        _rooms[(site, room_id)].block_time = time


class ChatCommand:
    def __init__(self, type_signature, reply=False, whole_msg=False, privileged=False,
                 arity=None, aliases=None, give_name=False):
        self.type_signature = type_signature
        self.reply = reply
        self.whole_msg = whole_msg
        self.privileged = privileged
        self.arity = arity
        self.aliases = aliases or []
        self.give_name = give_name
        self.__func__ = None

    def __call__(self, *args, original_msg=None, alias_used=None, quiet_action=False):
        disable_key = "no-" + self.__func__.__name__
        try:
            room_identifier = (original_msg.room._client.host, original_msg.room.id)
            if disable_key in _room_roles and room_identifier in _room_roles[disable_key]:
                return "This command is disabled in this room"
        except AttributeError:
            # Test cases in CI don't contain enough data
            pass

        if self.privileged and not is_privileged(original_msg.owner, original_msg.room):
            return GlobalVars.not_privileged_warning

        if self.whole_msg:
            processed_args = [original_msg]
        else:
            processed_args = []

        try:
            try:
                processed_args.extend(
                    [(coerce(arg) if arg else arg) for coerce, arg in zip(self.type_signature, args)])
            except ValueError as e:
                return "Invalid input type given for an argument"

            if self.give_name:
                result = self.__func__(*processed_args, alias_used=alias_used)
            else:
                result = self.__func__(*processed_args)

            return result if not quiet_action else ""
        except CmdException as e:
            return str(e)
        except Exception:  # Everything else
            log_exception(*sys.exc_info())
            return "I hit an error while trying to run that command; run `!!/errorlogs` for details."

    def __repr__(self):
        return "{}({}, reply={}, whole_msg={}, privileged={}, arity={}, aliases={}, give_name={})" \
            .format(
                self.__class__.__name__, ", ".join([s.__name__ for s in self.type_signature]), self.reply,
                self.whole_msg, self.privileged,
                self.arity, self.aliases, self.give_name
            )


def command(*type_signature, reply=False, whole_msg=False, privileged=False, arity=None, aliases=None, give_name=False):
    aliases = aliases or []

    def decorator(func):
        f = ChatCommand(type_signature, reply, whole_msg, privileged, arity, aliases, give_name)
        f.__func__ = func

        cmd = (f, arity if arity else (len(type_signature), len(type_signature)))

        if reply:
            _reply_commands[func.__name__.replace('_', '-')] = cmd

            for alias in aliases:
                _reply_commands[alias] = cmd
        else:
            _prefix_commands[func.__name__.replace("_", "-")] = cmd

            for alias in aliases:
                _prefix_commands[alias] = cmd

        return f

    return decorator


def message(msg):
    assert isinstance(msg, Message)
    return msg


def get_message(id, host="stackexchange.com"):
    if host not in _clients:
        raise ValueError("Invalid host")
    return _clients[host].get_message(int(id))


def dispatch_command(msg):
    command_parts = GlobalVars.parser.unescape(msg.content).split(" ", 1)
    try:
        if command_parts[0] == 'sdc':
            command_parts = command_parts[1].split(" ", 1)
        else:
            command_parts[0] = command_parts[0][3:]
    except IndexError:
        return "Invalid command: Use either `!!/cmd_name` or `sdc cmd_name`" +\
               " to run command `cmd_name`."

    if len(command_parts) == 2:
        cmd, args = command_parts
    else:
        cmd, = command_parts
        args = ""

    if cmd == "":
        return

    command_name = cmd.lower()

    quiet_action = command_name[-1] == "-"
    command_name = regex.sub(r"[[:punct:]]*$", "", command_name).replace("_", "-")

    if command_name not in _prefix_commands:
        return "No such command '{}'.".format(command_name)
    else:
        log('debug', 'Command received: ' + msg.content)
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


def dispatch_reply_command(msg, reply, full_cmd, comment=True):
    command_parts = full_cmd.split(" ", 1)

    if len(command_parts) == 2:
        cmd, args = command_parts
    else:
        cmd, = command_parts
        args = ""

    cmd = cmd.lower()

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
    elif comment and is_privileged(reply.owner, reply.room):
        post_data = get_report_data(msg)

        if post_data:
            Tasks.do(metasmoke.Metasmoke.post_auto_comment, full_cmd, reply.owner, url=post_data[0])


def dispatch_shorthand_command(msg):
    commands = shlex.split(GlobalVars.parser.unescape(msg.content).lower())[1:]

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
            result = dispatch_reply_command(message, msg, current_command, comment=False)

            if result:
                should_return_output = True
                output.append("[:{}] {}".format(message.id, result))
            else:
                output.append("[:{}] <processed without return value>".format(message.id))

    if should_return_output:
        return "\n".join(output)
