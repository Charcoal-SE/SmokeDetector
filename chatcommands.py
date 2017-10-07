# coding=utf-8
# noinspection PyUnresolvedReferences
from chatcommunicate import command, message, tell_rooms
from globalvars import GlobalVars
from findspam import FindSpam
# noinspection PyUnresolvedReferences
from datetime import datetime
from utcdate import UtcDate
from apigetpost import api_get_post
from datahandling import *
from blacklists import load_blacklists
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
# noinspection PyCompatibility
import regex
from helpers import only_blacklists_changed
from classes import Post

# TODO: pull out code block to get user_id, chat_site, room_id into function
# TODO: Return result for all functions should be similar (tuple/named tuple?)
# TODO: Do we need uid == -2 check?  Turn into "is_user_valid" check
# TODO: Consistant return structure
#   if return...else return vs if return...return


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


#
#
# System command functions below here


@command(int, whole_msg=True, privileged=True)
def approve(msg, pr_num):
    if is_code_privileged(msg.room, msg.owner.id, msg._client):
        resp = requests.post('{}/github/pr_approve/{}'.format(GlobalVars.metasmoke_host, pr_num))
        
        if resp.status_code == 200:
            return "Posted approval comment. PR will be merged automatically if it's a blacklist PR."
        else:
            return "Forwarding request to metasmoke returned HTTP {}. Check status manually.".format(resp.status_code))
    else:
        return "You don't have permission to do that."


# --- Blacklist Functions --- #
# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(str, whole_msg=True, privileged=True)
def addblu(msg, user):
    """
    Adds a user to site whitelist
    :param msg: ChatExchange message
    :param user:
    :return: A string
    """
    uid, val = get_user_from_list_command(user)

    if int(uid) > -1 and val != "":
        add_blacklisted_user((uid, val), msg.url, "")
        return "User blacklisted (`{}` on `{}`).".format(uid, val)
    elif int(uid) == -2:
        return "Error: {}".format(val)
    else:
        return "Invalid format. Valid format: `!!/addblu profileurl` "
                                        "*or* `!!/addblu userid sitename`."


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(str)
def isblu(user):
    """
    Check if a user is blacklisted
    :param user:
    :return: A string
    """

    uid, val = get_user_from_list_command(user)

    if int(uid) > -1 and val != "":
        if is_blacklisted_user((uid, val)):
            return "User is blacklisted (`{}` on `{}`).".format(uid, val)
        else:
            return "User is not blacklisted (`{}` on `{}`).".format(uid, val)
    elif int(uid) == -2:
        return "Error: {}".format(val)
    else:
        return "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(str, privileged=True)
def rmblu(user):
    """
    Removes user from site blacklist
    :param user:
    :return: A string
    """
    uid, val = get_user_from_list_command(user)

    if int(uid) > -1 and val != "":
        if remove_blacklisted_user((uid, val)):
            return "User removed from blacklist (`{}` on `{}`).".format(uid, val)
        else:
            return "User is not blacklisted."
    elif int(uid) == -2:
        return "Error: {}".format(val)
    else:
        return "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."


