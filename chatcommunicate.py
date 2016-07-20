from threading import Thread, Lock
from parsing import *
from datahandling import *
from globalvars import GlobalVars
import os
import re
from termcolor import colored
from deletionwatcher import DeletionWatcher
from ChatExchange.chatexchange.messages import Message
import chatcommands
from helpers import Response

# Please note: If new !!/ commands are added or existing ones are modified, don't forget to
# update the wiki at https://github.com/Charcoal-SE/SmokeDetector/wiki/Commands.

add_latest_message_lock = Lock()

command_aliases = {
    "f": "fp-",
    "notspam": "fp-",
    "k": "tpu-",
    "spam": "tpu-",
    "rude": "tpu-",
    "abuse": "tpu-",
    "abusive": "tpu-",
    "offensive": "tpu-",
    "n": "naa-",
}


cmds = chatcommands.command_dict
subcmds = chatcommands.subcommand_dict


def is_smokedetector_message(user_id, room_id):
    return user_id == GlobalVars.smokeDetector_user_id[room_id]


def add_to_listen_if_edited(host, message_id):
    if host + str(message_id) not in GlobalVars.listen_to_these_if_edited:
        GlobalVars.listen_to_these_if_edited.append(host + str(message_id))
    if len(GlobalVars.listen_to_these_if_edited) > 500:
        GlobalVars.listen_to_these_if_edited = GlobalVars.listen_to_these_if_edited[-500:]


def print_chat_message(ev):
    message = colored("Chat message in " + ev.data["room_name"] + " (" + str(ev.data["room_id"]) + "): \"", attrs=['bold'])
    message += ev.data['content']
    message += "\""
    print message + colored(" - " + ev.data['user_name'], attrs=['bold'])


def special_room_watcher(ev, wrap2):
    if ev.type_id != 1:
        return
    ev_user_id = str(ev.data["user_id"])
    content_source = ev.message.content_source
    if is_smokedetector_message(ev_user_id, GlobalVars.charcoal_room_id):
        post_site_id = fetch_post_id_and_site_from_msg_content(content_source)
        post_url = fetch_post_url_from_msg_content(content_source)
        if post_site_id is not None and post_url is not None:
            t_check_websocket = Thread(target=DeletionWatcher.check_if_report_was_deleted, args=(post_site_id, post_url, ev.message))
            t_check_websocket.daemon = True
            t_check_websocket.start()


