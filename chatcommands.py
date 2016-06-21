from globalvars import GlobalVars
from findspam import FindSpam
from datetime import datetime
from utcdate import UtcDate
from apigetpost import api_get_post
from datahandling import *
from chatcommunicate import *
from metasmoke import Metasmoke
from parsing import *
from spamhandling import handle_spam
from spamhandling import handle_user_with_all_spam
from threading import Thread, Lock
import random
import requests
import os
import time


# TODO: pull out code block to get user_id, chat_site, room_id into function
# TODO: Return result for all functions should be similar (tuple/named tuple?)
# TODO: Do we need uid == -2 check?  Turn into "is_user_valid" check
# TODO: Consistant return structure
#   if return...else return vs if return...return

# Functions go before the final dictionaries of command to function mappings

def is_report(post_site_id):
    """
    Checks if a post is a report
    :param post_site_id: Report to check
    :return: Boolean stating if it is a report
    """
    if post_site_id is None:
        return False
    return True


def send_metasmoke_feedback(post_url, second_part_lower, ev_user_name, ev_user_id):
    """
    Sends feedback to MetaSmoke
    :param post_url: The post url we are sending
    :param second_part_lower: Feedback
    :param ev_username: User name supplying the feedback
    :param ev_user_id: User ID supplying the feedback
    :return: None
    """
    t_metasmoke = Thread(target=Metasmoke.send_feedback_for_post,
                         args=(post_url, second_part_lower, ev_user_name, ev_user_id,))
    t_metasmoke.start()


def single_random_user(ev_room):
    """
    Returns a single user name from users in a room
    :param ev_room: Room to select users from
    :return: A single user tuple
    """
    return random.choice(GlobalVars.users_chatting[ev_room])

#
#
# System command functions below here
# Each of these should take the *args and **kwargs parameters. This allows us to create functions that
# don't accept any parameters but still use the `command_dict` mappings


# --- Blacklist Functions --- #
def command_add_blacklist_user(*args, **kwargs):
    """
    Adds a user to the site blacklist
    :param kwargs: Requires that 'content_lower', 'message_url', 'ev_room', 'ev_user_id', and 'wrap2' is passed as kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        uid, val = get_user_from_list_command(kwargs['content_lower'])
    if uid > -1 and val != "":
        add_blacklisted_user((uid, val), kwargs['message_url'], "")
        return "User blacklisted (`{}` on `{}`).".format(uid, val)
    elif uid == -2:
        return "Error: {}".format(val)
    else:
        return "Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`."


def command_check_blacklist(*args, **kwargs):
    """
    Checks if a user is blacklisted
    :param kwargs: Requires 'content_lower' is passed as a kwarg
    :return: A string
    """
    uid, val = get_user_from_list_command(kwargs['content_lower'])
    if uid > -1 and val != "":
        if is_blacklisted_user((uid, val)):
            return "User is blacklisted (`{}` on `{}`).".format(uid, val)
        else:
            return "User is not blacklisted (`{}` on `{}`).".format(uid, val)
    elif uid == -2:
        return "Error: {}".format(val)
    else:
        return False, "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."


def command_remove_blacklist_user(*args, **kwargs):
    """
    Removes user from site blacklist
    :param kwargs: Requires 'content_lower', 'ev_room', 'ev_user_id' and 'wrap2' is passed as kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        uid, val = get_user_from_list_command(kwargs['content_lower'])
        if uid > -1 and val != "":
            if remove_blacklisted_user((uid, val)):
                return "User removed from blacklist (`{}` on `{}`).".format(uid, val)
            else:
                return "User is not blacklisted."
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."


