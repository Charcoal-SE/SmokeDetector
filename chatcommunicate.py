import random
import time
from parsing import *
from datahandling import *
from bayesianfuncs import bayesian_learn_title
from globalvars import GlobalVars
import os
import re
from datetime import datetime
from utcdate import UtcDate
from apigetpost import api_get_post
from spamhandling import handle_spam

# Please note: If new !!/ commands are added or existing ones are modified, don't forget to
# update the wiki at https://github.com/Charcoal-SE/SmokeDetector/wiki/Commands.


def post_message_in_room(room_id_str, msg, length_check=True):
    if room_id_str == GlobalVars.charcoal_room_id:
        GlobalVars.charcoal_hq.send_message(msg, length_check)
    elif room_id_str == GlobalVars.meta_tavern_room_id:
        GlobalVars.tavern_on_the_meta.send_message(msg, length_check)


def is_smokedetector_message(user_id, room_id):
    return user_id == GlobalVars.smokeDetector_user_id[room_id]


def watcher(ev, wrap2):
    if ev.type_id != 1:
        return
    print(ev)
    ev_room = str(ev.data["room_id"])
    ev_user_id = str(ev.data["user_id"])
    content_source = ev.message.content_source
    if is_smokedetector_message(ev_user_id, ev_room):
        GlobalVars.latest_smokedetector_messages[ev_room].append(ev.message.id)
        if len(GlobalVars.latest_smokedetector_messages[ev_room]) > 5:
            GlobalVars.latest_smokedetector_messages[ev_room] = GlobalVars.latest_smokedetector_messages[ev_room][-5:]
    message_parts = content_source.split(" ")

    ev_user_name = ev.data["user_name"].encode('utf-8')
    GlobalVars.tavern_users_chatting.append(ev_user_name)

    shortcut = False
    shortcut_messages = []
    if message_parts[0].lower() == "sd":
        shortcut = True
        message_parts = preprocess_shortcut_command(content_source).split(" ")
        if len(GlobalVars.latest_smokedetector_messages[ev_room]) == 0:
            ev.message.reply("I don't have any messages posted after the latest reboot.")
            return
        commands = message_parts[1:]
        if len(commands) > 5:
            ev.message.reply("You can only execute five commands at one time.")
            return
        if len(commands) > len(GlobalVars.latest_smokedetector_messages[ev_room]):
            ev.message.reply("I haven't posted enough messages after the latest reboot to execute all commands.")
            return
        for i in range(0, len(commands)):
            shortcut_messages.append(":" + str(GlobalVars.latest_smokedetector_messages[ev_room][-(i + 1)]) + " " + commands[i])
    if not shortcut:
        r = handle_commands(content_source.lower(), message_parts, ev_room, ev_user_id, ev_user_name, wrap2)
        if r is not None:
            ev.message.reply(r)
    else:
        reply = ""
        amount_none = 0
        amount_skipped = 0
        length = len(shortcut_messages)
        for i in range(0, length):
            current_message = shortcut_messages[i]
            if length > 1:
                reply += str(i + 1) + ". "
            reply += "[" + current_message.split(" ")[0] + "] "
            if current_message.split(" ")[1] != "-":
                result = handle_commands(current_message.lower(), current_message.split(" "), ev_room, ev_user_id, ev_user_name, wrap2)
                if result is not None:
                    reply += result + os.linesep
                else:
                    reply += "<no return value>" + os.linesep
                    amount_none += 1
            else:
                reply += "<skipped>" + os.linesep
                amount_skipped += 1
        if amount_none + amount_skipped == length:
            reply = ""
        else:
            reply = reply.strip()
        if reply != "":
            ev.message.reply(reply)


