import random
from threading import Thread, Lock
from parsing import *
from datahandling import *
from metasmoke import Metasmoke
from globalvars import GlobalVars
import os
import re
from datetime import datetime
from utcdate import UtcDate
from apigetpost import api_get_post
from spamhandling import handle_spam, handle_user_with_all_spam
from termcolor import colored
from findspam import FindSpam
from deletionwatcher import DeletionWatcher
from ChatExchange.chatexchange.messages import Message


# Please note: If new !!/ commands are added or existing ones are modified, don't forget to
# update the wiki at https://github.com/Charcoal-SE/SmokeDetector/wiki/Commands.

add_latest_message_lock = Lock()


def post_message_in_room(room_id_str, msg, length_check=True):
    if room_id_str == GlobalVars.charcoal_room_id:
        GlobalVars.charcoal_hq.send_message(msg, length_check)
    elif room_id_str == GlobalVars.meta_tavern_room_id:
        GlobalVars.tavern_on_the_meta.send_message(msg, length_check)
    elif room_id_str == GlobalVars.socvr_room_id:
        GlobalVars.socvr.send_message(msg, length_check)


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
    message += colored(" - " + ev.data['user_name'], attrs=['bold'])
    print message


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
    message_parts = content_source.split(" ")

    ev_user_name = ev.data["user_name"]
    ev_user_link = "//chat." + wrap2.host + "/users/" + str(ev.user.id)
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
            shortcut_messages.append(":" + str(latest_smokedetector_messages[-(i + 1)]) + " " + commands[i])
        reply = ""
        amount_none = 0
        amount_skipped = 0
        amount_unrecognized = 0
        length = len(shortcut_messages)
        for i in xrange(0, length):
            current_message = shortcut_messages[i]
            if length > 1:
                reply += str(i + 1) + ". "
            reply += "[" + current_message.split(" ")[0] + "] "
            if current_message.split(" ")[1] != "-":
                r = handle_commands(current_message.lower(), current_message.split(" "), ev_room, ev_room_name, ev_user_id, ev_user_name, wrap2, current_message, message_id)
                result = r
                if type(result) == tuple:
                    result = result[1]
                if result is not None and result is not False:
                    reply += result + os.linesep
                elif result is None:
                    reply += "<processed without return value>" + os.linesep
                    amount_none += 1
                elif result is False or r[0] is False:
                    reply += "<unrecognized command>" + os.linesep
                    amount_unrecognized += 1
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
        r = handle_commands(content_source.lower(), message_parts, ev_room, ev_room_name, ev_user_id, ev_user_name, wrap2, content_source, message_id)
        if type(r) != tuple:
            r = (True, r)
        if r[1] is not None:
            if wrap2.host + str(message_id) in GlobalVars.listen_to_these_if_edited:
                GlobalVars.listen_to_these_if_edited.remove(wrap2.host + str(message_id))
            message_with_reply = u":{} {}".format(message_id, r[1])
            if len(message_with_reply) <= 500 or "\n" in r[1]:
                ev.message.reply(r[1], False)
        if r[0] is False:
            add_to_listen_if_edited(wrap2.host, message_id)


