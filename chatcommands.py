# coding=utf-8
# noinspection PyUnresolvedReferences
from globalvars import GlobalVars
from findspam import FindSpam
# noinspection PyUnresolvedReferences
from datetime import datetime
from utcdate import UtcDate
from apigetpost import api_get_post
from datahandling import *
from metasmoke import Metasmoke
from parsing import *
from spamhandling import handle_spam
from spamhandling import handle_user_with_all_spam
from gitmanager import GitManager
import threading
from threading import Thread
import random
import requests
import os
import time
import datahandling
# noinspection PyCompatibility
import regex
from helpers import Response
from classes import Post

# TODO: pull out code block to get user_id, chat_site, room_id into function
# TODO: Return result for all functions should be similar (tuple/named tuple?)
# TODO: Do we need uid == -2 check?  Turn into "is_user_valid" check
# TODO: Consistant return structure
#   if return...else return vs if return...return


# noinspection PyMissingTypeHints
def check_permissions(function_):
    # noinspection PyMissingTypeHints
    def run_command(ev_room, ev_user_id, wrap2, *args, **kwargs):
        if datahandling.is_privileged(ev_room, ev_user_id, wrap2):
            kwargs['ev_room'] = ev_room
            kwargs['ev_user_id'] = ev_user_id
            kwargs['wrap2'] = wrap2
            return function_(*args, **kwargs)
        else:
            return Response(command_status=False,
                            message=GlobalVars.not_privileged_warning)

    return run_command


# Functions go before the final dictionaries of command to function mappings
def post_message_in_room(room_id_str, msg, length_check=True):
    if room_id_str == GlobalVars.charcoal_room_id:
        GlobalVars.charcoal_hq.send_message(msg, length_check)
    elif room_id_str == GlobalVars.meta_tavern_room_id:
        GlobalVars.tavern_on_the_meta.send_message(msg, length_check)
    elif room_id_str == GlobalVars.socvr_room_id:
        GlobalVars.socvr.send_message(msg, length_check)


# noinspection PyMissingTypeHints
def is_report(post_site_id):
    """
    Checks if a post is a report
    :param post_site_id: Report to check
    :return: Boolean stating if it is a report
    """
    if post_site_id is None:
        return False
    return True


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def send_metasmoke_feedback(post_url, second_part_lower, ev_user_name, ev_user_id, ev_chat_host):
    """
    Sends feedback to metasmoke
    :param ev_user_name:
    :param post_url: The post url we are sending
    :param second_part_lower: Feedback
    :param ev_user_name: User name supplying the feedback
    :param ev_user_id: User ID supplying the feedback
    :return: None
    """
    t_metasmoke = Thread(name="metasmoke feedback send on #{url}".format(url=post_url),
                         target=Metasmoke.send_feedback_for_post,
                         args=(post_url, second_part_lower, ev_user_name, ev_user_id, ev_chat_host,))
    t_metasmoke.start()