def handle_commands(content_lower, message_parts, ev_room, ev_user_id, ev_user_name, wrap2):
    second_part_lower = "" if len(message_parts) < 2 else message_parts[1].lower()
    if re.compile(":[0-9]+").search(message_parts[0]):
        msg_id = int(message_parts[0][1:])
        msg = wrap2.get_message(msg_id)
        msg_content = None
        msg_content = msg.content_source
        quiet_action = ("-" in message_parts[1].lower())
        if str(msg.owner.id) != GlobalVars.smokeDetector_user_id[ev_room] or msg_content is None:
            return
        post_site_id = fetch_post_id_and_site_from_msg_content(msg_content)
        if post_site_id is not None:
            post_type = post_site_id[2]
        else:
            post_type = None
        if (second_part_lower.startswith("false") or second_part_lower.startswith("fp")) \
                and is_privileged(ev_room, ev_user_id, wrap2):
            if post_site_id is None:
                return "That message is not a report."
            add_false_positive((post_site_id[0], post_site_id[1]))
            user_added = False
            if message_parts[1].lower().startswith("falseu") or message_parts[1].lower().startswith("fpu"):
                url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                if url_from_msg is not None:
                    user = get_user_from_url(url_from_msg)
                    if user is not None:
                        add_whitelisted_user(user)
                        user_added = True
            learned = False
            if post_type == "question":
                learned = bayesian_learn_title(fetch_title_from_msg_content(msg_content), "good")
                if learned and user_added and not quiet_action:
                    return "Registered question as false positive, whitelisted user and added title to Bayesian doctype 'good'."
                elif learned and not quiet_action:
                    return "Registered question as false positive and added title to Bayesian doctype 'good'."
                elif not learned:
                    return "Registered question as false positive, but could not add title to Bayesian doctype 'good'."
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
            learned = False
            user_added = False
            if message_parts[1].lower().startswith("trueu") or message_parts[1].lower().startswith("tpu"):
                url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                if url_from_msg is not None:
                    user = get_user_from_url(url_from_msg)
                    if user is not None:
                        add_blacklisted_user(user)
                        user_added = True
            if post_type == "question":
                learned = bayesian_learn_title(fetch_title_from_msg_content(msg_content), "bad")
                if learned and user_added and not quiet_action:
                    return "Blacklisted user and registered question as true positive: added title to the Bayesian doctype 'bad'."
                elif learned and not quiet_action:
                    return "Registered question as true positive: added title to the Bayesian doctype 'bad'."
                elif not learned:
                    return "Something went wrong when registering question as true positive."
            elif post_type == "answer":
                if user_added and not quiet_action:
                    return "Blacklisted user."
                elif not user_added:
                    return "`true`/`tp` cannot be used for answers because their job is to add the title of the *question* to the Bayesian doctype 'bad'. If you want to blacklist the poster of the answer, use `trueu` or `tpu`."
        if second_part_lower.startswith("ignore") and is_privileged(ev_room, ev_user_id, wrap2):
            if post_site_id is None:
                return "That message is not a report."
            add_ignored_post(post_site_id[0:2])
            if not quiet_action:
                return "Post ignored; alerts about it will no longer be posted."
        if second_part_lower.startswith("delete") or second_part_lower.startswith("remove") or second_part_lower.startswith("gone") \
                and is_privileged(ev_room, ev_user_id, wrap2):
            try:
                msg.delete()
            except:
                pass  # couldn't delete message
    if content_lower.startswith("!!/addblu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            add_blacklisted_user((uid, val))
            return "User blacklisted (`%s` on `%s`)." % (uid, val)
        elif uid == -2:
            return "Error: %s" % val
        else:
            return "Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`."
    if content_lower.startswith("!!/rmblu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            if remove_blacklisted_user((uid, val)):
                return "User removed from blacklist (`%s` on `%s`)." % (uid, val)
            else:
                return "User is not blacklisted."
        elif uid == -2:
            return "Error: %s" % val
        else:
            return "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."
    if content_lower.startswith("!!/isblu"):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            if is_blacklisted_user((uid, val)):
                return "User is blacklisted. (`%s` on `%s`)." % (uid, val)
            else:
                return "User is not blacklisted. (`%s` on `%s`)." % (uid, val)
        elif uid == -2:
            return "Error: %s" % val
        else:
            return "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."
    if content_lower.startswith("!!/addwlu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            add_whitelisted_user((uid, val))
            return "User whitelisted (`%s` on `%s`)." % (uid, val)
        elif uid == -2:
            return "Error: %s" % val
        else:
            return "Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`."
    if content_lower.startswith("!!/rmwlu") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        uid, val = get_user_from_list_command(content_lower)
        if uid != -1 and val != "":
            if remove_whitelisted_user((uid, val)):
                return "User removed from whitelist (`%s` on `%s`)." % (uid, val)
            else:
                return "User is not whitelisted."
        elif uid == -2:
            return "Error: %s" % val
        else:
            return "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."
    if content_lower.startswith("!!/iswlu"):
        uid, val = get_user_from_list_command(content_lower)
        if uid > -1 and val != "":
            if is_whitelisted_user((uid, val)):
                return "User is whitelisted. (`%s` on `%s`)." % (uid, val)
            else:
                return "User is not whitelisted. (`%s` on `%s`)." % (uid, val)
        elif uid == -2:
            return "Error: %s" % val
        else:
            return "Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`."
    if content_lower.startswith("!!/report") \
            and is_privileged(ev_room, ev_user_id, wrap2):
        if len(message_parts) < 2:
            return "Not enough arguments."
        url = message_parts[1]
        post_data = api_get_post(url)
        if post_data is False:
            return "Could not find data for this post in the API. Check whether the post is not deleted yet."
        user = get_user_from_url(post_data.owner_url)
        if user is not None:
            add_blacklisted_user(user)
        bayesian_learn_title(post_data.title, "bad")
        handle_spam(post_data.title, post_data.owner_name, post_data.site, post_data.post_url,
                    post_data.owner_url, post_data.post_id, ["Manually reported " + post_data.post_type],
                    post_data.post_type == "answer")
    if content_lower.startswith("!!/wut"):
        return "Whaddya mean, 'wut'? Humans..."
    if content_lower.startswith("!!/lick"):
        return "*licks ice cream cone*"
    if content_lower.startswith("!!/alive"):
        if ev_room == GlobalVars.charcoal_room_id:
            return 'Of course'
        elif ev_room == GlobalVars.meta_tavern_room_id:
            return random.choice(['Yup', 'You doubt me?', 'Of course', '... did I miss something?',
                                  'plz send teh coffee',
                                  'Watching this endless list of new questions *never* gets boring',
                                  'Kinda sorta'])
    if content_lower.startswith("!!/rev"):
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
            return 'Running since %s UTC (%s %s)' % (GlobalVars.startup_utc, minutes, minutestr)
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
    if content_lower.startswith("!!/block"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            timeToBlock = content_lower[9:].strip()
            timeToBlock = int(timeToBlock) if timeToBlock else 0
            if 0 < timeToBlock < 14400:
                GlobalVars.blockedTime = time.time() + timeToBlock
            else:
                GlobalVars.blockedTime = time.time() + 900
            return "blocked"
    if content_lower.startswith("!!/unblock"):
        if is_privileged(ev_room, ev_user_id, wrap2):
            GlobalVars.blockedTime = time.time()
            return "unblocked"
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
    if content_lower.startswith("!!/help"):
        return "I'm [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector), a bot that detects spam and low-quality posts on the network and posts alerts to chat. [A command list is available here](https://github.com/Charcoal-SE/SmokeDetector/wiki/Commands)."
    if content_lower.startswith("!!/apiquota"):
        return GlobalVars.apiquota
    if content_lower.startswith("!!/location"):
        return GlobalVars.location
    if content_lower.startswith("!!/queuestatus"):
        post_message_in_room(ev_room, GlobalVars.bodyfetcher.print_queue(), False)
    if content_lower.startswith("!!/blame") and ev_room == GlobalVars.meta_tavern_room_id:
        GlobalVars.tavern_users_chatting = list(set(GlobalVars.tavern_users_chatting))  # Make unique
        user_to_blame = random.choice(GlobalVars.tavern_users_chatting)
        return "It's " + user_to_blame + "'s fault."
    if "smokedetector" in content_lower and "fault" in content_lower and ("xkcdbot" in ev_user_name.lower() or "bjb568" in ev_user_name.lower()):
        return "Liar"
    return None