# --- Whitelist functions --- #
def command_add_whitelist_user(*args, **kwargs):
    """
    Adds a user to site whitelist
    :param kwargs: Requires that 'content_lower', 'ev_room', 'ev_user_id', and 'wrap2' is passed as kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        uid, val = get_user_from_list_command(kwargs['content_lower'])
        if uid > -1 and val != "":
            add_whitelisted_user((uid, val))
            return "User whitelisted (`{}` on `{}`).".format(uid, val)
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`."


def command_check_whitelist(*args, **kwargs):
    """
    Checks if a user is whitelisted
    :param kwargs: Requires 'content_lower' is passed as a kwarg
    :return: A string
    """
    uid, val = get_user_from_list_command(kwargs['content_lower'])
    if uid > -1 and val != "":
        if is_whitelisted_user((uid, val)):
            return "User is whitelisted (`{}` on `{}`).".format(uid, val)
        else:
            return "User is not whitelisted (`{}` on `{}`).".format(uid, val)
    elif uid == -2:
        return "Error: {}".format(val)
    else:
        return False, "Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`."


def command_remove_whitelist_user(*args, **kwargs):
    """
    Removes a user from site whitelist
    :param kwargs: Requires 'content_lower', 'ev_room', 'ev_user_id' and 'wrap2' is passed as kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        uid, val = get_user_from_list_command(kwargs['content_lower'])
        if uid != -1 and val != "":
            if remove_whitelisted_user((uid, val)):
                return "User removed from whitelist (`{}` on `{}`).".format(uid, val)
            else:
                return "User is not whitelisted."
        elif uid == -2:
            return "Error: {}".format(val)
        else:
            return False, "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."


# --- Joke Commands --- #
def command_blame(*args, **kwargs):
    """
    Returns a string with a user to blame (This is a joke command)
    :param kwargs: Requires that 'ev_room' is passed as a kwarg
    :return: A string
    """
    GlobalVars.users_chatting[kwargs['ev_room']] = list(set(GlobalVars.users_chatting[kwargs['ev_room']]))
    user_to_blame = single_random_user(kwargs['ev_room'])
    return u"It's [{}]({})'s fault.".format(user_to_blame[0], user_to_blame[1])


def command_brownie(*args, **kwargs):
    """
    Returns a string equal to "Brown!" (This is a joke command)
    :return: A string
    """
    return "Brown!"


def command_coffee(*args, **kwargs):
    """
    Returns a string stating who the coffee is for (This is a joke command)
    :param kwargs: Requires that 'ev_user_name' is passed as a kwarg
    :return: A string
    """
    return "*brews coffee for @" + kwargs['ev_user_name'].replace(" ", "") + "*"


def command_lick(*args, **kwargs):
    """
    Returns a string when a user says 'lick' (This is a joke command)
    :return: A string
    """
    return "*licks ice cream cone*"


def command_tea(*args, **kwargs):
    """
    Returns a string stating who the tea is for (This is a joke command)
    :param kwargs: Requires that 'ev_user_name' is passed as a kwarg
    :return: A string
    """
    return "*brews a cup of {choice} tea for @{user}*".format(
        choice=random.choice(['earl grey', 'green', 'chamomile', 'lemon', 'darjeeling', 'mint', 'jasmine']),
        user=kwargs['ev_user_name'].replace(" ", ""))


def command_wut(*args, **kwargs):
    """
    Returns a string when a user asks 'wut' (This is a joke command)
    :return: A string
    """
    return "Whaddya mean, 'wut'? Humans..."