def handle_commands(content_lower, message_parts, ev_room, ev_room_name, ev_user_id, ev_user_name, wrap2, content, message_id):
    message_url = "//chat." + wrap2.host + "/transcript/message/" + str(message_id)
    second_part_lower = "" if len(message_parts) < 2 else message_parts[1].lower()
    if second_part_lower == "f":
        second_part_lower = "fp-"
    if second_part_lower == "k":
        second_part_lower = "tpu-"
    if second_part_lower == "n":
        second_part_lower = "naa-"
    if re.compile("^:[0-9]+$").search(message_parts[0]):
        msg_id = int(message_parts[0][1:])
        msg = wrap2.get_message(msg_id)
        msg_content = msg.content_source
        quiet_action = ("-" in second_part_lower)
        if str(msg.owner.id) != GlobalVars.smokeDetector_user_id[ev_room] or msg_content is None:
            return
        post_url = fetch_post_url_from_msg_content(msg_content)
        post_site_id = fetch_post_id_and_site_from_msg_content(msg_content)
        if post_site_id is not None:
            post_type = post_site_id[2]
        else:
            post_type = None
        if (second_part_lower.startswith("false") or second_part_lower.startswith("fp")) \
                and is_privileged(ev_room, ev_user_id, wrap2):
            if post_site_id is None:
                return "That message is not a report."

            t_metasmoke = Thread(target=Metasmoke.send_feedback_for_post,
                                 args=(post_url, second_part_lower, ev_user_name, ev_user_id, ))
            t_metasmoke.start()

            add_false_positive((post_site_id[0], post_site_id[1]))
            user_added = False
            if second_part_lower.startswith("falseu") or second_part_lower.startswith("fpu"):
                url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                if url_from_msg is not None:
                    user = get_user_from_url(url_from_msg)
                    if user is not None:
                        add_whitelisted_user(user)
                        user_added = True
            if post_type == "question":
                if user_added and not quiet_action:
                    return "Registered question as false positive and whitelisted user."
                elif not quiet_action:
                    return "Registered question as false positive."
            elif post_type == "answer":
                if user_added and not quiet_action:
                    return "Registered answer as false positive and whitelisted user."
                elif not quiet_action:
                    return "Registered answer as false positive."
            try:
                msg.delete()
            except:
                pass
        if (second_part_lower.startswith("true") or second_part_lower.startswith("tp")) \
                and is_privileged(ev_room, ev_user_id, wrap2):
            if post_site_id is None:
                return "That message is not a report."

            t_metasmoke = Thread(target=Metasmoke.send_feedback_for_post,
                                 args=(post_url, second_part_lower, ev_user_name, ev_user_id, ))
            t_metasmoke.start()

            user_added = False
            if second_part_lower.startswith("trueu") or second_part_lower.startswith("tpu"):
                url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                if url_from_msg is not None:
                    user = get_user_from_url(url_from_msg)
                    if user is not None:
                        add_blacklisted_user(user, message_url, "http:" + post_url)
                        user_added = True
            if post_type == "question":
                if not quiet_action:
                    if user_added:
                        return "Blacklisted user and registered question as true positive."
                    return "Recorded question as true positive in metasmoke. Use `tpu` or `trueu` if you want to blacklist a user."
                else:
                    return None
            elif post_type == "answer":
                if not quiet_action:
                    if user_added:
                        return "Blacklisted user."
                    return "Recorded answer as true positive in metasmoke. If you want to blacklist the poster of the answer, use `trueu` or `tpu`."
                else:
                    return None
        if second_part_lower.startswith("ignore") and is_privileged(ev_room, ev_user_id, wrap2):
            if post_site_id is None:
                return "That message is not a report."

            t_metasmoke = Thread(target=Metasmoke.send_feedback_for_post,
                                 args=(post_url, second_part_lower, ev_user_name, ev_user_id, ))
            t_metasmoke.start()

            add_ignored_post(post_site_id[0:2])
            if not quiet_action:
                return "Post ignored; alerts about it will no longer be posted."
            else:
                return None
        if second_part_lower.startswith("naa") and is_privileged(ev_room, ev_user_id, wrap2):
            if post_site_id is None:
                return "That message is not a report."
            if post_type != "answer":
                return "That report was a question; questions cannot be marked as NAAs."

            t_metasmoke = Thread(target=Metasmoke.send_feedback_for_post,
                                 args=(post_url, second_part_lower, ev_user_name, ev_user_id, ))
            t_metasmoke.start()

            add_ignored_post(post_site_id[0:2])
            if not quiet_action:
                return "Recorded answer as an NAA in metasmoke."
            else:
                return None
        if (second_part_lower.startswith("delete") or second_part_lower.startswith("remove") or second_part_lower.startswith("gone") or second_part_lower.startswith("poof") or
                second_part_lower == "del") and is_privileged(ev_room, ev_user_id, wrap2):
            try:
                msg.delete()
            except:
                pass  # couldn't delete message
        if second_part_lower.startswith("postgone") and is_privileged(ev_room, ev_user_id, wrap2):
            edited = edited_message_after_postgone_command(msg_content)
            if edited is None:
                return "That's not a report."
            msg.edit(edited)
            return None
        if second_part_lower.startswith("why"):
            t = fetch_post_id_and_site_from_msg_content(msg_content)
            if t is None:
                t = fetch_user_from_allspam_report(msg_content)
                if t is None:
                    return "That's not a report."
                why = get_why_allspam(t)
                if why is None or why == "":
                    return "There is no `why` data for that user (anymore)."
                else:
                    return why
            post_id, site, _ = t
            why = get_why(site, post_id)
            if why is None or why == "":
                return "There is no `why` data for that post (anymore)."
            else:
                return why
    if content_lower.startswith("!!/addblu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            add_blacklisted_user((uid, val), message_url, "")
            return "User blacklisted (`{}` on `{}`).".format(uid, val)
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return "Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`."
    if content_lower.startswith("!!/rmblu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            if remove_blacklisted_user((uid, val)):
                return "User removed from blacklist (`{}` on `{}`).".format(uid, val)
            else:
                return "User is not blacklisted."
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."
    if content_lower.startswith("!!/isblu"):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            if is_blacklisted_user((uid, val)):
                return "User is blacklisted (`{}` on `{}`).".format(uid, val)
            else:
                return "User is not blacklisted (`{}` on `{}`).".format(uid, val)
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."
    if content_lower.startswith("!!/addwlu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            add_whitelisted_user((uid, val))
            return "User whitelisted (`{}` on `{}`).".format(uid, val)
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`."
    if content_lower.startswith("!!/rmwlu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid != -1 and val != "":
            if remove_whitelisted_user((uid, val)):
                return "User removed from whitelist (`{}` on `{}`).".format(uid, val)
            else:
                return "User is not whitelisted."
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."
    if content_lower.startswith("!!/iswlu"):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            if is_whitelisted_user((uid, val)):
                return "User is whitelisted (`{}` on `{}`).".format(uid, val)
            else:
                return "User is not whitelisted (`{}` on `{}`).".format(uid, val)
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`."
    if (content_lower.startswith("!!/allspam") or content_lower.startswith("!!/reportuser")) and is_privileged(ev_room, ev_user_id, wrap2):
        if len(message_parts) != 2:
            return False, "1 argument expected"
        url = message_parts[1]
        user = get_user_from_url(url)
        if user is None:
            return "That doesn't look like a valid user URL."
        why = u"User manually reported by *{}* in room *{}*.\n".format(ev_user_name, ev_room_name.decode('utf-8'))
        handle_user_with_all_spam(user, why)
        return None
    if content_lower.startswith("!!/report") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        crn, wait = can_report_now(ev_user_id, wrap2.host)
        if not crn:
            return "You can execute the !!/report command again in {} seconds. " \
                   "To avoid one user sending lots of reports in a few commands and slowing SmokeDetector down due to rate-limiting, " \
                   "you have to wait 30 seconds after you've reported multiple posts using !!/report, even if your current command just has one URL. " \
                   "(Note that this timeout won't be applied if you only used !!/report for one post)".format(wait)
        if len(message_parts) < 2:
            return False, "Not enough arguments."
        output = []
        index = 0
        urls = list(set(message_parts[1:]))
        if len(urls) > 5:
            return False, "To avoid SmokeDetector reporting posts too slowly, " \
                          "you can report at most 5 posts at a time. " \
                          "This is to avoid SmokeDetector's chat messages getting rate-limited too much, " \
                          "which would slow down reports."
        for url in urls:
            index += 1
            post_data = api_get_post(url)
            if post_data is None:
                output.append("Post {}: That does not look like a valid post URL.".format(index))
                continue
            if post_data is False:
                output.append("Post {}: Could not find data for this post in the API. It may already have been deleted.".format(index))
                continue
            user = get_user_from_url(post_data.owner_url)
            if user is not None:
                add_blacklisted_user(user, message_url, post_data.post_url)
            why = u"Post manually reported by user *{}* in room *{}*.\n".format(ev_user_name, ev_room_name.decode('utf-8'))
            batch = ""
            if len(urls) > 1:
                batch = " (batch report: post {} out of {})".format(index, len(urls))
            handle_spam(post_data.title, post_data.body, post_data.owner_name, post_data.site, post_data.post_url,
                        post_data.owner_url, post_data.post_id, ["Manually reported " + post_data.post_type + batch],
                        post_data.post_type == "answer", why, post_data.owner_rep, post_data.score, post_data.up_vote_count,
                        post_data.down_vote_count, post_data.question_id)
        if 1 < len(urls) > len(output):
            add_or_update_multiple_reporter(ev_user_id, wrap2.host, time.time())
        if len(output) > 0:
            return os.linesep.join(output)
        else:
            return None
    if content_lower.startswith("!!/wut"):
        return "Whaddya mean, 'wut'? Humans..."
    if content_lower.startswith("!!/lick"):
        return "*licks ice cream cone*"
    if content_lower.startswith("!!/alive"):
        if ev_room == GlobalVars.charcoal_room_id:
            return 'Of course'
        elif ev_room == GlobalVars.meta_tavern_room_id or ev_room == GlobalVars.socvr_room_id:
            return random.choice(['Yup', 'You doubt me?', 'Of course', '... did I miss something?',
                                  'plz send teh coffee',
                                  'Watching this endless list of new questions *never* gets boring',
                                  'Kinda sorta'])
    if content_lower.startswith("!!/rev") or content_lower.startswith("!!/ver"):
            return '[' + \
                GlobalVars.commit_with_author + \
                '](https://github.com/Charcoal-SE/SmokeDetector/commit/' + \
                GlobalVars.commit + \
                ')'
    if content_lower.startswith("!!/status"):
            now = datetime.utcnow()
            diff = now - UtcDate.startup_utc_date
            minutes, remainder = divmod(diff.seconds, 60)
            minutestr = "minutes" if minutes != 1 else "minute"
            return 'Running since {} UTC ({} {})'.format(GlobalVars.startup_utc, minutes, minutestr)
    if content_lower.startswith("!!/reboot"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            post_message_in_room(ev_room, "Goodbye, cruel world")
            os._exit(5)
    if content_lower.startswith("!!/stappit"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            post_message_in_room(ev_room, "Goodbye, cruel world")
            os._exit(6)
    if content_lower.startswith("!!/master"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            os._exit(8)
    if content_lower.startswith("!!/clearbl"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            if os.path.isfile("blacklistedUsers.txt"):
                os.remove("blacklistedUsers.txt")
                GlobalVars.blacklisted_users = []
                return "Kaboom, blacklisted users cleared."
            else:
                return "There are no blacklisted users at the moment."
    if content_lower.startswith("!!/block") and is_privileged(ev_room, ev_user_id, wrap2):
        room_id = message_parts[2] if len(message_parts) > 2 else "all"
        timeToBlock = message_parts[1] if len(message_parts) > 1 else "0"
        if not timeToBlock.isdigit():
            return False, "Invalid duration."
        else:
            timeToBlock = int(timeToBlock)
        timeToBlock = timeToBlock if 0 < timeToBlock < 14400 else 900
        GlobalVars.blockedTime[room_id] = time.time() + timeToBlock
        which_room = "globally" if room_id == "all" else "in room " + room_id
        report = "Reports blocked for {} seconds {}.".format(timeToBlock, which_room)
        if room_id != GlobalVars.charcoal_room_id:
            GlobalVars.charcoal_hq.send_message(report)
        return report
    if content_lower.startswith("!!/unblock") and is_privileged(ev_room, ev_user_id, wrap2):
        room_id = message_parts[2] if len(message_parts) > 2 else "all"
        GlobalVars.blockedTime[room_id] = time.time()
        which_room = "globally" if room_id == "all" else "in room " + room_id
        report = "Reports unblocked {}.".format(GlobalVars.blockedTime - time.time(), which_room)
        if room_id != GlobalVars.charcoal_room_id:
            GlobalVars.charcoal_hq.send_message(report)
        return report
    if content_lower.startswith("!!/errorlogs"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            count = -1
            if len(message_parts) != 2:
                return "The !!/errorlogs command requires 1 argument."
            try:
                count = int(message_parts[1])
            except ValueError:
                pass
            if count == -1:
                return "Invalid argument."
            logs_part = fetch_lines_from_error_log(count)
            post_message_in_room(ev_room, logs_part, False)
    if content_lower.startswith("!!/pull"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            r = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/git/refs/heads/master')
            latest_sha = r.json()["object"]["sha"]
            r = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/commits/' + latest_sha + '/statuses')
            states = []
            for status in r.json():
                state = status["state"]
                states.append(state)
            if "success" in states:
                os._exit(3)
            elif "error" in states or "failure" in states:
                return "CI build failed! :( Please check your commit."
            elif "pending" in states or not states:
                return "CI build is still pending, wait until the build has finished and then pull again."
    if content_lower.startswith("!!/help") or content_lower.startswith("!!/info"):
        return "I'm [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector), a bot that detects spam and offensive posts on the network and posts alerts to chat. [A command list is available here](https://github.com/Charcoal-SE/SmokeDetector/wiki/Commands)."
    if content_lower.startswith("!!/apiquota"):
        return "The current API quota remaining is {}.".format(GlobalVars.apiquota)
    if content_lower.startswith("!!/whoami"):
        if (ev_room in GlobalVars.smokeDetector_user_id):
            return "My id for this room is {}.".format(GlobalVars.smokeDetector_user_id[ev_room])
        else:
            return "I don't know my user ID for this room. (Something is wrong, and it's apnorton's fault.)"
    if content_lower.startswith("!!/location"):
        return GlobalVars.location
    if content_lower.startswith("!!/queuestatus"):
        post_message_in_room(ev_room, GlobalVars.bodyfetcher.print_queue(), False)
    if content_lower.startswith("!!/blame"):
        GlobalVars.users_chatting[ev_room] = list(set(GlobalVars.users_chatting[ev_room]))  # Make unique
        user_to_blame = random.choice(GlobalVars.users_chatting[ev_room])
        return u"It's [{}]({})'s fault.".format(user_to_blame[0], user_to_blame[1])
    if "smokedetector" in content_lower and "fault" in content_lower and ("xkcdbot" in ev_user_name.lower() or "bjb568" in ev_user_name.lower()):
        return "Liar"
    if content_lower.startswith("!!/coffee"):
        return "*brews coffee for @" + ev_user_name.replace(" ", "") + "*"
    if content_lower.startswith("!!/tea"):
        return "*brews a cup of " + random.choice(['earl grey', 'green', 'chamomile', 'lemon', 'darjeeling', 'mint']) + " tea for @" + ev_user_name.replace(" ", "") + "*"
    if content_lower.startswith("!!/brownie"):
        return "Brown!"
    if content_lower.startswith("!!/hats"):
        wb_end = datetime(2016, 1, 4, 0, 0, 0)
        now = datetime.utcnow()
        if wb_end > now:
            diff = wb_end - now
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            daystr = "days" if diff.days != 1 else "day"
            hourstr = "hours" if hours != 1 else "hour"
            minutestr = "minutes" if minutes != 1 else "minute"
            secondstr = "seconds" if seconds != 1 else "second"
            return "HURRY UP AND EARN MORE HATS! Winterbash will be over in {} {}, {} {}, {} {}, and {} {}. :(".format(diff.days, daystr, hours, hourstr, minutes, minutestr, seconds, secondstr)
        else:
            return "Winterbash is over. :("
    if content_lower.startswith("!!/test-a"):
        string_to_test = content[10:]
        if len(string_to_test) == 0:
            return "Nothing to test"
        result = "> "
        reasons, why = FindSpam.test_post("", string_to_test, "", "", True, False, 1, 0)
        if len(reasons) == 0:
            result += "Would not be caught for answer."
            return result
        result += ", ".join(reasons).capitalize()
        if why is not None and len(why) > 0:
            result += "\n----------\n"
            result += why
        return result
    if content_lower.startswith("!!/test"):
        string_to_test = content[8:]
        if len(string_to_test) == 0:
            return "Nothing to test"
        result = "> "
        reasons, why = FindSpam.test_post(string_to_test, string_to_test, string_to_test, "", False, False, 1, 0)
        if len(reasons) == 0:
            result += "Would not be caught for title, body, and username."
            return result
        result += ", ".join(reasons).capitalize()
        if why is not None and len(why) > 0:
            result += "\n----------\n"
            result += why
        return result
    if content_lower.startswith("!!/amiprivileged"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            return "Yes, you are a privileged user."
        else:
            return "No, you are not a privileged user."
    if content_lower.startswith("!!/notify"):
        if len(message_parts) != 3:
            return False, "2 arguments expected"
        user_id = int(ev_user_id)
        chat_site = wrap2.host
        room_id = message_parts[1]
        if not room_id.isdigit():
            return False, "Room ID is invalid."
        else:
            room_id = int(room_id)
        quiet_action = ("-" in message_parts[2])
        se_site = message_parts[2].replace('-', '')
        r, full_site = add_to_notification_list(user_id, chat_site, room_id, se_site)
        if r == 0:
            if not quiet_action:
                return "You'll now get pings from me if I report a post on `%s`, in room `%s` on `chat.%s`" % (full_site, room_id, chat_site)
            else:
                return None
        elif r == -1:
            return "That notification configuration is already registered."
        elif r == -2:
            return False, "The given SE site does not exist."
    if content_lower.startswith("!!/unnotify"):
        if len(message_parts) != 3:
            return False, "2 arguments expected"
        user_id = int(ev_user_id)
        chat_site = wrap2.host
        room_id = message_parts[1]
        if not room_id.isdigit():
            return False, "Room ID is invalid."
        else:
            room_id = int(room_id)
        quiet_action = ("-" in message_parts[2])
        se_site = message_parts[2].replace('-', '')
        r = remove_from_notification_list(user_id, chat_site, room_id, se_site)
        if r:
            if not quiet_action:
                return "I will no longer ping you if I report a post on `%s`, in room `%s` on `chat.%s`" % (se_site, room_id, chat_site)
            else:
                return None
        else:
            return "That configuration doesn't exist."
    if content_lower.startswith("!!/willibenotified"):
        if len(message_parts) != 3:
            return False, "2 arguments expected"
        user_id = int(ev_user_id)
        chat_site = wrap2.host
        room_id = message_parts[1]
        if not room_id.isdigit():
            return False, "Room ID is invalid"
        else:
            room_id = int(room_id)
        se_site = message_parts[2]
        will_be_notified = will_i_be_notified(user_id, chat_site, room_id, se_site)
        if will_be_notified:
            return "Yes, you will be notified for that site in that room."
        else:
            return "No, you won't be notified for that site in that room."
    if content_lower.startswith("!!/allnotificationsites"):
        if len(message_parts) != 2:
            return False, "1 argument expected"
        user_id = int(ev_user_id)
        chat_site = wrap2.host
        room_id = message_parts[1]
        if not room_id.isdigit():
            return False, "Room ID is invalid."
        sites = get_all_notification_sites(user_id, chat_site, room_id)
        if len(sites) == 0:
            return "You won't get notified for any sites in that room."
        else:
            return "You will get notified for these sites:\r\n" + ", ".join(sites)
    return False, None  # Unrecognized command, can be edited later.