# --- Whitelist functions --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@command(str, privileged=True)
def addwlu(user):
    """
    Adds a user to site whitelist
    :param user:
    :return: A string
    """
    uid, val = get_user_from_list_command(content_lower)

    if int(uid) > -1 and val != "":
        add_whitelisted_user((uid, val))
        return "User whitelisted (`{}` on `{}`).".format(uid, val)
    elif int(uid) == -2:
        return "Error: {}".format(val)
    else:
        return "Invalid format. Valid format: `!!/addwlu profileurl` *or* "
                                             "`!!/addwlu userid sitename`."


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@command(str)
def iswlu(user):
    """
    Checks if a user is whitelisted
    :param user:
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


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@check_permissions
def rmwlu(user):
    """
    Removes a user from site whitelist
    :param user:
    :return: A string
    """
    uid, val = get_user_from_list_command(user)

    if int(uid) != -1 and val != "":
        if remove_whitelisted_user((uid, val)):
            return "User removed from whitelist (`{}` on `{}`).".format(uid, val)
        else:
            return "User is not whitelisted."
    elif int(uid) == -2:
        return "Error: {}".format(val)
    else:
        return "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."


# noinspection PyIncorrectDocstring
@command(str)
def blacklist(_):
    """
    Returns a string which explains the usage of the new blacklist commands.
    :return: A string
    """
    return "The !!/blacklist command has been deprecated. "
           "Please use !!/blacklist-website, !!/blacklist-username,"
           "!!/blacklist-keyword, or perhaps !!/watch-keyword. "
           "Remember to escape dots in URLs using \\."


def check_blacklist(string_to_test, is_username, is_watchlist):
    # Test the string and provide a warning message if it is already caught.
    if is_username:
        question = Post(api_response={'title': 'Valid title', 'body': 'Valid body',
                                      'owner': {'display_name': string_to_test, 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': False, 'score': 0})
        answer = Post(api_response={'title': 'Valid title', 'body': 'Valid body',
                                    'owner': {'display_name': string_to_test, 'reputation': 1, 'link': ''},
                                    'site': "", 'IsAnswer': True, 'score': 0})

    else:
        question = Post(api_response={'title': 'Valid title', 'body': string_to_test,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': False, 'score': 0})
        answer = Post(api_response={'title': 'Valid title', 'body': string_to_test,
                                    'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                    'site': "", 'IsAnswer': True, 'score': 0})

    question_reasons, _ = FindSpam.test_post(question)
    answer_reasons, _ = FindSpam.test_post(answer)

    # Filter out duplicates
    reasons = list(set(question_reasons) | set(answer_reasons))

    # Filter out watchlist results
    if not is_watchlist:
        reasons = list(filter(lambda reason: "potentially bad keyword" not in reason, reasons))

    return reasons


def format_blacklist_reasons(reasons):
    # Capitalize
    reasons = list(map(lambda reason: reason.capitalize(), reasons))

    # Join
    if len(reasons) < 3:
        reason_string = " and ".join(reasons)
    else:
        reason_string = ", and ".join([", ".join(reasons[:-1]), reasons[-1]])

    return reason_string


def do_blacklist(pattern, blacklist_type, msg, force=False):
    """
    Adds a string to the website blacklist and commits/pushes to GitHub
    :param message_parts:
    :param ev_user_name:
    :param ev_room:
    :param :ev_user_id:
    :return: A string
    """

    chat_user_profile_link = "http://chat.{host}/users/{id}".format(host=msg._client.host,
                                                                    id=msg.owner.id)

    # noinspection PyProtectedMember
    try:
        regex.compile(pattern)
    except regex._regex_core.error:
        return "An invalid pattern was provided, not blacklisting."

    if not force:
        reasons = check_blacklist(pattern.replace("\\W", " ").replace("\\.", "."),
                                  blacklist_type == "username",
                                  blacklist_type == "watch_keyword")

        if reasons:
            return "That pattern looks like it's already caught by " +
                    format_blacklist_reasons(reasons) + "; append`-force` if you really want to do that.")

    _, result = GitManager.add_to_blacklist(
        blacklist=blacklist_type,
        item_to_blacklist=pattern,
        username=user.name,
        chat_profile_link=chat_user_profile_link,
        code_permissions=is_code_privileged(msg.room, msg.owner.id, msg._client)
    )

    return result


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, give_name=True, aliases=["blacklist_website",
                                                                        "blacklist_username",
                                                                        "blacklist_keyword_force"
                                                                        "blacklist_website_force"
                                                                        "blacklist_username_force"])
def blacklist_keyword(msg, pattern, alias_used="blacklist_keyword"):
    """
    Adds a string to the blacklist and commits/pushes to GitHub
    :param msg:
    :param website:
    :return: A string
    """

    parts = alias_used.split("_")
    return do_blacklist(pattern, parts[1], msg, force=len(parts) > 2)


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, aliases=["watch_keyword"])
def watch(msg, website):
    """
    Adds a string to the watched keywords list and commits/pushes to GitHub
    :param msg:
    :param website:
    :return: A string
    """

    return do_blacklist(website, "watch_keyword", msg, force=False)


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, aliases=["watch_keyword_force"])
def watch_force(msg, website):
    """
    Adds a string to the watched keywords list and commits/pushes to GitHub
    :param msg:
    :param website:
    :return: A string
    """

    return do_blacklist(website, "watch_keyword", msg, force=True)


# noinspection PyIncorrectDocstring
@command(privileged=True)
def gitstatus():
    return GitManager.current_git_status()


@command(privileged=True, aliases=["remote-diff", "remote_diff"])
def remotediff():
    will_require_full_restart = "SmokeDetector will require a full restart to pull changes: " \
                                "{}".format(str(not only_blacklists_changed(GitManager.get_remote_diff())))

    return "{}\n\n{}".format(GitManager.get_remote_diff(), will_require_full_restart))


# --- Joke Commands --- #
@command(whole_msg=True)
def blame(msg):
    unlucky_victim = msg._client.get_user(random.choice(msg.room.get_current_user_ids()))

    return "It's [{}](https://chat.{}/users/{})'s fault.".format(unlucky_victim.name, msg._client.host, unlucky_victim.id)


@command(str, whole_msg=True, aliases=["blame\u180E"])
def blame2(msg, x):
    base = {"\u180E": 0, "\u200B": 1, "\u200C": 2, "\u200D": 3, "\u2060": 4, "\u2063": 5, "\uFEFF": 6}
    user = 0

    for i, char in enumerate(reversed(x)):
        user += (len(base)**i) * base[char]

    unlucky_victim = msg._client.get_user(user)
    return "It's [{}](https://chat.{}/users/{})'s fault.".format(unlucky_victim.name, msg._client.host, unlucky_victim.id)

# noinspection PyIncorrectDocstring
@command
def brownie():
    """
    Returns a string equal to "Brown!" (This is a joke command)
    :return: A string
    """
    return "Brown!"


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, arity=(0, 1))
def coffee(msg, other_user):
    """
    Returns a string stating who the coffee is for (This is a joke command)
    :param msg:
    :param other_user:
    :return: A string
    """
    return "*brews coffee for @" + (other_user if other_user else msg.owner.name.replace(" ", "")) + "*"


# noinspection PyIncorrectDocstring
@command
def lick(*args, **kwargs):
    """
    Returns a string when a user says 'lick' (This is a joke command)
    :return: A string
    """
    return "*licks ice cream cone*"


TEAS = ['earl grey', 'green', 'chamomile', 'lemon', 'darjeeling', 'mint', 'jasmine', 'passionfruit']


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, arity=(0, 1))
def tea(msg, other_user):
    """
    Returns a string stating who the tea is for (This is a joke command)
    :param msg:
    :param other_user:
    :return: A string
    """

    if other_user is None:
        return "*brews a cup of {} tea for @{}*".format(random.choice(TEAS), msg.owner.name.replace(" ", ""))
    else:
        return "*brews a cup of {} tea for @{}*".format(random.choice(TEAS), other_user)


# noinspection PyIncorrectDocstring
@command
def wut():
    """
    Returns a string when a user asks 'wut' (This is a joke command)
    :return: A string
    """
    return "Whaddya mean, 'wut'? Humans..."


""" Uncomment when Winterbash comes back
@command(aliases=["zomg_hats"])
def hats():
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
        secondstr = "seconds" if seconds != 1 else "diff_second"
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

    return return_string