# --- Block application from posting functions --- #
def command_block(*args, **kwargs):
    """
    Blocks posts from application for a period of time
    :param kwargs: Requires that 'message_parts', 'ev_user_id' and 'wrap2' be passed as kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        room_id = kwargs['message_parts'][2] if len(kwargs['message_parts']) > 2 else "all"
        time_to_block = kwargs['message_parts'][1] if len(kwargs['message_parts']) > 1 else "0"
        if not time_to_block.isdigit():
            return False, "Invalid duration."

        time_to_block = int(time_to_block)
        time_to_block = time_to_block if 0 < time_to_block < 14400 else 900
        GlobalVars.blockedTime[room_id] = time.time() + time_to_block
        which_room = "globally" if room_id == "all" else "in room " + room_id
        report = "Reports blocked for {} seconds {}.".format(time_to_block, which_room)
        if room_id != GlobalVars.charcoal_room_id:
            GlobalVars.charcoal_hq.send_message(report)
        return report


def command_unblock(*args, **kwargs):
    """
    Unblocks posting to a room
    :param kwargs: Requires that 'message_parts', 'ev_user_id' and 'wrap2' be passed as a kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        room_id = kwargs['message_parts'][2] if len(kwargs['message_parts']) > 2 else "all"
        GlobalVars.blockedTime[room_id] = time.time()
        which_room = "globally" if room_id == "all" else "in room " + room_id
        report = "Reports unblocked {}.".format(GlobalVars.blockedTime - time.time(), which_room)
        if room_id != GlobalVars.charcoal_room_id:
            GlobalVars.charcoal_hq.send_message(report)
        return report


# --- Administration Commands --- #
def command_alive(*args, **kwargs):
    """
    Returns a string indicating the process is still active
    :param kwargs: Requires that 'ev_room' be passed as kwarg
    :return: A string
    """
    if kwargs['ev_room'] == GlobalVars.charcoal_room_id:
        return 'Of course'
    elif kwargs['ev_room'] == GlobalVars.meta_tavern_room_id or kwargs['ev_room'] == GlobalVars.socvr_room_id:
        return random.choice(['Yup', 'You doubt me?', 'Of course', '... did I miss something?', 'plz send teh coffee',
                              'Watching this endless list of new questions *never* gets boring', 'Kinda sorta'])


def command_allspam(*args, **kwargs):
    """
    Reports all of a user's posts as spam
    :param kwargs: Requires that 'message_parts', 'ev_user_id', 'ev_room_name' and 'wrap2' be passed as kwarg
    :return:
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        if len(kwargs['message_parts']) != 2:
            return False, "1 argument expected"
        url = kwargs['message_parts'][1]
        user = get_user_from_url(url)
        if user is None:
            return "That doesn't look like a valid user URL."
        why = u"User manually reported by *{}* in room *{}*.\n".format(kwargs['ev_user_name'], kwargs['ev_room_name'].decode('utf-8'))
        handle_user_with_all_spam(user, why)
        return None


def command_errorlogs(*args, **kwargs):
    """
    Shows the most recent lines in the error logs
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'message_parts' is passed as kwarg
    :return:
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        count = -1
        if len(kwargs['message_parts']) != 2:
            return "The !!/errorlogs command requires 1 argument."
        try:
            count = int(kwargs['message_parts'][1])
        except ValueError:
            pass
        if count == -1:
            return "Invalid argument."
        logs_part = fetch_lines_from_error_log(count)
        post_message_in_room(room_id_str=kwargs['ev_room'], msg=logs_part, length_check=False)
    # TODO: NEEDS A RETURN


def command_help(*args, **kwargs):
    """
    Returns the help text
    :param kwargs:
    :return: A string
    """
    return "I'm [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector), a bot " \
           "that detects spam and offensive posts on the network and posts alerts to chat. " \
           "[A command list is available here](https://github.com/Charcoal-SE/SmokeDetector/wiki/Commands)."


def command_location(*args, **kwargs):
    """
    Returns the current location the application is running from
    :return: A string with current location
    """
    return GlobalVars.location


def command_master(*args, **kwargs):
    """
    Forces a system exit with exit code = 8
    :param kwargs: Requires 'ev_room', 'ev_user_id' and 'wrap2' is passed as kwarg
    :return: None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        os._exit(8)


def command_pull(*args, **kwargs):
    """
    Pull an update from GitHub
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2' is passed as kwarg
    :return: String on failure, None on success
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        request = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/git/refs/heads/master')
        latest_sha = request.json()["object"]["sha"]
        request = requests.get(
            'https://api.github.com/repos/Charcoal-SE/SmokeDetector/commits/{commit_code}/statuses'.format(
                commit_code=latest_sha))
        states = []
        for status in request.json():
            state = status["state"]
            states.append(state)
        if "success" in states:
            os._exit(3)
        elif "error" in states or "failure" in states:
            return "CI build failed! :( Please check your commit."
        elif "pending" in states or not states:
            return "CI build is still pending, wait until the build has finished and then pull again."