# noinspection PyMissingTypeHints
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
# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_add_blacklist_user(message_parts, content_lower, message_url, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Adds a user to the site blacklist
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param message_url:
    :param content_lower:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    quiet_action = any([part.endswith('-') for part in message_parts])
    uid, val = get_user_from_list_command(content_lower)
    if int(uid) > -1 and val != "":
        add_blacklisted_user((uid, val), message_url, "")
        return Response(command_status=True, message=None) if quiet_action \
            else Response(command_status=True, message="User blacklisted (`{}` on `{}`).".format(uid, val))
    elif int(uid) == -2:
        return Response(command_status=True, message="Error: {}".format(val))
    else:
        return Response(command_status=False,
                        message="Invalid format. Valid format: `!!/addblu profileurl` "
                                "*or* `!!/addblu userid sitename`.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_check_blacklist(content_lower, *args, **kwargs):
    """
    Checks if a user is blacklisted
    :param content_lower:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    uid, val = get_user_from_list_command(content_lower)
    if int(uid) > -1 and val != "":
        if is_blacklisted_user((uid, val)):
            return Response(command_status=True, message="User is blacklisted (`{}` on `{}`).".format(uid, val))
        else:
            return Response(command_status=True, message="User is not blacklisted (`{}` on `{}`).".format(uid, val))
    elif int(uid) == -2:
        return Response(command_status=True, message="Error: {}".format(val))
    else:
        return Response(command_status=False,
                        message="Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_remove_blacklist_user(message_parts, content_lower, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Removes user from site blacklist
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param content_lower:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    quiet_action = any([part.endswith('-') for part in message_parts])
    uid, val = get_user_from_list_command(content_lower)
    if int(uid) > -1 and val != "":
        if remove_blacklisted_user((uid, val)):
            return Response(command_status=True, message=None) if quiet_action \
                else Response(command_status=True,
                              message="User removed from blacklist (`{}` on `{}`).".format(uid, val))
        else:
            return Response(command_status=True, message="User is not blacklisted.")
    elif int(uid) == -2:
        return Response(command_status=True, message="Error: {}".format(val))
    else:
        return Response(command_status=False,
                        message="Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`.")


# --- Whitelist functions --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@check_permissions
def command_add_whitelist_user(message_parts, content_lower, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Adds a user to site whitelist
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param content_lower:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    quiet_action = any([part.endswith('-') for part in message_parts])
    uid, val = get_user_from_list_command(content_lower)
    if int(uid) > -1 and val != "":
        add_whitelisted_user((uid, val))
        return Response(command_status=True, message=None) if quiet_action \
            else Response(command_status=True, message="User whitelisted (`{}` on `{}`).".format(uid, val))
    elif int(uid) == -2:
        return Response(command_status=True, message="Error: {}".format(val))
    else:
        return Response(command_status=False,
                        message="Invalid format. Valid format: `!!/addwlu profileurl` *or* "
                                "`!!/addwlu userid sitename`.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_check_whitelist(content_lower, *args, **kwargs):
    """
    Checks if a user is whitelisted
    :param content_lower:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    uid, val = get_user_from_list_command(content_lower)
    if int(uid) > -1 and val != "":
        if is_whitelisted_user((uid, val)):
            return Response(command_status=True, message="User is whitelisted (`{}` on `{}`).".format(uid, val))
        else:
            return Response(command_status=True, message="User is not whitelisted (`{}` on `{}`).".format(uid, val))
    elif int(uid) == -2:
        return Response(command_status=True, message="Error: {}".format(val))
    else:
        return Response(command_status=False,
                        message="Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@check_permissions
def command_remove_whitelist_user(message_parts, content_lower, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Removes a user from site whitelist
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param content_lower:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    quiet_action = any([part.endswith('-') for part in message_parts])
    uid, val = get_user_from_list_command(content_lower)
    if int(uid) != -1 and val != "":
        if remove_whitelisted_user((uid, val)):
            return Response(command_status=True, message=None) if quiet_action \
                else Response(command_status=True,
                              message="User removed from whitelist (`{}` on `{}`).".format(uid, val))
        else:
            return Response(command_status=True, message="User is not whitelisted.")
    elif int(uid) == -2:
        return Response(command_status=True, message="Error: {}".format(val))
    else:
        return Response(command_status=False,
                        message="Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_blacklist_help(*args, **kwargs):
    """
    Returns a string which explains the usage of the new blacklist commands.
    :return: A string
    """
    return Response(command_status=True, message="The !!/blacklist command has been deprecated. "
                                                 "Please use !!/blacklist-website, !!/blacklist-username "
                                                 "or !!/blacklist-keyword. Remember to escape dots "
                                                 "in URLs using \\.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_blacklist_website(message_parts, ev_user_name, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Adds a string to the website blacklist and commits/pushes to GitHub
    :param message_parts:
    :param ev_user_name:
    :param ev_room:
    :param :ev_user_id:
    :return: A Response
    """

    chat_user_profile_link = "http://chat.{host}/users/{id}".format(host=wrap2.host, id=str(ev_user_id))
    website_pattern = " ".join(message_parts[1:])
    # noinspection PyProtectedMember
    try:
        regex.compile(website_pattern)
    except regex._regex_core.error:
        return Response(command_status=False, message="An invalid website pattern was provided, not blacklisting.")
    result = GitManager.add_to_blacklist(
        blacklist="website",
        item_to_blacklist=website_pattern,
        username=ev_user_name,
        chat_profile_link=chat_user_profile_link,
        code_permissions=datahandling.is_code_privileged(ev_room, ev_user_id, wrap2)
    )
    return Response(command_status=result[0], message=result[1])


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_blacklist_keyword(message_parts, ev_user_name, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Adds a string to the keyword blacklist and commits/pushes to GitHub
    :param message_parts:
    :param ev_user_name:
    :param ev_room:
    :param :ev_user_id:
    :return: A Response
    """

    chat_user_profile_link = "http://chat.{host}/users/{id}".format(host=wrap2.host, id=str(ev_user_id))
    keyword_pattern = " ".join(message_parts[1:])
    # noinspection PyProtectedMember
    try:
        regex.compile(keyword_pattern)
    except regex._regex_core.error:
        return Response(command_status=False, message="An invalid keyword pattern was provided, not blacklisting.")
    result = GitManager.add_to_blacklist(
        blacklist="keyword",
        item_to_blacklist=keyword_pattern,
        username=ev_user_name,
        chat_profile_link=chat_user_profile_link,
        code_permissions=datahandling.is_code_privileged(ev_room, ev_user_id, wrap2)
    )
    return Response(command_status=result[0], message=result[1])


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_blacklist_username(message_parts, ev_user_name, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Adds a string to the username blacklist and commits/pushes to GitHub
    :param message_parts:
    :param ev_user_name:
    :param ev_room:
    :param :ev_user_id:
    :return: A Response
    """

    chat_user_profile_link = "http://chat.{host}/users/{id}".format(host=wrap2.host, id=str(ev_user_id))
    username_pattern = " ".join(message_parts[1:])
    # noinspection PyProtectedMember
    try:
        regex.compile(username_pattern)
    except regex._regex_core.error:
        return Response(command_status=False, message="An invalid username pattern was provided, not blacklisting.")
    result = GitManager.add_to_blacklist(
        blacklist="username",
        item_to_blacklist=username_pattern,
        username=ev_user_name,
        chat_profile_link=chat_user_profile_link,
        code_permissions=datahandling.is_code_privileged(ev_room, ev_user_id, wrap2)
    )
    return Response(command_status=result[0], message=result[1])


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_gitstatus(wrap2, *args, **kwargs):
    return Response(command_status=True, message=GitManager.current_git_status())


# --- Joke Commands --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_blame(ev_room, *args, **kwargs):
    """
    Returns a string with a user to blame (This is a joke command)
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    GlobalVars.users_chatting[ev_room] = list(set(GlobalVars.users_chatting[ev_room]))
    user_to_blame = single_random_user(ev_room)
    return Response(command_status=True, message=u"It's [{}]({})'s fault.".format(user_to_blame[0], user_to_blame[1]))


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_brownie(*args, **kwargs):
    """
    Returns a string equal to "Brown!" (This is a joke command)
    :return: A string
    """
    return Response(command_status=True, message="Brown!")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_coffee(ev_user_name, *args, **kwargs):
    """
    Returns a string stating who the coffee is for (This is a joke command)
    :param ev_user_name:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    return Response(command_status=True, message=u"*brews coffee for @" + ev_user_name.replace(" ", "") + "*")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_lick(*args, **kwargs):
    """
    Returns a string when a user says 'lick' (This is a joke command)
    :return: A string
    """
    return Response(command_status=True, message="*licks ice cream cone*")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_tea(ev_user_name, *args, **kwargs):
    """
    Returns a string stating who the tea is for (This is a joke command)
    :param ev_user_name:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    return Response(command_status=True,
                    message=u"*brews a cup of {choice} tea for @{user}*".format(
                        choice=random.choice(['earl grey', 'green', 'chamomile',
                                              'lemon', 'darjeeling', 'mint', 'jasmine']),
                        user=ev_user_name.replace(" ", "")))


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_wut(*args, **kwargs):
    """
    Returns a string when a user asks 'wut' (This is a joke command)
    :return: A string
    """
    return Response(command_status=True, message="Whaddya mean, 'wut'? Humans...")


""" Uncomment when Winterbash comes back
# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_hats(*args, **kwargs):
    wb_start = datetime(2016, 12, 19, 0, 0, 0)
    wb_end = datetime(2017, 1, 9, 0, 0, 0)
    now = datetime.utcnow()
    return_string = ""
    if wb_start > now:
        diff = wb_start - now
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        daystr = "days" if diff.days != 1 else "day"
        hourstr = "hours" if hours != 1 else "hour"
        minutestr = "minutes" if minutes != 1 else "minute"
        secondstr = "seconds" if seconds != 1 else "second"
        return_string = "WE LOVE HATS! Winter Bash will begin in {} {}, {} {}, {} {}, and {} {}.".format(
            diff.days, daystr, hours, hourstr, minutes, minutestr, seconds, secondstr)
    elif wb_end > now:
        diff = wb_end - now
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        daystr = "days" if diff.days != 1 else "day"
        hourstr = "hours" if hours != 1 else "hour"
        minutestr = "minutes" if minutes != 1 else "minute"
        secondstr = "seconds" if seconds != 1 else "second"
        return_string = "Winter Bash won't end for {} {}, {} {}, {} {}, and {} {}. GO EARN SOME HATS!".format(
            diff.days, daystr, hours, hourstr, minutes, minutestr, seconds, secondstr)
    return Response(command_status=True, message=return_string)
"""


# --- Block application from posting functions --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_block(message_parts, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Blocks posts from application for a period of time
    :param ev_room:
    :param wrap2:
    :param ev_user_id:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    room_id = message_parts[2] if len(message_parts) > 2 else "all"
    time_to_block = message_parts[1] if len(message_parts) > 1 else "0"
    if not time_to_block.isdigit():
        return Response(command_status=False, message="Invalid duration.")

    time_to_block = int(time_to_block)
    time_to_block = time_to_block if 0 < time_to_block < 14400 else 900
    GlobalVars.blockedTime[room_id] = time.time() + time_to_block
    which_room = "globally" if room_id == "all" else "in room " + room_id
    report = "Reports blocked for {} seconds {}.".format(time_to_block, which_room)
    if room_id != GlobalVars.charcoal_room_id:
        GlobalVars.charcoal_hq.send_message(report)
    return Response(command_status=True, message=report)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_unblock(message_parts, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Unblocks posting to a room
    :param ev_room:
    :param wrap2:
    :param ev_user_id:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    room_id = message_parts[2] if len(message_parts) > 2 else "all"
    GlobalVars.blockedTime[room_id] = time.time()
    which_room = "globally" if room_id == "all" else "in room " + room_id
    report = "Reports unblocked {}.".format(GlobalVars.blockedTime - time.time(), which_room)
    if room_id != GlobalVars.charcoal_room_id:
        GlobalVars.charcoal_hq.send_message(report)
    return Response(command_status=True, message=report)


# --- Administration Commands --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_alive(ev_room, *args, **kwargs):
    """
    Returns a string indicating the process is still active
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    return Response(command_status=True,
                    message=random.choice(['Yup', 'You doubt me?', 'Of course',
                                           '... did I miss something?', 'plz send teh coffee',
                                           'Watching this endless list of new questions *never* gets boring',
                                           'Kinda sorta']))


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_allspam(message_parts, ev_room, ev_user_id, wrap2, ev_user_name, ev_room_name, *args, **kwargs):
    """
    Reports all of a user's posts as spam
    :param ev_room_name:
    :param ev_user_name:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return:
    """
    if len(message_parts) != 2:
        return Response(command_status=False, message="1 argument expected")
    url = message_parts[1]
    user = get_user_from_url(url)
    if user is None:
        return Response(command_status=True, message="That doesn't look like a valid user URL.")
    why = u"User manually reported by *{}* in room *{}*.\n".format(ev_user_name, ev_room_name.decode('utf-8'))
    handle_user_with_all_spam(user, why)
    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_errorlogs(ev_room, ev_user_id, wrap2, message_parts, *args, **kwargs):
    """
    Shows the most recent lines in the error logs
    :param message_parts:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return:
    """
    count = -1
    if len(message_parts) > 2:
        return Response(command_status=False, message="The !!/errorlogs command requires either 0 or 1 arguments.")
    try:
        count = int(message_parts[1])
    except (ValueError, IndexError):
        count = 50
    logs_part = fetch_lines_from_error_log(count)
    post_message_in_room(room_id_str=ev_room, msg=logs_part, length_check=False)
    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_help(*args, **kwargs):
    """
    Returns the help text
    :param kwargs: No additional arguments expected
    :return: A string
    """
    return Response(command_status=True, message="I'm " + GlobalVars.chatmessage_prefix +
                                                 ", a bot that detects spam and offensive posts on the network and "
                                                 "posts alerts to chat. "
                                                 "[A command list is available here]"
                                                 "(https://charcoal-se.org/smokey/Commands).")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_location(*args, **kwargs):
    """
    Returns the current location the application is running from
    :return: A string with current location
    """
    return Response(command_status=True, message=GlobalVars.location)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyProtectedMember
@check_permissions
def command_master(ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Forces a system exit with exit code = 8
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    os._exit(8)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyProtectedMember
@check_permissions
def command_pull(ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Pull an update from GitHub
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: String on failure, None on success
    """
    request = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/git/refs/heads/deploy')
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
        return Response(command_status=True, message="CI build failed! :( Please check your commit.")
    elif "pending" in states or not states:
        return Response(command_status=True,
                        message="CI build is still pending, wait until the build has finished and then pull again.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyProtectedMember
@check_permissions
def command_reboot(ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Forces a system exit with exit code = 5
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    post_message_in_room(room_id_str=ev_room, msg="Goodbye, cruel world")
    os._exit(5)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_privileged(ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Tells user whether or not they have privileges
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    if is_privileged(ev_room, ev_user_id, wrap2):
        return Response(command_status=True, message=u"\u2713 You are a privileged user.")
    return Response(command_status=True,
                    message=u"\u2573 " + GlobalVars.not_privileged_warning)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_code_privileged(ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Tells user whether or not they have code privileges
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    if is_code_privileged(ev_room, ev_user_id, wrap2):
        return Response(command_status=True, message="Yes, you have code privileges.")
    return Response(command_status=True,
                    message="No, you are not a code-privileged user.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_quota(*args, **kwargs):
    """
    Report how many API hits remain for the day
    :return: A string
    """
    return Response(command_status=True, message="The current API quota remaining is {}.".format(GlobalVars.apiquota))


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_queuestatus(*args, **kwargs):
    """
    Report current API queue
    :return: A string
    """
    return Response(command_status=True, message=GlobalVars.bodyfetcher.print_queue())


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyProtectedMember
@check_permissions
def command_stappit(message_parts, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Forces a system exit with exit code = 6
    :param message_parts:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    if len(message_parts) == 1 or " ".join(message_parts[1:]).lower() in GlobalVars.location.lower():
        post_message_in_room(room_id_str=ev_room, msg="Goodbye, cruel world")
        os._exit(6)

    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_status(*args, **kwargs):
    """
    Returns the amount of time the application has been running
    :return: A string
    """
    now = datetime.utcnow()
    diff = now - UtcDate.startup_utc_date
    minutes, remainder = divmod(diff.seconds, 60)
    minute_str = "minutes" if minutes != 1 else "minute"
    return Response(command_status=True,
                    message='Running since {time} UTC ({minute_count} {plurality})'.format(
                        time=GlobalVars.startup_utc,
                        minute_count=minutes, plurality=minute_str))


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_stop_flagging(*args, **kwargs):
    t_metasmoke = Thread(name="stop_autoflagging", target=Metasmoke.stop_autoflagging,
                         args=())
    t_metasmoke.start()
    return Response(command_status=True, message="Request sent...")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyProtectedMember
@check_permissions
def command_standby(message_parts, ev_room, ev_user_id, wrap2, *args, **kwargs):
    """
    Forces a system exit with exit code = 7
    :param message_parts:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    if " ".join(message_parts[1:]).lower() in GlobalVars.location.lower():
        m = "{location} is switching to standby".format(location=GlobalVars.location)
        post_message_in_room(room_id_str=ev_room, msg=m)
        os._exit(7)

    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_test(content, content_lower, *args, **kwargs):
    """
    Test a post to determine if it'd be automatically reported
    :param content_lower:
    :param content:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    string_to_test = content[8:]
    test_as_answer = False
    if len(string_to_test) == 0:
        return Response(command_status=True, message="Nothing to test")
    result = "> "
    fakepost = Post(api_response={'title': string_to_test, 'body': string_to_test,
                                  'owner': {'display_name': string_to_test, 'reputation': 1, 'link': ''},
                                  'site': "", 'IsAnswer': test_as_answer, 'score': 0})
    reasons, why = FindSpam.test_post(fakepost)
    if len(reasons) == 0:
        result += "Would not be caught for title, body, and username."
        return Response(command_status=True, message=result)
    result += ", ".join(reasons).capitalize()
    if why is not None and len(why) > 0:
        result += "\n----------\n"
        result += why
    return Response(command_status=True, message=result)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_test_answer(content, content_lower, *args, **kwargs):
    """
    Test an answer to determine if it'd be automatically reported
    :param content_lower:
    :param content:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    string_to_test = content[10:]
    test_as_answer = True
    if len(string_to_test) == 0:
        return Response(command_status=True, message="Nothing to test")
    result = "> "
    fakepost = Post(api_response={'title': 'Valid title', 'body': string_to_test,
                                  'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                  'site': "", 'IsAnswer': test_as_answer, 'score': 0})
    reasons, why = FindSpam.test_post(fakepost)
    if len(reasons) == 0:
        result += "Would not be caught as an answer."
        return Response(command_status=True, message=result)
    result += ", ".join(reasons).capitalize()
    if why is not None and len(why) > 0:
        result += "\n----------\n"
        result += why
    return Response(command_status=True, message=result)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_test_question(content, content_lower, *args, **kwargs):
    """
    Test a question to determine if it'd be automatically reported
    :param content_lower:
    :param content:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    string_to_test = content[10:]
    test_as_answer = False
    if len(string_to_test) == 0:
        return Response(command_status=True, message="Nothing to test")
    result = "> "
    fakepost = Post(api_response={'title': 'Valid title', 'body': string_to_test,
                                  'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                  'site': "", 'IsAnswer': test_as_answer, 'score': 0})
    reasons, why = FindSpam.test_post(fakepost)
    if len(reasons) == 0:
        result += "Would not be caught as a question."
        return Response(command_status=True, message=result)
    result += ", ".join(reasons).capitalize()
    if why is not None and len(why) > 0:
        result += "\n----------\n"
        result += why
    return Response(command_status=True, message=result)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_test_title(content, content_lower, *args, **kwargs):
    """
    Test a title to determine if it'd be automatically reported
    :param content_lower:
    :param content:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    string_to_test = content[10:]
    test_as_answer = False
    if len(string_to_test) == 0:
        return Response(command_status=True, message="Nothing to test")
    result = "> "
    fakepost = Post(api_response={'title': string_to_test, 'body': "Valid question body",
                                  'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                  'site': "", 'IsAnswer': test_as_answer, 'score': 0})
    reasons, why = FindSpam.test_post(fakepost)
    if len(reasons) == 0:
        result += "Would not be caught as a title."
        return Response(command_status=True, message=result)
    result += ", ".join(reasons).capitalize()
    if why is not None and len(why) > 0:
        result += "\n----------\n"
        result += why
    return Response(command_status=True, message=result)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_test_username(content, content_lower, *args, **kwargs):
    """
    Test a username to determine if it'd be automatically reported
    :param content_lower:
    :param content:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    string_to_test = content[10:]
    test_as_answer = False
    if len(string_to_test) == 0:
        return Response(command_status=True, message="Nothing to test")
    result = "> "
    fakepost = Post(api_response={'title': 'Valid title', 'body': "Valid post body",
                                  'owner': {'display_name': string_to_test, 'reputation': 1, 'link': ''},
                                  'site': '', 'IsAnswer': test_as_answer, 'score': 0})
    reasons, why = FindSpam.test_post(fakepost)
    if len(reasons) == 0:
        result += "Would not be caught as a username."
        return Response(command_status=True, message=result)
    result += ", ".join(reasons).capitalize()
    if why is not None and len(why) > 0:
        result += "\n----------\n"
        result += why
    return Response(command_status=True, message=result)


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_thread_descriptions(*args, **kwargs):
    """
    Returns a description of current threads, for debugging
    :return: A string
    """

    threads = ("{ident}: {name}".format(ident=t.ident, name=t.name) for t in threading.enumerate())

    return Response(command_status=True, message="{threads}".format(threads="\n".join(list(threads))))


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_version(*args, **kwargs):
    """
    Returns the current version of the application
    :return: A string
    """
    return Response(command_status=True, message='[{commit_name}]({repository}/commit/{commit_code})'.format(
        commit_name=GlobalVars.commit_with_author, commit_code=GlobalVars.commit, repository=GlobalVars.bot_repository))


# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_whoami(ev_room, *args, **kwargs):
    """
    Returns user id of smoke detector
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return:
    """
    if ev_room in GlobalVars.smokeDetector_user_id:
        return Response(command_status=True,
                        message="My id for this room is {}.".format(GlobalVars.smokeDetector_user_id[ev_room]))
    return Response(command_status=True,
                    message="I don't know my user ID for this room. (Something is wrong, and it's apnorton's fault.)")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyUnboundLocalVariable
def command_pending(content, content_lower, *args, **kwargs):
    """
    Finds posts with TP feedback that have yet to be deleted.
    :param args: No additional arguments expected.
    :param kwargs: No additional arguments expected.
    :return:
    """
    try:
        page = int(content[11:])
    except ValueError:
        return Response(
            command_status=False,
            message="Expected an integer page number and got '{0!r}'"
            " instead (ValueError).".format(content[11:]))
    posts = requests.get("https://metasmoke.erwaysoftware.com/api/undeleted?pagesize=2&page={}&key={}".format(
        page, GlobalVars.metasmoke_key)).json()
    messages = []
    for post in posts['items']:
        messages.append("[{0}]({1}) ([MS](https://m.erwaysoftware.com/post/{0}))".format(post['id'], post['link']))
    return Response(command_status=True,
                    message=", ".join(messages))


# --- Notification functions --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal
def command_allnotifications(message_parts, ev_user_id, wrap2, *args, **kwargs):
    """
    Returns a string stating what sites a user will be notified about
    :param wrap2:
    :param ev_user_id:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    if len(message_parts) != 2:
        return Response(command_status=False, message="1 argument expected")
    user_id = int(ev_user_id)
    chat_site = wrap2.host
    room_id = message_parts[1]
    if not room_id.isdigit():
        return Response(command_status=False, message="Room ID is invalid.")
    sites = get_all_notification_sites(user_id, chat_site, room_id)
    if len(sites) == 0:
        return Response(command_status=True, message="You won't get notified for any sites in that room.")

    return Response(command_status=True, message="You will get notified for these sites:\r\n" + ", ".join(sites))


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_notify(message_parts, ev_user_id, wrap2, *args, **kwargs):
    """
    Subscribe a user to events on a site in a single room
    :param wrap2:
    :param ev_user_id:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    if len(message_parts) != 3:
        return Response(command_status=False, message="2 arguments expected")
    user_id = int(ev_user_id)
    chat_site = wrap2.host
    room_id = message_parts[1]
    if not room_id.isdigit():
        return Response(command_status=False, message="Room ID is invalid.")

    room_id = int(room_id)
    quiet_action = any([part.endswith('-') for part in message_parts])
    se_site = message_parts[2].replace('-', '')
    response, full_site = add_to_notification_list(user_id, chat_site, room_id, se_site)
    if response == 0:
        return Response(command_status=True, message=None) if quiet_action \
            else Response(command_status=True,
                          message="You'll now get pings from me if I report a post on `{site_name}`, in room "
                                  "`{room_id}` on `chat.{chat_domain}`".format(site_name=se_site,
                                                                               room_id=room_id,
                                                                               chat_domain=chat_site))
    elif response == -1:
        return Response(command_status=True, message="That notification configuration is already registered.")
    elif response == -2:
        return Response(command_status=False, message="The given SE site does not exist.")
    else:
        return Response(command_status=False, message="Unrecognized code returned when adding notification.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_unnotify(message_parts, ev_user_id, wrap2, *args, **kwargs):
    """
    Unsubscribes a user to specific events
    :param wrap2:
    :param ev_user_id:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    if len(message_parts) != 3:
        return Response(command_status=False, message="2 arguments expected")
    user_id = int(ev_user_id)
    chat_site = wrap2.host
    room_id = message_parts[1]
    if not room_id.isdigit():
        return Response(command_status=False, message="Room ID is invalid.")

    room_id = int(room_id)
    quiet_action = any([part.endswith('-') for part in message_parts])
    se_site = message_parts[2].replace('-', '')
    response = remove_from_notification_list(user_id, chat_site, room_id, se_site)
    if response:
        return Response(command_status=True, message=None) if quiet_action \
            else Response(command_status=True,
                          message="I will no longer ping you if I report a post on `{site_name}`, in room `{room_id}` "
                                  "on `chat.{chat_domain}`".format(site_name=se_site,
                                                                   room_id=room_id,
                                                                   chat_domain=chat_site))
    return Response(command_status=True, message="That configuration doesn't exist.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def command_willbenotified(message_parts, ev_user_id, wrap2, *args, **kwargs):
    """
    Returns a string stating whether a user will be notified or not
    :param wrap2:
    :param ev_user_id:
    :param message_parts:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    if len(message_parts) != 3:
        return Response(command_status=False, message="2 arguments expected")
    user_id = int(ev_user_id)
    chat_site = wrap2.host
    room_id = message_parts[1]
    if not room_id.isdigit():
        return Response(command_status=False, message="Room ID is invalid")

    room_id = int(room_id)
    se_site = message_parts[2]
    will_be_notified = will_i_be_notified(user_id, chat_site, room_id, se_site)
    if will_be_notified:
        return Response(command_status=True, message="Yes, you will be notified for that site in that room.")

    return Response(command_status=True, message="No, you won't be notified for that site in that room.")


# --- Post Responses --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def command_report_post(ev_room, ev_user_id, wrap2, message_parts, message_url,
                        ev_user_name, ev_room_name, *args, **kwargs):
    """
    Report a post (or posts)
    :param ev_room_name:
    :param ev_user_name:
    :param message_url:
    :param message_parts:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: A string (or None)
    """
    crn, wait = can_report_now(ev_user_id, wrap2.host)
    if not crn:
        return Response(command_status=False, message="You can execute the !!/report command again in {} seconds. "
                                                      "To avoid one user sending lots of reports in a few commands and "
                                                      "slowing SmokeDetector down due to rate-limiting, you have to "
                                                      "wait 30 seconds after you've reported multiple posts using "
                                                      "!!/report, even if your current command just has one URL. (Note "
                                                      "that this timeout won't be applied if you only used !!/report "
                                                      "for one post)".format(wait))
    if len(message_parts) < 2:
        return Response(command_status=False, message="Not enough arguments.")
    output = []
    index = 0
    urls = list(set(message_parts[1:]))
    if len(urls) > 5:
        return Response(command_status=False, message="To avoid SmokeDetector reporting posts too slowly, you can "
                                                      "report at most 5 posts at a time. This is to avoid "
                                                      "SmokeDetector's chat messages getting rate-limited too much, "
                                                      "which would slow down reports.")
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
        if has_already_been_posted(post_data.site, post_data.post_id, post_data.title) and not is_false_positive(
                (post_data.post_id, post_data.site)):
            # Don't re-report if the post wasn't marked as a false positive. If it was marked as a false positive,
            # this re-report might be attempting to correct that/fix a mistake/etc.
            output.append("Post {}: Already recently reported".format(index))
            continue
        post_data.is_answer = (post_data.post_type == "answer")
        post = Post(api_response=post_data.as_dict)
        user = get_user_from_url(post_data.owner_url)
        if user is not None:
            add_blacklisted_user(user, message_url, post_data.post_url)
        why = u"Post manually reported by user *{}* in room *{}*.\n".format(ev_user_name,
                                                                            ev_room_name.decode('utf-8'))
        batch = ""
        if len(urls) > 1:
            batch = " (batch report: post {} out of {})".format(index, len(urls))
        handle_spam(post=post,
                    reasons=["Manually reported " + post_data.post_type + batch],
                    why=why)
    if 1 < len(urls) > len(output):
        add_or_update_multiple_reporter(ev_user_id, wrap2.host, time.time())
    if len(output) > 0:
        return Response(command_status=True, message=os.linesep.join(output))
    return Response(command_status=True, message=None)


#
#
# Subcommands go below here
# noinspection PyIncorrectDocstring,PyUnusedLocal,PyBroadException
@check_permissions
def subcommand_delete(ev_room, ev_user_id, wrap2, msg, *args, **kwargs):
    """
    Attempts to delete a post from room
    :param msg:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    try:
        msg.delete()
    except:
        pass  # couldn't delete message
    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def subcommand_editlink(ev_room, ev_user_id, wrap2, msg_content, msg, *args, **kwargs):
    """
    Removes link from a marked report message
    :param msg:
    :param msg_content:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    edited = edited_message_after_postgone_command(msg_content)
    if edited is None:
        return Response(command_status=True, message="That's not a report.")
    msg.edit(edited)
    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyBroadException
@check_permissions
def subcommand_falsepositive(ev_room, ev_user_id, wrap2, post_site_id, post_url,
                             quiet_action, post_type, msg, second_part_lower, ev_user_name,
                             msg_content, *args, **kwargs):
    """
    Marks a post as a false positive
    :param msg_content:
    :param ev_user_name:
    :param second_part_lower:
    :param msg:
    :param post_type:
    :param quiet_action:
    :param post_url:
    :param post_site_id:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None or a string
    """
    if not is_report(post_site_id):
        return Response(command_status=True, message="That message is not a report.")

    send_metasmoke_feedback(post_url=post_url,
                            second_part_lower=second_part_lower,
                            ev_user_name=ev_user_name,
                            ev_user_id=ev_user_id,
                            ev_chat_host=wrap2.host)

    add_false_positive((post_site_id[0], post_site_id[1]))
    user_added = False
    user_removed = False
    url_from_msg = fetch_owner_url_from_msg_content(msg_content)
    user = None
    if url_from_msg is not None:
        user = get_user_from_url(url_from_msg)

    if second_part_lower.startswith("falseu") or second_part_lower.startswith("fpu"):
        if user is not None:
            add_whitelisted_user(user)
            user_added = True
    if "Blacklisted user:" in msg_content:
        if user is not None:
            remove_blacklisted_user(user)
            user_removed = True
    if post_type == "question":
        if user_added and not quiet_action:
            return Response(command_status=True, message="Registered question as false positive and whitelisted user.")
        elif user_removed and not quiet_action:
            return Response(command_status=True,
                            message="Registered question as false positive and removed user from the blacklist.")
        elif not quiet_action:
            return Response(command_status=True, message="Registered question as false positive.")
    elif post_type == "answer":
        if user_added and not quiet_action:
            return Response(command_status=True, message="Registered answer as false positive and whitelisted user.")
        elif user_removed and not quiet_action:
            return Response(command_status=True,
                            message="Registered answer as false positive and removed user from the blacklist.")
        elif not quiet_action:
            return Response(command_status=True, message="Registered answer as false positive.")
    try:
        if int(msg.room.id) != int(GlobalVars.charcoal_hq.id):
            msg.delete()
    except:
        pass
    return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@check_permissions
def subcommand_ignore(ev_room, ev_user_id, wrap2, post_site_id, post_url, quiet_action, second_part_lower, ev_user_name,
                      *args, **kwargs):
    """
    Marks a post to be ignored
    :param quiet_action:
    :param post_url:
    :param post_site_id:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: String or None
    """
    if not is_report(post_site_id):
        return Response(command_status=True, message="That message is not a report.")

    send_metasmoke_feedback(post_url=post_url,
                            second_part_lower=second_part_lower,
                            ev_user_name=ev_user_name,
                            ev_user_id=ev_user_id,
                            ev_chat_host=wrap2.host)

    add_ignored_post(post_site_id[0:2])
    if not quiet_action:
        return Response(command_status=True, message="Post ignored; alerts about it will no longer be posted.")
    else:
        return Response(command_status=True, message=None)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def subcommand_naa(ev_room, ev_user_id, wrap2, post_site_id, post_url, quiet_action,
                   second_part_lower, ev_user_name, post_type, *args, **kwargs):
    """
    Marks a post as NAA
    :param post_type:
    :param ev_user_name:
    :param second_part_lower:
    :param quiet_action:
    :param post_url:
    :param post_site_id:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: String or None
    :return:
    """
    if not is_report(post_site_id):
        return Response(command_status=True, message="That message is not a report.")
    if post_type != "answer":
        return Response(command_status=True, message="That report was a question; questions cannot be marked as NAAs.")

    send_metasmoke_feedback(post_url=post_url,
                            second_part_lower=second_part_lower,
                            ev_user_name=ev_user_name,
                            ev_user_id=ev_user_id,
                            ev_chat_host=wrap2.host)

    add_ignored_post(post_site_id[0:2])
    if quiet_action:
        return Response(command_status=True, message=None)
    return Response(command_status=True, message="Recorded answer as an NAA in metasmoke.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
@check_permissions
def subcommand_truepositive(ev_room, ev_user_id, wrap2, post_site_id, post_url, quiet_action,
                            post_type, message_url, msg, second_part_lower, ev_user_name,
                            msg_content, *args, **kwargs):
    """
    Marks a post as a true positive
    :param msg_content:
    :param ev_user_name:
    :param second_part_lower:
    :param msg:
    :param message_url:
    :param post_type:
    :param quiet_action:
    :param post_url:
    :param post_site_id:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None or a string
    """
    if not is_report(post_site_id):
        return Response(command_status=True, message="That message is not a report.")

    send_metasmoke_feedback(post_url=post_url,
                            second_part_lower=second_part_lower,
                            ev_user_name=ev_user_name,
                            ev_user_id=ev_user_id,
                            ev_chat_host=wrap2.host)

    user_added = False
    if second_part_lower.startswith("trueu") or second_part_lower.startswith("tpu"):
        url_from_msg = fetch_owner_url_from_msg_content(msg_content)
        if url_from_msg is not None:
            user = get_user_from_url(url_from_msg)
            if user is not None:
                add_blacklisted_user(user, message_url, "http:" + post_url)
                user_added = True
    if post_type == "question":
        if quiet_action:
            return Response(command_status=True, message=None)
        if user_added:
            return Response(command_status=True, message="Blacklisted user and registered question as true positive.")
        return Response(command_status=True,
                        message="Recorded question as true positive in metasmoke. Use `tpu` or `trueu` if you want "
                                "to blacklist a user.")
    elif post_type == "answer":
        if quiet_action:
            return Response(command_status=True, message=None)
        if user_added:
            return Response(command_status=True, message="Blacklisted user.")
        return Response(command_status=True, message="Recorded answer as true positive in metasmoke. If you want to "
                                                     "blacklist the poster of the answer, use `trueu` or `tpu`.")

    else:
        return Response(command_status=False, message="Post type was not recognized (not `question` or `answer`) - "
                                                      "call a developer! "
                                                      "No action was taken.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def subcommand_why(msg_content, *args, **kwargs):
    """
    Returns reasons a post was reported
    :param msg_content:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    post_info = fetch_post_id_and_site_from_msg_content(msg_content)
    if post_info is None:
        post_info = fetch_user_from_allspam_report(msg_content)
        if post_info is None:
            return Response(command_status=True, message="That's not a report.")
        why = get_why_allspam(post_info)
        if why is not None or why != "":
            return Response(command_status=True, message=why)
    else:
        post_id, site, _ = post_info
        why = get_why(site, post_id)
        if why is not None or why != "":
            return Response(command_status=True, message=why)
    return Response(command_status=True, message="There is no `why` data for that user (anymore).")


# noinspection PyIncorrectDocstring,PyUnusedLocal
def subcommand_autoflagged(msg_content, post_url, *args, **kwargs):
    """
    Determines whether a post was automatically flagged by Metasmoke
    :param msg_content:
    :param post_url:
    :param kwargs: No additional arguments expected
    :return: A string
    """
    autoflagged, names = Metasmoke.determine_if_autoflagged(post_url)
    if autoflagged:
        return Response(command_status=True,
                        message="That post was automatically flagged, using flags from: {}.".format(", ".join(names)))
    else:
        return Response(command_status=True, message="That post was **not** automatically flagged by metasmoke.")


# This dictionary defines our commands and the associated function to call
# To use this your calling code will look like this
#    command_dict['command'](paramer1, parameter2, ...)
# Each key can have a different set of parameters so 'command1' could look like this
#    command_dict['command1'](paramer1)
# Triggering input:
#        !!/alive
# Hardcoded key example of above input:
#    command_dict["!!/alive"]()
command_dict = {
    "!!/addblu": command_add_blacklist_user,
    "!!/addblu-": command_add_blacklist_user,
    "!!/addwlu": command_add_whitelist_user,
    "!!/addwlu-": command_add_whitelist_user,
    "!!/alive": command_alive,
    "!!/allnotificationsites": command_allnotifications,
    "!!/allspam": command_allspam,
    "!!/amiprivileged": command_privileged,
    "!!/amicodeprivileged": command_code_privileged,
    "!!/apiquota": command_quota,
    "!!/blame": command_blame,
    "!!/block": command_block,
    "!!/brownie": command_brownie,
    "!!/blacklist": command_blacklist_help,
    "!!/blacklist-website": command_blacklist_website,
    "!!/blacklist-keyword": command_blacklist_keyword,
    "!!/blacklist-username": command_blacklist_username,
    "!!/commands": command_help,
    "!!/coffee": command_coffee,
    "!!/errorlogs": command_errorlogs,
    "!!/gitstatus": command_gitstatus,
    "!!/help": command_help,
    # "!!/hats": command_hats, (uncomment when Winterbash begins)
    "!!/info": command_help,
    "!!/isblu": command_check_blacklist,
    "!!/iswlu": command_check_whitelist,
    "!!/lick": command_lick,
    "!!/location": command_location,
    "!!/master": command_master,
    "!!/notify": command_notify,
    "!!/notify-": command_notify,
    "!!/pull": command_pull,
    "!!/pending": command_pending,
    "!!/reboot": command_reboot,
    "!!/reportuser": command_allspam,
    "!!/rmblu": command_remove_blacklist_user,
    "!!/rmblu-": command_remove_blacklist_user,
    "!!/rmwlu": command_remove_whitelist_user,
    "!!/rmwlu-": command_remove_whitelist_user,
    "!!/report": command_report_post,
    "!!/restart": command_reboot,
    "!!/rev": command_version,
    "!!/stappit": command_stappit,
    "!!/status": command_status,
    "!!/stopflagging": command_stop_flagging,
    "!!/standby": command_standby,
    "!!/tea": command_tea,
    "!!/test": command_test,
    "!!/testanswer": command_test_answer,
    "!!/test-a": command_test_answer,
    "!!/testquestion": command_test_question,
    "!!/test-q": command_test_question,
    "!!/testtitle": command_test_title,
    "!!/test-t": command_test_title,
    "!!/testusername": command_test_username,
    "!!/testuser": command_test_username,
    "!!/test-u": command_test_username,
    "!!/threads": command_thread_descriptions,
    "!!/unblock": command_unblock,
    "!!/unnotify": command_unnotify,
    "!!/unnotify-": command_unnotify,
    "!!/ver": command_version,
    "!!/willibenotified": command_willbenotified,
    "!!/whoami": command_whoami,
    "!!/wut": command_wut,
    "!!/queuestatus": command_queuestatus
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
    "why?": subcommand_why,

    "autoflagged?": subcommand_autoflagged,
    "autoflagged": subcommand_autoflagged,
}