def watcher(ev, wrap2):
    if ev.type_id != 1 and ev.type_id != 2:
        return
    if ev.type_id == 2 and (wrap2.host + str(ev.message.id)) not in GlobalVars.listen_to_these_if_edited:
        return

    print_chat_message(ev)

    ev_room = str(ev.data["room_id"])
    ev_user_id = str(ev.data["user_id"])
    ev_room_name = ev.data["room_name"].encode('utf-8')
    if ev.type_id == 2:
        ev.message = Message(ev.message.id, wrap2)
    content_source = ev.message.content_source
    message_id = ev.message.id
    if is_smokedetector_message(ev_user_id, ev_room):
        add_latest_message_lock.acquire()
        add_latest_smokedetector_message(ev_room, message_id)
        add_latest_message_lock.release()

        post_site_id = fetch_post_id_and_site_from_msg_content(content_source)
        post_url = fetch_post_url_from_msg_content(content_source)
        if post_site_id is not None and (ev_room == GlobalVars.meta_tavern_room_id or ev_room == GlobalVars.socvr_room_id):
            t_check_websocket = Thread(target=DeletionWatcher.check_if_report_was_deleted, args=(post_site_id, post_url, ev.message))
            t_check_websocket.daemon = True
            t_check_websocket.start()
    message_parts = re.split('[ ,]+', content_source)

    ev_user_name = ev.data["user_name"]
    ev_user_link = "//chat.{host}/users/{user_id}".format(host=wrap2.host, user_id=ev.user.id)
    if ev_user_name != "SmokeDetector":
        GlobalVars.users_chatting[ev_room].append((ev_user_name, ev_user_link))

    shortcut_messages = []
    if message_parts[0].lower() == "sd":
        message_parts = preprocess_shortcut_command(content_source).split(" ")
        latest_smokedetector_messages = GlobalVars.latest_smokedetector_messages[ev_room]
        commands = message_parts[1:]
        if len(latest_smokedetector_messages) == 0:
            ev.message.reply("I don't have any messages posted after the latest reboot.")
            return
        if len(commands) > len(latest_smokedetector_messages):
            ev.message.reply("I've only posted {} messages since the latest reboot; that's not enough to execute all commands. No commands were executed.".format(len(latest_smokedetector_messages)))
            return
        for i in xrange(0, len(commands)):
            shortcut_messages.append(u":{message} {command_name}".format(message=latest_smokedetector_messages[-(i + 1)], command_name=commands[i]))
        reply = ""
        amount_none = 0
        amount_skipped = 0
        amount_unrecognized = 0
        length = len(shortcut_messages)
        for i in xrange(0, length):
            current_message = shortcut_messages[i]
            if length > 1:
                reply += str(i + 1) + ". "
            reply += u"[{0}] ".format(current_message.split(" ")[0])
            if current_message.split(" ")[1] != "-":
                result = handle_commands(content_lower=current_message.lower(),
                                         message_parts=current_message.split(" "),
                                         ev_room=ev_room,
                                         ev_room_name=ev_room_name,
                                         ev_user_id=ev_user_id,
                                         ev_user_name=ev_user_name,
                                         wrap2=wrap2,
                                         content=current_message,
                                         message_id=message_id)
                if result.command_status and result.message:
                    reply += result.message + os.linesep
                if result.command_status is False:
                    reply += "<unrecognized command>" + os.linesep
                    amount_unrecognized += 1
                if result.message is None and result.command_status is not False:
                    reply += "<processed without return value>" + os.linesep
                    amount_none += 1

            else:
                reply += "<skipped>" + os.linesep
                amount_skipped += 1
        if amount_unrecognized == length:
            add_to_listen_if_edited(wrap2.host, message_id)
        if amount_none + amount_skipped + amount_unrecognized == length:
            reply = ""

        reply = reply.strip()
        if reply != "":
            message_with_reply = u":{} {}".format(message_id, reply)
            if len(message_with_reply) <= 500 or "\n" in reply:
                ev.message.reply(reply, False)
    else:
        result = handle_commands(content_lower=content_source.lower(),
                                 message_parts=message_parts,
                                 ev_room=ev_room,
                                 ev_room_name=ev_room_name,
                                 ev_user_id=ev_user_id,
                                 ev_user_name=ev_user_name,
                                 wrap2=wrap2,
                                 content=content_source,
                                 message_id=message_id)
        if result.message:
            if wrap2.host + str(message_id) in GlobalVars.listen_to_these_if_edited:
                GlobalVars.listen_to_these_if_edited.remove(wrap2.host + str(message_id))
            message_with_reply = u":{} {}".format(message_id, result.message)
            if len(message_with_reply) <= 500 or "\n" in result.message:
                ev.message.reply(result.message, False)
        if result.command_status is False:
            add_to_listen_if_edited(wrap2.host, message_id)


def handle_commands(content_lower, message_parts, ev_room, ev_room_name, ev_user_id, ev_user_name, wrap2, content, message_id):
    message_url = "//chat.{host}/transcript/message/{id}#{id}".format(host=wrap2.host, id=message_id)
    second_part_lower = "" if len(message_parts) < 2 else message_parts[1].lower()
    if command_aliases.get(second_part_lower):
        second_part_lower = command_aliases.get(second_part_lower)
    match = re.match(r"[!/]*[\w-]+", content_lower)
    command = match.group(0) if match else ""
    if re.compile("^:[0-9]{4,}$").search(message_parts[0]):
        msg_id = int(message_parts[0][1:])
        msg = wrap2.get_message(msg_id)
        msg_content = msg.content_source
        quiet_action = ("-" in second_part_lower)
        if str(msg.owner.id) != GlobalVars.smokeDetector_user_id[ev_room] or msg_content is None:
            return Response(command_status=False, message=None)
        post_url = fetch_post_url_from_msg_content(msg_content)
        post_site_id = fetch_post_id_and_site_from_msg_content(msg_content)
        if post_site_id is not None:
            post_type = post_site_id[2]
        else:
            post_type = None

        subcommand_parameters = {
            'msg_content': msg_content,
            'ev_room': ev_room,
            'ev_room_name': ev_room_name,
            'ev_user_id': ev_user_id,
            'ev_user_name': ev_user_name,
            'message_url': message_url,
            'msg': msg,
            'post_site_id': post_site_id,
            'post_type': post_type,
            'post_url': post_url,
            'quiet_action': quiet_action,
            'second_part_lower': second_part_lower,
            'wrap2': wrap2,
        }
        if second_part_lower not in subcmds:
            return Response(command_status=False, message=None) # Unrecognized subcommand

        return subcmds[second_part_lower](**subcommand_parameters)

    # Process additional commands
    command_parameters = {
        'content': content,
        'content_lower': content_lower,
        'ev_room': ev_room,
        'ev_room_name': ev_room_name,
        'ev_user_id': ev_user_id,
        'ev_user_name': ev_user_name,
        'message_parts': message_parts,
        'message_url': message_url,
        'wrap2': wrap2,
    }
    if command not in cmds:
        return Response(command_status=False, message=None)  # Unrecognized command, can be edited later.

    return cmds[command](**command_parameters)