def command_reboot(*args, **kwargs):
    """
    Forces a system exit with exit code = 5
    :param kwargs: Requires 'ev_room', 'ev_user_id' and 'wrap2' is passed as kwarg
    :return: None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        post_message_in_room(room_id_str=kwargs['ev_room'], msg="Goodbye, cruel world")
        os._exit(5)


def command_privileged(*args, **kwargs):
    """
    Tells user whether or not they have privileges
    :param kwargs: Requires that 'ev_room', 'ev_user_id' and 'wrap2' are passed as kwargs
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        return "Yes, you are a privileged user."
    return "No, you are not a privileged user. See " \
           "[the Privileges wiki page](//github.com/Charcoal-SE/SmokeDetector/wiki/Privileges) for information on " \
           "what privileges are and what is expected."


def command_quota(*args, **kwargs):
    """
    Report how many API hits remain for the day
    :return: A string
    """
    return "The current API quota remaining is {}.".format(GlobalVars.apiquota)


def command_stappit(*args, **kwargs):
    """
    Forces a system exit with exit code = 6
    :param kwargs: Requires 'ev_room', 'ev_user_id' and 'wrap2' is passed as kwarg
    :return: None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        post_message_in_room(room_id_str=kwargs['ev_room'], msg="Goodbye, cruel world")
        os._exit(6)


def command_status(*args, **kwargs):
    """
    Returns the amount of time the application has been running
    :return: A string
    """
    now = datetime.utcnow()
    diff = now - UtcDate.startup_utc_date
    minutes, remainder = divmod(diff.seconds, 60)
    minute_str = "minutes" if minutes != 1 else "minute"
    return 'Running since {time} UTC ({minute_count} {plurality})'.format(time=GlobalVars.startup_utc,
                                                                          minute_count=minutes, plurality=minute_str)


def command_test(*args, **kwargs):
    """
    Test a post to determine if it'd be automatically reported
    :param kwargs: Requires that 'content', 'content-lower' be passed as a kwarg
    :return: A string
    """
    string_to_test = kwargs['content'][8:]
    test_as_answer = False
    if kwargs['content_lower'].startswith("!!/test-a"):
        string_to_test = kwargs['content'][10:]
        test_as_answer = True
    if len(string_to_test) == 0:
        return "Nothing to test"
    result = "> "
    reasons, why = FindSpam.test_post(string_to_test, string_to_test, string_to_test, "", test_as_answer, False, 1, 0)
    if len(reasons) == 0:
        result += "Would not be caught for title, {}, and username.".format("answer" if test_as_answer else "body")
        return result
    result += ", ".join(reasons).capitalize()
    if why is not None and len(why) > 0:
        result += "\n----------\n"
        result += why
    return result


def command_version(*args, **kwargs):
    """
    Returns the current version of the application
    :return: A string
    """
    return '[{commit_name}](https://github.com/Charcoal-SE/SmokeDetector/commit/{commit_code})'.format(
        commit_name=GlobalVars.commit_with_author, commit_code=GlobalVars.commit)


def command_whoami(*args, **kwargs):
    """
    Returns user id of smoke detector
    :param kwargs: Requires 'ev_room' is passed as a kwarg
    :return:
    """
    if kwargs['ev_room'] in GlobalVars.smokeDetector_user_id:
        return "My id for this room is {}.".format(GlobalVars.smokeDetector_user_id[kwargs['ev_room']])
    return "I don't know my user ID for this room. (Something is wrong, and it's apnorton's fault.)"


# --- Notification functions --- #
def command_allnotifications(*args, **kwargs):
    """
    Returns a string stating what sites a user will be notified about
    :param kwargs: Requires that 'message_parts', 'ev_user_id' and 'wrap2' be passed as kwarg
    :return: A string
    """
    if len(kwargs['message_parts']) != 2:
        return False, "1 argument expected"
    user_id = int(kwargs['ev_user_id'])
    chat_site = kwargs['wrap2'].host
    room_id = kwargs['message_parts'][1]
    if not room_id.isdigit():
        return False, "Room ID is invalid."
    sites = get_all_notification_sites(user_id, chat_site, room_id)
    if len(sites) == 0:
        return "You won't get notified for any sites in that room."

    return "You will get notified for these sites:\r\n" + ", ".join(sites)


def command_notify(*args, **kwargs):
    """
    Subscribe a user to events on a site in a single room
    :param kwargs: Requires that 'message_parts', 'ev_user_id' and 'wrap2' be passed as a kwarg
    :return: A string
    """
    if len(kwargs['message_parts']) != 3:
        return False, "2 arguments expected"
    user_id = int(kwargs['ev_user_id'])
    chat_site = kwargs['wrap2'].host
    room_id = kwargs['message_parts'][1]
    if not room_id.isdigit():
        return False, "Room ID is invalid."

    room_id = int(room_id)
    quiet_action = ("-" in kwargs['message_parts'][2])
    se_site = kwargs['message_parts'][2].replace('-', '')
    response, full_site = add_to_notification_list(user_id, chat_site, room_id, se_site)
    if response == 0:
        if quiet_action:
            return None

        return "You'll now get pings from me if I report a post on `{site_name}`, in room `{room_id}` on `chat.{chat_domain}`".format(
            site_name=se_site, room_id=room_id, chat_domain=chat_site)
    elif response == -1:
        return "That notification configuration is already registered."
    elif response == -2:
        return False, "The given SE site does not exist."


def command_unnotify(*args, **kwargs):
    """
    Unsubscribes a user to specific events
    :param kwargs: Requires that 'message_parts', 'ev_user_id' and 'wrap2' be passed as a kwarg
    :return: A string
    """
    if len(kwargs['message_parts']) != 3:
        return False, "2 arguments expected"
    user_id = int(kwargs['ev_user_id'])
    chat_site = kwargs['wrap2'].host
    room_id = kwargs['message_parts'][1]
    if not room_id.isdigit():
        return False, "Room ID is invalid."

    room_id = int(room_id)
    quiet_action = ("-" in kwargs['message_parts'][2])
    se_site = kwargs['message_parts'][2].replace('-', '')
    response = remove_from_notification_list(user_id, chat_site, room_id, se_site)
    if response:
        if quiet_action:
            return None
        return "I will no longer ping you if I report a post on `{site_name}`, in room `{room_id}` on" \
               " `chat.{chat_domain}`".format(site_name=se_site, room_id=room_id, chat_domain=chat_site)
    return "That configuration doesn't exist."


def command_willbenotified(*args, **kwargs):
    """
    Returns a string stating whether a user will be notified or not
    :param kwargs: Requires that 'message_parts', 'ev_user_id' and 'wrap2' be passed as a kwarg
    :return: A string
    """
    if len(kwargs['message_parts']) != 3:
        return False, "2 arguments expected"
    user_id = int(kwargs['ev_user_id'])
    chat_site = kwargs['wrap2'].host
    room_id = kwargs['message_parts'][1]
    if not room_id.isdigit():
        return False, "Room ID is invalid"

    room_id = int(room_id)
    se_site = kwargs['message_parts'][2]
    will_be_notified = will_i_be_notified(user_id, chat_site, room_id, se_site)
    if will_be_notified:
        return "Yes, you will be notified for that site in that room."

    return "No, you won't be notified for that site in that room."


# --- Post Responses --- #
def command_report_post(*args, **kwargs):
    """
    Report a post (or posts)
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'message_parts', 'message_url' is passed as kwarg
    :return: A string (or None)
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        crn, wait = can_report_now(kwargs['ev_user_id'], kwargs['wrap2'].host)
        if not crn:
            return "You can execute the !!/report command again in {} seconds. " \
                   "To avoid one user sending lots of reports in a few commands and slowing SmokeDetector down " \
                   "due to rate-limiting, you have to wait 30 seconds after you've reported multiple posts using " \
                   "!!/report, even if your current command just has one URL. (Note that this timeout won't be " \
                   "applied if you only used !!/report for one post)".format(wait)
        if len(kwargs['message_parts']) < 2:
            return False, "Not enough arguments."
        output = []
        index = 0
        urls = list(set(kwargs['message_parts'][1:]))
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
                output.append("Post {}: Could not find data for this post in the API. "
                              "It may already have been deleted.".format(index))
                continue
            user = get_user_from_url(post_data.owner_url)
            if user is not None:
                add_blacklisted_user(user, kwargs['message_url'], post_data.post_url)
            why = u"Post manually reported by user *{}* in room *{}*.\n".format(kwargs['ev_user_name'],
                                                                                kwargs['ev_room_name'].decode('utf-8'))
            batch = ""
            if len(urls) > 1:
                batch = " (batch report: post {} out of {})".format(index, len(urls))
            handle_spam(title=post_data.title,
                        body=post_data.body,
                        poster=post_data.owner_name,
                        site=post_data.site,
                        post_url=post_data.post_url,
                        poster_url=post_data.owner_url,
                        post_id=post_data.post_id,
                        reasons=["Manually reported " + post_data.post_type + batch],
                        is_answer=post_data.post_type == "answer",
                        why=why,
                        owner_rep=post_data.owner_rep,
                        post_score=post_data.score,
                        up_vote_count=post_data.up_vote_count,
                        down_vote_count=post_data.down_vote_count,
                        question_id=post_data.question_id)
        if 1 < len(urls) > len(output):
            add_or_update_multiple_reporter(kwargs['ev_user_id'], kwargs['wrap2'].host, time.time())
        if len(output) > 0:
            return os.linesep.join(output)
        return None