"""


# --- Block application from posting functions --- #
# noinspection PyIncorrectDocstring
@command(int, int, privileged=True, arity=(1, 2))
def command_block(time, room_id):
    """
    Blocks posts from application for a period of time
    :param time:
    :param room_id:
    :return: A string
    """
    if room_id is None:

    time_to_block = time_to_block if 0 < time_to_block < 14400 else 900
    GlobalVars.blockedTime[room_id] = time.time() + time_to_block
    which_room = "globally" if room_id is None else "in room " + room_id
    report = "Reports blocked for {} seconds {}.".format(time, room_id)

    tell_rooms(report, ("debug", "metatavern"), ())
    return report


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(int int, privileged=True, arity=(1, 2))
def unblock(time, room_id):
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

    tell_rooms(report, ("debug", "metatavern"), ())
    return report


# --- Administration Commands --- #
# noinspection PyIncorrectDocstring
@command
def alive():
    """
    Returns a string indicating the process is still active
    :return: A string
    """
    return random.choice(['Yup', 'You doubt me?', 'Of course',
                          '... did I miss something?', 'plz send teh coffee',
                          'Watching this endless list of new questions *never* gets boring',
                          'Kinda sorta']))


# noinspection PyIncorrectDocstring
@command(str, privileged=True)
def allspam(url):
    """
    Reports all of a user's posts as spam
    :param url:
    :return:
    """
    user = get_user_from_url(url)

    if user is None:
        return "That doesn't look like a valid user URL."

    why = u"User manually reported by *{}* in room *{}*.\n".format(ev_user_name, ev_room_name.decode('utf-8'))
    handle_user_with_all_spam(user, why)


# noinspection PyIncorrectDocstring
@command(int, privileged=True, arity=(0, 1))
def command_errorlogs(count):
    """
    Shows the most recent lines in the error logs
    :param count:
    :return: A string
    """
    return fetch_lines_from_error_log(count or 50)


# noinspection PyIncorrectDocstring
@command
def help():
    """
    Returns the help text
    :return: A string
    """
    return "I'm " + GlobalVars.chatmessage_prefix +
           ", a bot that detects spam and offensive posts on the network and "
           "posts alerts to chat. "
           "[A command list is available here]"
           "(https://charcoal-se.org/smokey/Commands).")


# noinspection PyIncorrectDocstring
@command
def location():
    """
    Returns the current location the application is running from
    :return: A string with current location
    """
    return GlobalVars.location


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(privileged=True)
def command_master():
    """
    Forces a system exit with exit code = 8
    :return: None
    """
    os._exit(8)


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(privileged=True)
def command_pull():
    """
    Pull an update from GitHub
    :return: String on failure, None on success
    """
    if only_blacklists_changed(GitManager.get_remote_diff()):
        GitManager.pull_remote()
        load_blacklists()
        return "No code modified, only blacklists reloaded."
    else:
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
            return "CI build failed! :( Please check your commit."
        elif "pending" in states or not states:
            return "CI build is still pending, wait until the build has finished and then pull again."


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(whole_msg=True, privileged=True, aliases=["restart"])
def command_reboot(msg):
    """
    Forces a system exit with exit code = 5
    :param msg:
    :return: None
    """
    msg.room.send_message("Goodbye, cruel world")
    os._exit(5)


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(whole_msg=True)
def amiprivileged(msg):
    """
    Tells user whether or not they have privileges
    :param msg:
    :return: A string
    """
    if is_privileged(msg.room, msg.owner.id, msg._client):
        return "\u2713 You are a privileged user."

    return "\u2573 " + GlobalVars.not_privileged_warning


# noinspection PyIncorrectDocstring,
@command(whole_msg=True)
def amicodeprivileged(msg):
    """
    Tells user whether or not they have code privileges
    :param msg:
    :return: A string
    """
    if is_code_privileged(msg.room, msg.owner.id, msg._client):
        return "\u2713 You are a code-privileged user."

    return "\u2573 No, you are not a code-privileged user."


# noinspection PyIncorrectDocstring
@command
def apiquota():
    """
    Report how many API hits remain for the day
    :return: A string
    """
    return "The current API quota remaining is {}.".format(GlobalVars.apiquota)


# noinspection PyIncorrectDocstring
@command
def queuestatus():
    """
    Report current API queue
    :return: A string
    """
    return GlobalVars.bodyfetcher.print_queue()


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(str, whole_msg=True, privileged=True, arity=(0, 1))
def command_stappit(msg, location):
    """
    Forces a system exit with exit code = 6
    :param message_parts:
    :param wrap2:
    :param ev_user_id:
    :param ev_room:
    :param kwargs: No additional arguments expected
    :return: None
    """
    if location is None or location.lower() in GlobalVars.location.lower():
        msg.room.send_message("Goodbye, cruel world")
        os._exit(6)


def td_format(td_object):
    # source: http://stackoverflow.com/a/13756038/5244995
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    return ", ".join(strings)


# noinspection PyIncorrectDocstring
@command
def status():
    """
    Returns the amount of time the application has been running
    :return: A string
    """
    now = datetime.utcnow()
    diff = now - UtcDate.startup_utc_date

    return 'Running since {time} UTC ({relative})'.format(time=GlobalVars.startup_utc, relative=td_format(diff))


# noinspection PyIncorrectDocstring
@command(privileged=True)
def stopflagging(*args, **kwargs):
    t_metasmoke = Thread(name="stop_autoflagging", target=Metasmoke.stop_autoflagging,
                         args=())
    t_metasmoke.start()

    return "Request sent..."


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(str, whole_msg=True, privileged=True)
def command_standby(msg, location):
    """
    Forces a system exit with exit code = 7
    :param msg:
    :param location:
    :return: None
    """
    if location.lower() in GlobalVars.location.lower():
        msg.room.send_message("{location} is switching to standby".format(location=GlobalVars.location))
        os._exit(7)


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
def test(content, content_lower, *args, **kwargs):
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


# noinspection PyIncorrectDocstring
@command(str, aliases=["test-q, test-a, test-u, test-t"], give_name=True)
def test(content, alias_used="test"):
    """
    Test an answer to determine if it'd be automatically reported
    :param content:
    :return: A string
    """
    result = "> "
    kind = ""

    if alias_used == "test-q":
        kind = " question."
        fakepost = Post(api_response={'title': 'Valid title', 'body': content,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': False, 'score': 0})
    elif alias_used == "test-a":
        kind = "n answer."
        fakepost = Post(api_response={'title': 'Valid title', 'body': content,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': True, 'score': 0})
    elif alias_used == "test-u":
        kind = " username."
        fakepost = Post(api_response={'title': 'Valid title', 'body': "Valid question body",
                                      'owner': {'display_name': content, 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': False, 'score': 0})
    elif alias_used == "test-t":
        kind = " title."
        fakepost = Post(api_response={'title': content, 'body': "Valid question body",
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': False, 'score': 0})
    else:
        kind = " question, title or username."
        fakepost = Post(api_response={'title': content, 'body': content,
                                      'owner': {'display_name': content, 'reputation': 1, 'link': ''},
                                      'site': "", 'IsAnswer': False, 'score': 0})
    
    reasons, why = FindSpam.test_post(fakepost)

    if len(reasons) == 0:
        result += "Would not be caught as a{}".format(kind)
    else:
        result += ", ".join(reasons).capitalize()
    
        if why is not None and len(why) > 0:
            result += "\n----------\n"
            result += why
    
    return result


# noinspection PyIncorrectDocstring
@command
def threads():
    """
    Returns a description of current threads, for debugging
    :return: A string
    """

    threads = ("{ident}: {name}".format(ident=t.ident, name=t.name) for t in threading.enumerate())

    return "{threads}".format(threads="\n".join(list(threads)))


# noinspection PyIncorrectDocstring
@command(aliases=["rev"])
def version():
    """
    Returns the current version of the application
    :return: A string
    """

    return '{id} [{commit_name}]({repository}/commit/{commit_code})'.format(
            id=GlobalVars.location,
            commit_name=GlobalVars.commit_with_author,
            commit_code=GlobalVars.commit['id'],
            repository=GlobalVars.bot_repository))


# noinspection PyIncorrectDocstring
@command(whole_msg=True)
def whoami(msg):
    """
    Returns user id of smoke detector
    :param msg:
    :return:
    """
    return "My id for this room is {}, and it's not apnorton's fault.".format(msg._client._br.user_id)


# noinspection PyIncorrectDocstring
@command(int)
def pending():
    """
    Finds posts with TP feedback that have yet to be deleted.
    :param args: No additional arguments expected.
    :param kwargs: No additional arguments expected.
    :return:
    """
    posts = requests.get("https://metasmoke.erwaysoftware.com/api/undeleted?pagesize=2&page={}&key={}".format(
        page, GlobalVars.metasmoke_key)).json()

    messages = []
    for post in posts['items']:
        messages.append("[{0}]({1}) ([MS](https://m.erwaysoftware.com/post/{0}))".format(post['id'], post['link']))

    return ", ".join(messages))


# --- Notification functions --- #
# noinspection PyIncorrectDocstring
@command(int, whole_msg=True)
def allnotifications(msg, room_id):
    """
    Returns a string stating what sites a user will be notified about
    :param msg:
    :param room_id:
    :return: A string
    """
    sites = get_all_notification_sites(msg.owner.id, msg._client.host, room_id)

    if len(sites) == 0:
        return "You won't get notified for any sites in that room."

    return "You will get notified for these sites:\r\n" + ", ".join(sites)


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(int, str, whole_msg=True)
def notify(msg, room_id, se_site):
    """
    Subscribe a user to events on a site in a single room
    :param msg:
    :param room_id:
    :param site:
    :return: A string
    """
    response, full_site = add_to_notification_list(msg.owner.id, msg._client.host, room_id, se_site)

    if response == 0:
        return "You'll now get pings from me if I report a post on `{site}`, in room "
               "`{room}` on `chat.{domain}`".format(site=se_site, room=room_id, domain=msg._client.host))
    elif response == -1:
        return "That notification configuration is already registered."
    elif response == -2:
        return "The given SE site does not exist."
    else:
        return "Unrecognized code returned when adding notification."


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(str, whole_msg=True)
def command_whois(msg, role):
    """
    Return a list of important users
    :param msg:
    :param role:
    :return: A string
    """
    valid_roles = {"admin": "admin",
                   "code_admin": "code_admin",
                   "admins": "admin",
                   "codeadmins": "code_admin"}

    if role not in list(valid_roles.keys()):
        return "That is not a user level I can check. "
               "I know about {0}".format(", ".join(set(valid_roles.values())))

    ms_route = "https://metasmoke.erwaysoftware.com/api/users/?role={}&key={}&per_page=100".format(
        valid_roles[role],
        GlobalVars.metasmoke_key)

    user_response = requests.get(ms_route)
    user_response.encoding = 'utf-8-sig'
    user_response = user_response.json()

    chat_host = msg._client.host

    # Build our list of admin chat ids
    key = ""
    if chat_host == "stackexchange.com":
        key = 'stackexchange_chat_id'
    elif chat_host == "meta.stackexchange.com":
        key = 'meta_stackexchange_chat_id'
    elif chat_host == "stackoverflow.com":
        key = 'stackoverflow_chat_id'

    admin_ids = [a[key] for a in user_response['items'] if a[key] and a['id'] != -1]

    all_users_in_room = msg.room.get_current_user_ids()
    admins_in_room = list(set(admin_ids) & set(all_users_in_room))
    admins_not_in_room = list(set(admin_ids) - set(admins_in_room))

    admins_list = [(admin,
                    msg._client.get_user(admin).name,
                    msg._client.get_user(admin).last_message,
                    msg._client.get_user(admin).last_seen)
                   for admin in admin_ids]

    admins_in_room_list = [(admin,
                            msg._client.get_user(admin).name,
                            msg._client.get_user(admin).last_message,
                            msg._client.get_user(admin).last_seen)
                           for admin in admins_in_room]

    admins_not_in_room_list = [(admin,
                                msg._client.get_user(admin).name,
                                msg._client.get_user(admin).last_message,
                                msg._client.get_user(admin).last_seen)
                               for admin in admins_not_in_room]

    message = "I am aware of {} {}".format(len(admin_ids), message_parts[1])

    if admins_in_room_list:
        admins_in_room_list.sort(key=lambda x: x[2])    # Sort by last message (last seen = x[3])
        message += ". Currently in this room: **"
        for admin in admins_in_room_list:
            message += "{}, ".format(admin[1])
        message = message[:-2] + "**. "
        message += "Not currently in this room: "
        for admin in admins_not_in_room_list:
            message += "{}, ".format(admin[1])
        message = message[:-2] + "."

    else:
        message += ": "
        for admin in admins_list:
            message += "{}, ".format(admin[1])
        message = message[:-2] + ". "
        message += "None of them are currently in this room. Other users in this room might be able to help you."

    return message


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(int, str, whole_msg=True)
def unnotify(msg, room_id, se_site):
    """
    Unsubscribes a user to specific events
    :param msg:
    :param room_id:
    :param se_site:
    :return: A string
    """
    response = remove_from_notification_list(msg.owner.id, msg._client.host, room_id, se_site)

    if response:
        return "I will no longer ping you if I report a post on `{site}`, in room `{room}` "
               "on `chat.{domain}`".format(site=se_site, room=room_id, domain=msg._client.host))

    return "That configuration doesn't exist."


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(int, str, whole_msg=True)
def willbenotified(msg, room_id, se_site):
    """
    Returns a string stating whether a user will be notified or not
    :param msg:
    :param room_id:
    :param se_site:
    :return: A string
    """
    if will_i_be_notified(msg.owner.id, msg._client.host, room_id, se_site):
        return "Yes, you will be notified for that site in that room."

    return "No, you won't be notified for that site in that room."


# --- Post Responses --- #
# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True)
def command_report_post(msg, urls):
    """
    Report a post (or posts)
    :param msg:
    :param urls:
    :return: A string (or None)
    """
    crn, wait = can_report_now(msg.owner.id, msg_client.host)
    if not crn:
        return "You can execute the !!/report command again in {} seconds. "
               "To avoid one user sending lots of reports in a few commands and "
               "slowing SmokeDetector down due to rate-limiting, you have to "
               "wait 30 seconds after you've reported multiple posts using "
               "!!/report, even if your current command just has one URL. (Note "
               "that this timeout won't be applied if you only used !!/report "
               "for one post)".format(wait))

    output = []
    urls = list(set(urls.split()))

    if len(urls) > 5:
        return "To avoid SmokeDetector reporting posts too slowly, you can "
               "report at most 5 posts at a time. This is to avoid "
               "SmokeDetector's chat messages getting rate-limited too much, "
                "which would slow down reports."

    for index, url in enumerate(urls):
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

        why = u"Post manually reported by user *{}* in room *{}*.\n".format(msg.owner.name, msg.room.name)
        batch = ""
        if len(urls) > 1:
            batch = " (batch report: post {} out of {})".format(index, len(urls))

        handle_spam(post=post,
                    reasons=["Manually reported " + post_data.post_type + batch],
                    why=why)

    if 1 < len(urls) > len(output):
        add_or_update_multiple_reporter(msg.owner.id, msg._client.host, time.time())

    if len(output) > 0:
        return os.linesep.join(output))


#
#
# Subcommands go below here
# noinspection PyIncorrectDocstring,PyBroadException
@command(message, reply=True, aliases=["del", "poof", "gone", "kaboom"])
def delete(ev_room, ev_user_id, wrap2, msg, *args, **kwargs):
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
    "!!/amipriviledged": command_privileged,   # TODO: add typo warning?
    "!!/amicodeprivileged": command_code_privileged,
    "!!/amicodepriviledged": command_code_privileged,   # TODO: add typo warning?
    "!!/apiquota": command_quota,
    "!!/approve": command_approve,
    "!!/blame": command_blame,
    "!!/block": command_block,
    "!!/brownie": command_brownie,
    "!!/blacklist": command_blacklist_help,
    "!!/blacklist-website": command_blacklist_website,
    "!!/blacklist-keyword": command_blacklist_keyword,
    "!!/blacklist-username": command_blacklist_username,
    "!!/watch-keyword": command_watch_keyword,
    "!!/watch": command_watch_keyword,
    "!!/blacklist-website-force": command_force_blacklist_website,
    "!!/blacklist-keyword-force": command_force_blacklist_keyword,
    "!!/blacklist-username-force": command_force_blacklist_username,
    "!!/watch-keyword-force": command_force_watch_keyword,
    "!!/watch-force": command_force_watch_keyword,
    # "!!/unwatch-keyword": command_unwatch_keyword,  # TODO
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
    "!!/remote-diff": command_remotediff,
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
    "!!/whois": command_whois,
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