#
#
# Subcommands go below here
def subcommand_delete(*args, **kwargs):
    """
    Attempts to delete a post from room
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2' and 'msg' is passed as kwargs
    :return: None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        try:
            kwargs['msg'].delete()
        except:
            pass  # couldn't delete message


def subcommand_editlink(*args, **kwargs):
    """
    Removes link from a marked report message
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'msg_content' and 'msg' is passed as kwargs
    :return: None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        edited = edited_message_after_postgone_command(kwargs['msg_content'])
        if edited is None:
            return "That's not a report."
        kwargs['msg'].edit(edited)
        return None


def subcommand_falsepositive(*args, **kwargs):
    """
    Marks a post as a false positive
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'post_site_id', 'post_url', 'quiet_action', 'post_type'
        and 'msg' is passed as kwargs
    :return: None or a string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        if not is_report(kwargs['post_site_id']):
            return "That message is not a report."

        send_metasmoke_feedback(post_url=kwargs['post_url'],
                                second_part_lower=kwargs['second_part_lower'],
                                ev_user_name=kwargs['ev_user_name'],
                                ev_user_id=kwargs['ev_user_id'])

        add_false_positive((kwargs['post_site_id'][0], kwargs['post_site_id'][1]))
        user_added = False
        user_removed = False
        url_from_msg = fetch_owner_url_from_msg_content(kwargs['msg_content'])
        user = None
        if url_from_msg is not None:
            user = get_user_from_url(url_from_msg)

        if kwargs['second_part_lower'].startswith("falseu") or kwargs['second_part_lower'].startswith("fpu"):
            if user is not None:
                add_whitelisted_user(user)
                user_added = True
        if "Blacklisted user:" in kwargs['msg_content']:
            if user is not None:
                remove_blacklisted_user(user)
                user_removed = True
        if kwargs['post_type'] == "question":
            if user_added and not kwargs['quiet_action']:
                return "Registered question as false positive and whitelisted user."
            elif user_removed and not kwargs['quiet_action']:
                return "Registered question as false positive and removed user from the blacklist."
            elif not kwargs['quiet_action']:
                return "Registered question as false positive."
        elif kwargs['post_type'] == "answer":
            if user_added and not kwargs['quiet_action']:
                return "Registered answer as false positive and whitelisted user."
            elif user_removed and not kwargs['quiet_action']:
                return "Registered answer as false positive and removed user from the blacklist."
            elif not kwargs['quiet_action']:
                return "Registered answer as false positive."
        try:
            kwargs['msg'].delete()
        except:
            pass


def subcommand_ignore(*args, **kwargs):
    """
    Marks a post to be ignored
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'post_site_id', 'post_url', 'quiet_action' is passed
        as kwargs
    :return: String or None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        if not is_report(kwargs['post_site_id']):
            return "That message is not a report."

        send_metasmoke_feedback(post_url=kwargs['post_url'],
                                second_part_lower=kwargs['second_part_lower'],
                                ev_user_name=kwargs['ev_user_name'],
                                ev_user_id=kwargs['ev_user_id'])

        add_ignored_post(kwargs['post_site_id'][0:2])
        if not kwargs['quiet_action']:
            return "Post ignored; alerts about it will no longer be posted."
        else:
            return None


def subcommand_naa(*args, **kwargs):
    """
    Marks a post as NAA
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'post_site_id', 'post_url', 'quiet_action' is passed
        as kwargs
    :return: String or None
    :return:
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        if not is_report(kwargs['post_site_id']):
            return "That message is not a report."
        if kwargs['post_type'] != "answer":
            return "That report was a question; questions cannot be marked as NAAs."

        send_metasmoke_feedback(post_url=kwargs['post_url'],
                                second_part_lower=kwargs['second_part_lower'],
                                ev_user_name=kwargs['ev_user_name'],
                                ev_user_id=kwargs['ev_user_id'])

        add_ignored_post(kwargs['post_site_id'][0:2])
        if kwargs['quiet_action']:
            return None
        return "Recorded answer as an NAA in metasmoke."


def subcommand_truepositive(*args, **kwargs):
    """
    Marks a post as a true positive
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2', 'post_site_id', 'post_url', 'quiet_action', 'post_type'
        'message_url', and 'msg' is passed as kwargs
    :return: None or a string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        if not is_report(kwargs['post_site_id']):
            return "That message is not a report."

        send_metasmoke_feedback(post_url=kwargs['post_url'],
                                second_part_lower=kwargs['second_part_lower'],
                                ev_user_name=kwargs['ev_user_name'],
                                ev_user_id=kwargs['ev_user_id'])

        user_added = False
        if kwargs['second_part_lower'].startswith("trueu") or kwargs['second_part_lower'].startswith("tpu"):
            url_from_msg = fetch_owner_url_from_msg_content(kwargs['msg_content'])
            if url_from_msg is not None:
                user = get_user_from_url(url_from_msg)
                if user is not None:
                    add_blacklisted_user(user, kwargs['message_url'], "http:" + kwargs['post_url'])
                    user_added = True
        if kwargs['post_type'] == "question":
            if kwargs['quiet_action']:
                return None
            if user_added:
                return "Blacklisted user and registered question as true positive."
            return "Recorded question as true positive in metasmoke. Use `tpu` or `trueu` if you want to " \
                   "blacklist a user."
        elif kwargs['post_type'] == "answer":
            if kwargs['quiet_action']:
                return None
            if user_added:
                return "Blacklisted user."
            return "Recorded answer as true positive in metasmoke. If you want to blacklist the poster of the " \
                   "answer, use `trueu` or `tpu`."


def subcommand_why(*args, **kwargs):
    """
    Returns reasons a post was reported
    :param kwargs: Requires 'msg_content' is passed as a kwarg
    :return: A string
    """
    post_info = fetch_post_id_and_site_from_msg_content(kwargs['msg_content'])
    if post_info is None:
        post_info = fetch_user_from_allspam_report(kwargs['msg_content'])
        if post_info is None:
            return "That's not a report."
        why = get_why_allspam(post_info)
        if why is not None or why != "":
            return why
    else:
        post_id, site, _ = post_info
        why = get_why(site, post_id)
        if why is not None or why != "":
            return why
    return "There is no `why` data for that user (anymore)."


#
#
#
# This dictionary defines our commands and the associated function to call
# To use this your calling code will look like this
#    command_dict['command'](paramer1, parameter2, ...)
# Each key can have a different set of parameters so 'command1' could look like this
#    command_dict['command1'](paramer1)
# Triggering input:
#        !!/alive
# Hardcoded key example of above input:
#    command_dict["!//alive"]()
command_dict = {
    "!//addblu": command_add_blacklist_user,
    "!!/addwlu": command_add_whitelist_user,
    "!!/alive": command_alive,
    "!!/allnotificationsites": command_allnotifications,
    "!!/allspam": command_allspam,
    "!!/amiprivileged": command_privileged,
    "!!/apiquota": command_quota,
    "!!/blame": command_blame,
    "!!/block": command_block,
    "!!/brownie": command_brownie,
    "!!/commands": command_help,
    "!!/coffee": command_coffee,
    "!!/errorlogs": command_errorlogs,
    "!!/help": command_help,
    "!!/info": command_help,
    "!!/isblu": command_check_blacklist,
    "!!/iswlu": command_check_whitelist,
    "!!/lick": command_lick,
    "!!/location": command_location,
    "!!/master": command_master,
    "!!/notify": command_notify,
    "!!/pull": command_pull,
    "!!/reboot": command_reboot,
    "!!/reportuser": command_allspam,
    "!!/rmblu": command_remove_blacklist_user,
    "!!/rmwlu": command_remove_whitelist_user,
    "!!/report": command_report_post,
    "!!/rev": command_version,
    "!!/stappit": command_stappit,
    "!!/status": command_status,
    "!!/tea": command_tea,
    "!!/test": command_test,
    "!!/unblock": command_unblock,
    "!!/unnotify": command_unnotify,
    "!!/ver": command_version,
    "!!/willibenotified": command_willbenotified,
    "!!/whoami": command_whoami,
    "!!/wut": command_wut,
}


# This dictionary defines our subcommands and the associated function to call
# To use this your calling code will look like this
#    second_part_dict['command'](paramer1, parameter2, ...)
# Each key can have a different set of parameters so 'command1' could look like this
#    second_part_dict['command1'](paramer1)
# Triggering input:
#        sd false
# Hardcoded key example of above input:
#    command_dict["!//alive"]()

subcommand_dict = {
    "false": subcommand_falsepositive,
    "fp": subcommand_falsepositive,
    "falseu": subcommand_falsepositive,
    "fpu": subcommand_falsepositive,
    "false-": subcommand_falsepositive,
    "fp-": subcommand_falsepositive,
    "falseu-": subcommand_falsepositive,
    "fpu-": subcommand_falsepositive,

    "true": subcommand_truepositive,
    "tp": subcommand_truepositive,
    "trueu": subcommand_truepositive,
    "tpu": subcommand_truepositive,
    "true-": subcommand_truepositive,
    "tp-": subcommand_truepositive,
    "trueu-": subcommand_truepositive,
    "tpu-": subcommand_truepositive,

    "ignore": subcommand_ignore,
    "ignore-": subcommand_ignore,

    "naa": subcommand_naa,
    "naa-": subcommand_naa,

    "delete": subcommand_delete,
    "remove": subcommand_delete,
    "gone": subcommand_delete,
    "poof": subcommand_delete,
    "del": subcommand_delete,

    "postgone": subcommand_editlink,

    "why": subcommand_why,
    "why?":subcommand_why,
}