# coding=utf-8
# noinspection PyUnresolvedReferences
from chatcommunicate import add_room, block_room, CmdException, command, get_report_data, is_privileged, message, \
    tell_rooms
# noinspection PyUnresolvedReferences
from globalvars import GlobalVars
from findspam import FindSpam
# noinspection PyUnresolvedReferences
from datetime import datetime
from utcdate import UtcDate
from apigetpost import api_get_post, PostData
import datahandling
from datahandling import *
from blacklists import load_blacklists
from parsing import *
from spamhandling import check_if_spam, handle_spam
from gitmanager import GitManager
import threading
import random
import requests
import os
import time
from html import unescape
from ast import literal_eval
# noinspection PyCompatibility
import regex
from helpers import only_blacklists_changed, log, expand_shorthand_link
from classes import Post
from classes.feedback import *


# TODO: Do we need uid == -2 check?  Turn into "is_user_valid" check
#
#
# System command functions below here

# The following two commands are just bypasses for the "unrecognized command" message, so that pingbot
# can respond instead.
@command(aliases=['ping-help'])
def ping_help():
    return None


@command()
def groups():
    return None


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
        message_url = "https://chat.{}/transcript/{}?m={}".format(msg._client.host, msg.room.id, msg.id)

        add_blacklisted_user((uid, val), message_url, "")
        return "User blacklisted (`{}` on `{}`).".format(uid, val)
    elif int(uid) == -2:
        raise CmdException("Error: {}".format(val))
    else:
        raise CmdException("Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`.")


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
        raise CmdException("Error: {}".format(val))
    else:
        raise CmdException("Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`.")


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
        raise CmdException("Error: {}".format(val))
    else:
        raise CmdException("Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`.")


# --- Whitelist functions --- #
# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@command(str, privileged=True)
def addwlu(user):
    """
    Adds a user to site whitelist
    :param user:
    :return: A string
    """
    uid, val = get_user_from_list_command(user)

    if int(uid) > -1 and val != "":
        add_whitelisted_user((uid, val))
        return "User whitelisted (`{}` on `{}`).".format(uid, val)
    elif int(uid) == -2:
        raise CmdException("Error: {}".format(val))
    else:
        raise CmdException("Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`.")


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyMissingTypeHints
@command(str)
def iswlu(user):
    """
    Checks if a user is whitelisted
    :param user:
    :return: A string
    """
    uid, val = get_user_from_list_command(user)

    if int(uid) > -1 and val != "":
        if is_whitelisted_user((uid, val)):
            return "User is whitelisted (`{}` on `{}`).".format(uid, val)
        else:
            return "User is not whitelisted (`{}` on `{}`).".format(uid, val)
    elif int(uid) == -2:
        raise CmdException("Error: {}".format(val))
    else:
        raise CmdException("Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`.")


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(str, privileged=True)
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
        raise CmdException("Error: {}".format(val))
    else:
        raise CmdException("Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`.")


# noinspection PyIncorrectDocstring
@command(str)
def blacklist(_):
    """
    Returns a string which explains the usage of the new blacklist commands.
    :return: A string
    """
    raise CmdException("The !!/blacklist command has been deprecated. "
                       "Please use !!/blacklist-website, !!/blacklist-username,"
                       "!!/blacklist-keyword, or perhaps !!/watch-keyword. "
                       "Remember to escape dots in URLs using \\.")


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


def do_blacklist(blacklist_type, msg, force=False):
    """
    Adds a string to the website blacklist and commits/pushes to GitHub
    :param raw_pattern:
    :param blacklist_type:
    :param msg:
    :param force:
    :return: A string
    """

    chat_user_profile_link = "https://chat.{host}/users/{id}".format(host=msg._client.host,
                                                                     id=msg.owner.id)

    # noinspection PyProtectedMember
    pattern = rebuild_str(msg.content_source.split(" ", 1)[1])
    try:
        regex.compile(pattern, city=FindSpam.city_list)
    except regex._regex_core.error:
        raise CmdException("An invalid pattern was provided, not blacklisting.")

    if not force:
        reasons = check_blacklist(pattern.replace("\\W", " ").replace("\\.", ".").replace("\\d", "8"),
                                  blacklist_type == "username",
                                  blacklist_type == "watch_keyword")

        if reasons:
            raise CmdException("That pattern looks like it's already caught by " + format_blacklist_reasons(reasons) +
                               "; append `-force` if you really want to do that.")

    _, result = GitManager.add_to_blacklist(
        blacklist=blacklist_type,
        item_to_blacklist=pattern,
        username=msg.owner.name,
        chat_profile_link=chat_user_profile_link,
        code_permissions=is_code_privileged(msg._client.host, msg.owner.id)
    )

    return result


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, give_name=True, aliases=["blacklist-keyword",
                                                                        "blacklist-website",
                                                                        "blacklist-username",
                                                                        "blacklist-keyword-force",
                                                                        "blacklist-website-force",
                                                                        "blacklist-username-force"])
def blacklist_keyword(msg, pattern, alias_used="blacklist-keyword"):
    """
    Adds a string to the blacklist and commits/pushes to GitHub
    :param msg:
    :param pattern:
    :return: A string
    """

    parts = alias_used.split("-")
    return do_blacklist(parts[1], msg, force=len(parts) > 2)


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, aliases=["watch-keyword"])
def watch(msg, website):
    """
    Adds a string to the watched keywords list and commits/pushes to GitHub
    :param msg:
    :param website:
    :return: A string
    """

    return do_blacklist("watch_keyword", msg, force=False)


@command(str, whole_msg=True, privileged=True)
def unwatch(msg, item):
    pattern = msg.content_source.split(" ", 1)[1]
    _status, message = GitManager.unwatch(rebuild_str(pattern), msg.owner.name, is_code_privileged(
        msg._client.host, msg.owner.id))
    return message


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, aliases=["watch-force", "watch-keyword-force"])
def watch_force(msg, website):
    """
    Adds a string to the watched keywords list and commits/pushes to GitHub
    :param msg:
    :param website:
    :return: A string
    """

    return do_blacklist("watch_keyword", msg, force=True)


# noinspection PyIncorrectDocstring
@command(privileged=True)
def gitstatus():
    return GitManager.current_git_status()


@command(privileged=True, aliases=["remote-diff", "remote_diff"])
def remotediff():
    will_require_full_restart = "SmokeDetector will require a full restart to pull changes: " \
                                "{}".format(str(not only_blacklists_changed(GitManager.get_remote_diff())))

    return "{}\n\n{}".format(GitManager.get_remote_diff(), will_require_full_restart)


# --- Joke Commands --- #
@command(whole_msg=True)
def blame(msg):
    unlucky_victim = msg._client.get_user(random.choice(msg.room.get_current_user_ids()))

    return "It's [{}](https://chat.{}/users/{})'s fault.".format(unlucky_victim.name,
                                                                 msg._client.host,
                                                                 unlucky_victim.id)


@command(str, whole_msg=True, aliases=["blame\u180E"])
def blame2(msg, x):
    base = {"\u180E": 0, "\u200B": 1, "\u200C": 2, "\u200D": 3, "\u2060": 4, "\u2063": 5, "\uFEFF": 6}
    user = 0

    for i, char in enumerate(reversed(x)):
        user += (len(base)**i) * base[char]

    try:
        unlucky_victim = msg._client.get_user(user)
        return "It's [{}](https://chat.{}/users/{})'s fault.".format(unlucky_victim.name,
                                                                     msg._client.host,
                                                                     unlucky_victim.id)

    except requests.exceptions.HTTPError:
        unlucky_victim = msg.owner
        return "It's [{}](https://chat.{}/users/{})'s fault.".format(unlucky_victim.name,
                                                                     msg._client.host,
                                                                     unlucky_victim.id)


# noinspection PyIncorrectDocstring
@command()
def brownie():
    """
    Returns a string equal to "Brown!" (This is a joke command)
    :return: A string
    """
    return "Brown!"


COFFEES = ['Espresso', 'Macchiato', 'Ristretto', 'Americano', 'Latte', 'Cappuccino', 'Mocha', 'Affogato']


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, arity=(0, 1))
def coffee(msg, other_user):
    """
    Returns a string stating who the coffee is for (This is a joke command)
    :param msg:
    :param other_user:
    :return: A string
    """
    if other_user is None:
        return "*brews a cup of {} for @{}*".format(random.choice(COFFEES), msg.owner.name.replace(" ", ""))
    else:
        other_user = regex.sub(r'^@*|\b\s.{1,}', '', other_user)
        return "*brews a cup of {} for @{}*".format(random.choice(COFFEES), other_user)


# noinspection PyIncorrectDocstring
@command()
def lick():
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
        other_user = regex.sub(r'^@*|\b\s.{1,}', '', other_user)
        return "*brews a cup of {} tea for @{}*".format(random.choice(TEAS), other_user)


# noinspection PyIncorrectDocstring
@command()
def wut():
    """
    Returns a string when a user asks 'wut' (This is a joke command)
    :return: A string
    """
    return "Whaddya mean, 'wut'? Humans..."


@command(aliases=["zomg_hats"])
def hats():
    wb_start = datetime(2017, 12, 13, 0, 0, 0)
    wb_end = datetime(2018, 1, 3, 0, 0, 0)
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

    return return_string


# --- Block application from posting functions --- #
# noinspection PyIncorrectDocstring
@command(int, int, whole_msg=True, privileged=True, arity=(1, 2))
def block(msg, block_time, room_id):
    """
    Blocks posts from application for a period of time
    :param msg:
    :param block_time:
    :param room_id:
    :return: None
    """
    time_to_block = block_time if 0 < block_time < 14400 else 900

    which_room = "globally" if room_id is None else "in room {} on {}".format(room_id, msg._client.host)
    block_message = "Reports blocked for {} second(s) {}.".format(time_to_block, which_room)
    tell_rooms(block_message, ((msg._client.host, msg.room.id), "debug", "metatavern"), ())

    block_room(room_id, msg._client.host, time.time() + time_to_block)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(int, int, whole_msg=True, privileged=True, arity=(1, 2))
def unblock(msg, room_id):
    """
    Unblocks posting to a room
    :param msg:
    :param room_id:
    :return: None
    """
    block_room(room_id, msg._client.host, -1)

    which_room = "globally" if room_id is None else "in room {} on {}".format(room_id, msg._client.host)
    unblock_message = "Reports unblocked {}.".format(which_room)

    tell_rooms(unblock_message, ((msg._client.host, msg.room.id), "debug", "metatavern"), ())


# --- Administration Commands --- #
# noinspection PyIncorrectDocstring
@command(aliases=["live"])
def alive():
    """
    Returns a string indicating the process is still active
    :return: A string
    """
    return random.choice(['Yup', 'You doubt me?', 'Of course',
                          '... did I miss something?', 'plz send teh coffee',
                          'Watching this endless list of new questions *never* gets boring',
                          'Kinda sorta'])


# noinspection PyIncorrectDocstring
@command(int, privileged=True, arity=(0, 1), aliases=["errlogs", "errlog", "errorlog"])
def errorlogs(count):
    """
    Shows the most recent lines in the error logs
    :param count:
    :return: A string
    """
    return fetch_lines_from_error_log(count or 50)


# noinspection PyIncorrectDocstring
@command(aliases=["commands", "help"])
def info():
    """
    Returns the help text
    :return: A string
    """
    return "I'm " + GlobalVars.chatmessage_prefix +\
           " a bot that detects spam and offensive posts on the network and"\
           " posts alerts to chat."\
           " [A command list is available here](https://charcoal-se.org/smokey/Commands)."


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, arity=(0, 1))
def welcome(msg, other_user):
    """
    Returns the welcome text
    :param msg:
    :param other_user:
    :return: A string
    """
    w_msg = ("Welcome to {room}{user}! I'm {me}, a bot that detects spam and offensive posts on the network, "
             "and posts alerts to chat. You can find more about me on the "
             "[Charcoal website](https://charcoal-se.org/).")
    if other_user is None:
        raise CmdException(w_msg.format(room=msg.room.name, user="", me=GlobalVars.chatmessage_prefix))
    else:
        other_user = regex.sub(r'^@*|\b\s.{1,}', '', other_user)
        raise CmdException(w_msg.format(room=msg.room.name, user=" @" + other_user, me=GlobalVars.chatmessage_prefix))


# noinspection PyIncorrectDocstring
@command()
def location():
    """
    Returns the current location the application is running from
    :return: A string with current location
    """
    return GlobalVars.location


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(privileged=True)
def master():
    """
    Forces a system exit with exit code = 8
    :return: None
    """
    os._exit(8)


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(privileged=True)
def pull():
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
        for ci_status in request.json():
            state = ci_status["state"]
            states.append(state)
        if "success" in states:
            os._exit(3)
        elif "error" in states or "failure" in states:
            raise CmdException("CI build failed! :( Please check your commit.")
        elif "pending" in states or not states:
            raise CmdException("CI build is still pending, wait until the build has finished and then pull again.")


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(whole_msg=True, privileged=True, aliases=["restart"])
def reboot(msg):
    """
    Forces a system exit with exit code = 5
    :param msg:
    :return: None
    """
    tell_rooms("Goodbye, cruel world", ("debug", (msg._client.host, msg.room.id)), ())
    time.sleep(3)
    os._exit(5)


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(whole_msg=True)
def amiprivileged(msg):
    """
    Tells user whether or not they have privileges
    :param msg:
    :return: A string
    """
    if is_privileged(msg.owner, msg.room):
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
    if is_code_privileged(msg._client.host, msg.owner.id):
        return "\u2713 You are a code-privileged user."

    return "\u2573 No, you are not a code-privileged user."


# noinspection PyIncorrectDocstring
@command()
def apiquota():
    """
    Report how many API hits remain for the day
    :return: A string
    """
    return "The current API quota remaining is {}.".format(GlobalVars.apiquota)


# noinspection PyIncorrectDocstring
@command()
def queuestatus():
    """
    Report current API queue
    :return: A string
    """
    return GlobalVars.bodyfetcher.print_queue()


@command(str)
def inqueue(url):
    post_id, site, post_type = fetch_post_id_and_site_from_url(url)

    if post_type != "question":
        raise CmdException("Can't check for answers.")

    if site in GlobalVars.bodyfetcher.queue:
        for i, id in enumerate(GlobalVars.bodyfetcher.queue[site].keys()):
            if id == post_id:
                return "#" + str(i + 1) + " in queue."

    return "Not in queue."


@command()
def listening():
    # return "{} post(s) currently monitored for deletion.".format(len(GlobalVars.deletion_watcher.posts))
    return "Currently listening to:\n" + repr(GlobalVars.deletion_watcher.posts)


@command()
def last_feedbacked():
    return datahandling.last_feedbacked


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(str, whole_msg=True, privileged=True, arity=(0, 1))
def stappit(msg, location_search):
    """
    Forces a system exit with exit code = 6
    :param msg:
    :param location_search:
    :return: None
    """
    if location_search is None or location_search.lower() in GlobalVars.location.lower():
        tell_rooms("Goodbye, cruel world", ((msg._client.host, msg.room.id)), ())

        time.sleep(3)
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
@command()
def status():
    """
    Returns the amount of time the application has been running
    :return: A string
    """
    now = datetime.utcnow()
    diff = now - UtcDate.startup_utc_date

    return 'Running since {time} UTC ({relative})'.format(time=GlobalVars.startup_utc, relative=td_format(diff))


# noinspection PyIncorrectDocstring
@command(privileged=True, whole_msg=True)
def stopflagging(msg):
    Tasks.do(Metasmoke.stop_autoflagging)
    log('warning', 'Disabling autoflagging ({} ran !!/stopflagging, message {})'.format(msg.owner.name, msg.id))
    return 'Stopping'


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(str, whole_msg=True, privileged=True, aliases=["standby-except"], give_name=True)
def standby(msg, location_search, alias_used="standby"):
    """
    Forces a system exit with exit code = 7
    :param msg:
    :param location_search:
    :return: None
    """

    match = location_search.lower() in GlobalVars.location.lower()
    reverse_search = "except" in alias_used

    # Use `!=` as Logical XOR
    if match != reverse_search:
        tell_rooms("{location} is switching to standby".format(location=GlobalVars.location),
                   ("debug", (msg._client.host, msg.room.id)), (), notify_site="/standby")

        time.sleep(3)
        os._exit(7)


# noinspection PyIncorrectDocstring
@command(str, aliases=["test-q", "test-a", "test-u", "test-t"], give_name=True)
def test(content, alias_used="test"):
    """
    Test an answer to determine if it'd be automatically reported
    :param content:
    :return: A string
    """
    result = "> "
    site = ""

    option_count = 0
    for segment in content.split():
        if segment.startswith("site="):
            site = expand_shorthand_link(segment[5:])
        else:
            # Stop parsing options at first non-option
            break
        option_count += 1
    content = content.split(' ', option_count)[-1]  # Strip parsed options

    if alias_used == "test-q":
        kind = "a question"
        fakepost = Post(api_response={'title': 'Valid title', 'body': content,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})
    elif alias_used == "test-a":
        kind = "an answer"
        fakepost = Post(api_response={'title': 'Valid title', 'body': content,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': True, 'score': 0})
    elif alias_used == "test-u":
        kind = "a username"
        fakepost = Post(api_response={'title': 'Valid title', 'body': "Valid question body",
                                      'owner': {'display_name': content, 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})
    elif alias_used == "test-t":
        kind = "a title"
        fakepost = Post(api_response={'title': content, 'body': "Valid question body",
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})
    else:
        kind = "a post, title or username"
        fakepost = Post(api_response={'title': content, 'body': content,
                                      'owner': {'display_name': content, 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})

    reasons, why_response = FindSpam.test_post(fakepost)

    if len(reasons) == 0:
        result += "Would not be caught as {}".format(kind)

        if site == "chat.stackexchange.com":
            result += " on this magic userspace"
        elif len(site) > 0:
            result += " on site `{}`".format(site)
        result += "."
    else:
        result += ", ".join(reasons).capitalize()

        if why_response is not None and len(why_response) > 0:
            result += "\n----------\n"
            result += why_response

    return result


# noinspection PyIncorrectDocstring
@command()
def threads():
    """
    Returns a description of current threads, for debugging
    :return: A string
    """

    threads_list = ("{ident}: {name}".format(ident=t.ident, name=t.name) for t in threading.enumerate())

    return "{threads}".format(threads="\n".join(list(threads_list)))


# noinspection PyIncorrectDocstring
@command(aliases=["rev", "ver"])
def version():
    """
    Returns the current version of the application
    :return: A string
    """

    return '{id} [{commit_name}]({repository}/commit/{commit_code})'.format(id=GlobalVars.location,
                                                                            commit_name=GlobalVars.commit_with_author,
                                                                            commit_code=GlobalVars.commit['id'],
                                                                            repository=GlobalVars.bot_repository)


# noinspection PyIncorrectDocstring
@command(whole_msg=True)
def whoami(msg):
    """
    Returns user id of smoke detector
    :param msg:
    :return:
    """
    return "My id for this room is {}, and it's not apnorton's fault.".format(msg._client._br.user_id)


# --- Notification functions --- #
# noinspection PyIncorrectDocstring
@command(int, whole_msg=True, aliases=["allnotifications", "allnoti"])
def allnotificationsites(msg, room_id):
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
@command(int, str, literal_eval, whole_msg=True, arity=(2, 3))
def notify(msg, room_id, se_site, always_ping):
    """
    Subscribe a user to events on a site in a single room
    :param msg:
    :param room_id:
    :param se_site:
    :return: A string
    """
    # TODO: Add check whether smokey reports in that room
    response, full_site = add_to_notification_list(msg.owner.id, msg._client.host, room_id, se_site,
                                                   always_ping=(always_ping if always_ping is not None else True))

    if response == 0:
        return "You'll now get pings from me if I report a post on `{site}`, in room "\
               "`{room}` on `chat.{domain}`".format(site=se_site, room=room_id, domain=msg._client.host)
    elif response == -1:
        raise CmdException("That notification configuration is already registered.")
    elif response == -2:
        raise CmdException("The given SE site does not exist.")
    else:
        raise CmdException("Unrecognized code returned when adding notification.")


# temp command
@command(privileged=True)
def migrate_notifications():
    for i, notification in enumerate(GlobalVars.notifications):
        if len(notification) == 4:
            GlobalVars.notifications[i] = notification + (True,)

    with open("notifications.p", "wb") as f:
        pickle.dump(GlobalVars.notifications, f, protocol=pickle.HIGHEST_PROTOCOL)

    return "shoutouts to simpleflips"


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(whole_msg=True, aliases=["unnotify-all"])
def unnotify_all(msg):
    """
    Unsubscribes a user to all events
    :param msg:
    :return: A string
    """
    remove_all_from_notification_list(msg.owner.id)
    return "I will no longer ping you if I report a post anywhere."


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
        return "I will no longer ping you if I report a post on `{site}`, in room `{room}` "\
               "on `chat.{domain}`".format(site=se_site, room=room_id, domain=msg._client.host)

    raise CmdException("That configuration doesn't exist.")


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


RETURN_NAMES = {"admin": ["admin", "admins"], "code_admin": ["code admin", "code admins"]}
VALID_ROLES = {"admin": "admin",
               "code_admin": "code_admin",
               "admins": "admin",
               "codeadmins": "code_admin"}


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(str, whole_msg=True)
def whois(msg, role):
    """
    Return a list of important users
    :param msg:
    :param role:
    :return: A string
    """
    if role not in VALID_ROLES:
        raise CmdException("That is not a user level I can check. "
                           "I know about {0}".format(", ".join(set(VALID_ROLES.values()))))

    filter = "HMMKFJ"
    ms_route = "https://metasmoke.erwaysoftware.com/api/v2.0/users/with_role/{}?key={}&per_page=100&filter={}".format(
        VALID_ROLES[role],
        GlobalVars.metasmoke_key,
        filter)

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

    return_name = RETURN_NAMES[VALID_ROLES[role]][0 if len(admin_ids) == 1 else 1]

    response = "I am aware of {} {}".format(len(admin_ids), return_name)

    if admins_in_room_list:
        admins_in_room_list.sort(key=lambda x: x[2])    # Sort by last message (last seen = x[3])
        response += ". Currently in this room: **"
        for admin in admins_in_room_list:
            response += "{}, ".format(admin[1])
        response = response[:-2] + "**. "
        response += "Not currently in this room: "
        for admin in admins_not_in_room_list:
            response += "{}, ".format(admin[1])
        response = response[:-2] + "."

    else:
        response += ": "
        for admin in admins_list:
            response += "{}, ".format(admin[1])
        response = response[:-2] + ". "
        response += "None of them are currently in this room. Other users in this room might be able to help you."

    return response


@command(int, str, privileged=True, whole_msg=True)
def invite(msg, room_id, roles):
    add_room((msg._client.host, room_id), roles.split(","))

    return "I'll now send messages with types `{}` to room `{}` on `{}`." \
           " (Note that this will not persist after restarts.)".format(roles, room_id, msg._client.host)


# --- Post Responses --- #
# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True)
def report(msg, args):
    """
    Report a post (or posts)
    :param msg:
    :return: A string (or None)
    """
    crn, wait = can_report_now(msg.owner.id, msg._client.host)
    if not crn:
        raise CmdException("You can execute the !!/report command again in {} seconds. "
                           "To avoid one user sending lots of reports in a few commands and "
                           "slowing SmokeDetector down due to rate-limiting, you have to "
                           "wait 30 seconds after you've reported multiple posts in "
                           "one go.".format(wait))

    output = []

    argsraw = args.split(' "', 1)
    urls = argsraw[0].split(' ')

    # Handle determining whether a custom report reason was provided.
    try:
        # Custom handle trailing quotation marks at the end of the custom reason, which could happen.
        if argsraw[1][-1] is '"':
            custom_reason = argsraw[1][:-1]
        else:
            custom_reason = argsraw[1]

        # Deny cases of multiple close reasons, in which case custom_reason will still have " chars in it.
        if '"' in custom_reason:
            raise CmdException("You cannot provide multiple custom report reasons. "
                               "Please review the permitted !!/report syntax in the documentation "
                               "for guidance on using custom report reasons.")
    except IndexError:
        custom_reason = None

    urls = list(set(urls))

    if len(urls) > 5:
        raise CmdException("To avoid SmokeDetector reporting posts too slowly, you can "
                           "report at most 5 posts at a time. This is to avoid "
                           "SmokeDetector's chat messages getting rate-limited too much, "
                           "which would slow down reports.")

    for index, url in enumerate(urls, start=1):
        url = rebuild_str(url)
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

            if GlobalVars.metasmoke_key is not None:
                se_link = to_protocol_relative(post_data.post_url)
                ms_link = "https://m.erwaysoftware.com/posts/by-url?url={}".format(se_link)
                output.append("Post {}: Already recently reported [ [MS]({}) ]".format(index, ms_link))
                continue
            else:
                output.append("Post {}: Already recently reported".format(index))
                continue

        post_data.is_answer = (post_data.post_type == "answer")
        post = Post(api_response=post_data.as_dict)
        user = get_user_from_url(post_data.owner_url)

        scan_spam, scan_reasons, scan_why = check_if_spam(post)  # Scan it first
        # Scan before adding blacklist to prevent showing all reported posts as "Blacklisted user"

        if user is not None:
            message_url = "https://chat.{}/transcript/{}?m={}".format(msg._client.host, msg.room.id, msg.id)
            add_blacklisted_user(user, message_url, post_data.post_url)

        if custom_reason:
            why_info = u"Post manually reported by user *{}* in room *{}* with reason: *{}*.\n".format(
                msg.owner.name, msg.room.name, custom_reason
            )
        else:
            why_info = u"Post manually reported by user *{}* in room *{}*.\n".format(msg.owner.name, msg.room.name)

        batch = ""
        if len(urls) > 1:
            batch = " (batch report: post {} out of {})".format(index, len(urls))

        if scan_spam:
            why_append = u"This post would have also been caught for: " + ", ".join(scan_reasons).capitalize() + \
                '\n' + scan_why
        else:
            why_append = u"This post would not have been caught otherwise."

        handle_spam(post=post,
                    reasons=["Manually reported " + post_data.post_type + batch],
                    why=why_info + '\n' + why_append)

    if 1 < len(urls) > len(output):
        add_or_update_multiple_reporter(msg.owner.id, msg._client.host, time.time())

    if len(output) > 0:
        return os.linesep.join(output)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(str, whole_msg=True, give_name=True, aliases=['scan', 'test-p'])
def checkpost(msg, args, alias_used='scan'):
    """
    Force Smokey to scan a post even if it has no recent activity
    :param msg:
    :param url:
    :return str:
    """
    crn, wait = can_report_now(msg.owner.id, msg._client.host)
    if not crn:
        raise CmdException("You can execute the !!/{0} command again in {1} seconds. "
                           "To avoid one user sending lots of reports in a few commands and "
                           "slowing SmokeDetector down due to rate-limiting, you have to "
                           "wait 30 seconds after you've scanned multiple posts in "
                           "one go.".format(alias_used, wait))

    urls = args.split()

    if len(urls) > 5:
        raise CmdException("To avoid SmokeDetector reporting posts too slowly, you can "
                           "scan at most 5 posts at a time. This is to avoid "
                           "SmokeDetector's chat messages getting rate-limited too much, "
                           "which would slow down reports.")

    response = []

    for index, url in enumerate(urls):
        post_data = api_get_post(rebuild_str(url))

        if post_data is None:
            response.append((index, "That does not look like a valid post URL."))

        if post_data is False:
            response.append((index, "Cannot find data for this post in the API. "
                                    "It may have already been deleted."))

        # Update url to be consistent with other code
        url = to_protocol_relative(post_data.post_url)
        post = Post(api_response=post_data.as_dict)

        if has_already_been_posted(post_data.site, post_data.post_id, post_data.title) \
                and not is_false_positive((post_data.post_id, post_data.site)):
            # Don't re-report if the post wasn't marked as a false positive. If it was marked as a false positive,
            # this force scan might be attempting to correct that/fix a mistake/etc.

            response_text = "This post is already recently reported"
            if GlobalVars.metasmoke_key is not None:
                ms_link = "https://m.erwaysoftware.com/posts/by-url?url={}".format(url)  # se_link == url
                response.append((index, response_text + " [ [MS]({}) ]".format(ms_link)))
            else:
                response.append((index, response_text + "."))

        if fetch_post_id_and_site_from_url(url)[2] == "answer":
            parent = api_get_post("https://{}/q/{}".format(post.post_site, post_data.question_id))

            post._is_answer = True
            post._parent = Post(api_response=parent.as_dict)

        is_spam, reasons, why = check_if_spam(post)

        if is_spam:
            handle_spam(post=post, reasons=reasons, why=why + "\nManually triggered scan")
            continue

        response.append((index, "Post [{}]({}) does not look like spam.".format(sanitize_title(post_data.title), url)))

    if len(response) == 0:
        return None
    elif len(response) == 1:
        return response[0][1]
    else:
        return "\n".join("URL {}: {}".format(index + 1, text) for index, text in response)


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(str, whole_msg=True, privileged=True, aliases=['reportuser'])
def allspam(msg, url):
    """
    Reports all of a user's posts as spam
    :param msg:
    :param url: A user profile URL
    :return:
    """
    crn, wait = can_report_now(msg.owner.id, msg._client.host)
    if not crn:
        raise CmdException("You can execute the !!/allspam command again in {} seconds. "
                           "To avoid one user sending lots of reports in a few commands and "
                           "slowing SmokeDetector down due to rate-limiting, you have to "
                           "wait 30 seconds after you've reported multiple posts in "
                           "one go.".format(wait))
    user = get_user_from_url(url)
    if user is None:
        raise CmdException("That doesn't look like a valid user URL.")
    user_sites = []
    user_posts = []
    # Detect whether link is to network profile or site profile
    if user[1] == 'stackexchange.com':
        # Respect backoffs etc
        GlobalVars.api_request_lock.acquire()
        if GlobalVars.api_backoff_time > time.time():
            time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
        # Fetch sites
        api_filter = "!6Pbp)--cWmv(1"
        request_url = "http://api.stackexchange.com/2.2/users/{}/associated?filter={}&key=IAkbitmze4B8KpacUfLqkw((" \
            .format(user[0], api_filter)
        res = requests.get(request_url).json()
        if "backoff" in res:
            if GlobalVars.api_backoff_time < time.time() + res["backoff"]:
                GlobalVars.api_backoff_time = time.time() + res["backoff"]
        GlobalVars.api_request_lock.release()
        if 'items' not in res or len(res['items']) == 0:
            raise CmdException("The specified user does not appear to exist.")
        if res['has_more']:
            raise CmdException("The specified user has an abnormally high number of accounts. Please consider flagging "
                               "for moderator attention, otherwise use !!/report on the user's posts individually.")
        # Add accounts with posts
        for site in res['items']:
            if site['question_count'] > 0 or site['answer_count'] > 0:
                user_sites.append((site['user_id'], get_api_sitename_from_url(site['site_url'])))
    else:
        user_sites.append((user[0], get_api_sitename_from_url(user[1])))
    # Fetch posts
    for u_id, u_site in user_sites:
        # Respect backoffs etc
        GlobalVars.api_request_lock.acquire()
        if GlobalVars.api_backoff_time > time.time():
            time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
        # Fetch posts
        api_filter = "!)Q4RrMH0DC96Y4g9yVzuwUrW"
        request_url = "http://api.stackexchange.com/2.2/users/{}/posts?site={}&filter={}&key=IAkbitmze4B8KpacUfLqkw((" \
            .format(u_id, u_site, api_filter)
        res = requests.get(request_url).json()
        if "backoff" in res:
            if GlobalVars.api_backoff_time < time.time() + res["backoff"]:
                GlobalVars.api_backoff_time = time.time() + res["backoff"]
        GlobalVars.api_request_lock.release()
        if 'items' not in res or len(res['items']) == 0:
            raise CmdException("The specified user has no posts on this site.")
        posts = res['items']
        if posts[0]['owner']['reputation'] > 100:
            raise CmdException("The specified user's reputation is abnormally high. Please consider flagging for "
                               "moderator attention, otherwise use !!/report on the posts individually.")
        # Add blacklisted user - use most downvoted post as post URL
        message_url = "https://chat.{}/transcript/{}?m={}".format(msg._client.host, msg.room.id, msg.id)
        add_blacklisted_user(user, message_url, sorted(posts, key=lambda x: x['score'])[0]['owner']['link'])
        # TODO: Postdata refactor, figure out a better way to use apigetpost
        for post in posts:
            post_data = PostData()
            post_data.post_id = post['post_id']
            post_data.post_url = url_to_shortlink(post['link'])
            *discard, post_data.site, post_data.post_type = fetch_post_id_and_site_from_url(
                url_to_shortlink(post['link']))
            post_data.title = unescape(post['title'])
            post_data.owner_name = unescape(post['owner']['display_name'])
            post_data.owner_url = post['owner']['link']
            post_data.owner_rep = post['owner']['reputation']
            post_data.body = post['body']
            post_data.score = post['score']
            post_data.up_vote_count = post['up_vote_count']
            post_data.down_vote_count = post['down_vote_count']
            if post_data.post_type == "answer":
                # Annoyingly we have to make another request to get the question ID, since it is only returned by the
                # /answers route
                # Respect backoffs etc
                GlobalVars.api_request_lock.acquire()
                if GlobalVars.api_backoff_time > time.time():
                    time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
                # Fetch posts
                filter = "!*Jxb9s5EOrE51WK*"
                req_url = "http://api.stackexchange.com/2.2/answers/{}?site={}&filter={}&key=IAkbitmze4B8KpacUfLqkw((" \
                    .format(post['post_id'], u_site, filter)
                answer_res = requests.get(req_url).json()
                if "backoff" in res:
                    if GlobalVars.api_backoff_time < time.time() + res["backoff"]:
                        GlobalVars.api_backoff_time = time.time() + res["backoff"]
                GlobalVars.api_request_lock.release()
                # Finally, set the attribute
                post_data.question_id = answer_res['items'][0]['question_id']
                post_data.is_answer = True
            user_posts.append(post_data)
    if len(user_posts) == 0:
        raise CmdException("The specified user hasn't posted anything.")
    if len(user_posts) > 15:
        raise CmdException("The specified user has an abnormally high number of spam posts. Please consider flagging "
                           "for moderator attention, otherwise use !!/report on the posts individually.")
    why_info = u"User manually reported by *{}* in room *{}*.\n".format(msg.owner.name, msg.room.name)
    # Handle all posts
    for index, post in enumerate(user_posts, start=1):
        batch = ""
        if len(user_posts) > 1:
            batch = " (batch report: post {} out of {})".format(index, len(user_posts))
        handle_spam(post=Post(api_response=post.as_dict),
                    reasons=["Manually reported " + post.post_type + batch],
                    why=why_info)
        time.sleep(2)  # Should this be implemented differently?
    if len(user_posts) > 2:
        add_or_update_multiple_reporter(msg.owner.id, msg._client.host, time.time())


@command(str, str, privileged=True, whole_msg=True)
def feedback(msg, post_url, feedback):
    post_url = url_to_shortlink(post_url)[5:]

    for feedbacks in (TRUE_FEEDBACKS, FALSE_FEEDBACKS, NAA_FEEDBACKS):
        if feedback in feedbacks:
            feedbacks[feedback].send(post_url, msg)
            return

    raise CmdException("No such feedback.")


#
#
# Subcommands go below here
# noinspection PyIncorrectDocstring,PyBroadException
DELETE_ALIASES = ["delete", "del", "remove", "poof", "gone", "kaboom"]


@command(message, reply=True, privileged=True, aliases=[alias + "-force" for alias in DELETE_ALIASES])
def delete_force(msg):
    """
    Delete a post from the room, ignoring protection for Charcoal HQ
    :param msg:
    :return: None
    """
    # noinspection PyBroadException
    try:
        msg.delete()
    except:
        pass  # couldn't delete message


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyBroadException
@command(message, reply=True, privileged=True, aliases=DELETE_ALIASES)
def delete(msg):
    """
    Delete a post from a chatroom, with an override for Charcoal HQ.
    :param msg:
    :return: None
    """

    post_data = get_report_data(msg)
    if post_data and msg.room.id == 11540:
        return "Reports from SmokeDetector in Charcoal HQ are generally kept "\
               "as records. If you really need to delete a report, please use "\
               "`sd delete-force`. See [this note on message deletion]"\
               "(https://charcoal-se.org/smokey/Commands"\
               "#a-note-on-message-deletion) for more details."
    else:
        try:
            msg.delete()
        except:
            pass


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(message, reply=True, privileged=True)
def postgone(msg):
    """
    Removes link from a marked report message
    :param msg:
    :return: None
    """
    edited = edited_message_after_postgone_command(msg.content)

    if edited is None:
        raise CmdException("That's not a report.")

    msg.edit(edited)


# noinspection PyIncorrectDocstring
@command(message, str, reply=True, privileged=True, whole_msg=True, give_name=True, aliases=FALSE_FEEDBACKS.keys(),
         arity=(1, 2))
def false(feedback, msg, comment, alias_used="false"):
    """
    Marks a post as a false positive
    :param feedback:
    :param msg:
    :return: String
    """
    post_data = get_report_data(msg)
    if not post_data:
        raise CmdException("That message is not a report.")

    post_url, owner_url = post_data

    feedback_type = FALSE_FEEDBACKS[alias_used]
    feedback_type.send(post_url, feedback)

    post_id, site, post_type = fetch_post_id_and_site_from_url(post_url)
    add_false_positive((post_id, site))

    user = get_user_from_url(owner_url)

    if user is not None:
        if feedback_type.blacklist:
            add_whitelisted_user(user)
            result = "Registered " + post_type + " as false positive and whitelisted user."
        elif is_blacklisted_user(user):
            remove_blacklisted_user(user)
            result = "Registered " + post_type + " as false positive and removed user from the blacklist."
        else:
            result = "Registered " + post_type + " as false positive."
    else:
        result = "Registered " + post_type + " as false positive."

    try:
        if msg.room.id != 11540:
            msg.delete()
    except:
        pass

    if comment:
        Tasks.do(Metasmoke.post_auto_comment, comment, feedback.owner, url=post_url)

    return result if not feedback_type.always_silent else ""


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(message, str, reply=True, privileged=True, whole_msg=True, arity=(1, 2))
def ignore(feedback, msg, comment):
    """
    Marks a post to be ignored
    :param feedback:
    :param msg:
    :return: String
    """
    post_data = get_report_data(msg)
    if not post_data:
        raise CmdException("That message is not a report.")

    post_url, _ = post_data

    Feedback.send_custom("ignore", post_url, feedback)

    post_id, site, _ = fetch_post_id_and_site_from_url(post_url)
    add_ignored_post((post_id, site))

    if comment:
        Tasks.do(Metasmoke.post_auto_comment, comment, feedback.owner, url=post_url)

    return "Post ignored; alerts about it will no longer be posted."


# noinspection PyIncorrectDocstring
@command(message, str, reply=True, privileged=True, whole_msg=True, give_name=True, aliases=NAA_FEEDBACKS.keys(),
         arity=(1, 2))
def naa(feedback, msg, comment, alias_used="naa"):
    """
    Marks a post as NAA
    :param feedback:
    :param msg:
    :return: String
    """
    post_data = get_report_data(msg)
    if not post_data:
        raise CmdException("That message is not a report.")

    post_url, _ = post_data
    post_id, site, post_type = fetch_post_id_and_site_from_url(post_url)

    if post_type != "answer":
        raise CmdException("That report was a question; questions cannot be marked as NAAs.")

    feedback_type = NAA_FEEDBACKS[alias_used]
    feedback_type.send(post_url, feedback)

    post_id, site, _ = fetch_post_id_and_site_from_url(post_url)
    add_ignored_post((post_id, site))

    if comment:
        Tasks.do(Metasmoke.post_auto_comment, comment, feedback.owner, url=post_url)

    return "Recorded answer as an NAA in metasmoke." if not feedback_type.always_silent else ""


# noinspection PyIncorrectDocstring
@command(message, str, reply=True, privileged=True, whole_msg=True, give_name=True, aliases=TRUE_FEEDBACKS.keys(),
         arity=(1, 2))
def true(feedback, msg, comment, alias_used="true"):
    """
    Marks a post as a true positive
    :param feedback:
    :param msg:
    :return: string
    """
    post_data = get_report_data(msg)
    if not post_data:
        raise CmdException("That message is not a report.")

    post_url, owner_url = post_data

    feedback_type = TRUE_FEEDBACKS[alias_used]
    feedback_type.send(post_url, feedback)

    post_id, site, post_type = fetch_post_id_and_site_from_url(post_url)
    user = get_user_from_url(owner_url)

    if user is not None:
        if feedback_type.blacklist:
            message_url = "https://chat.{}/transcript/{}?m={}".format(msg._client.host, msg.room.id, msg.id)
            add_blacklisted_user(user, message_url, post_url)

            result = "Registered " + post_type + " as true positive and blacklisted user."
        else:
            result = "Registered " + post_type + " as true positive. If you want to "\
                     "blacklist the poster, use `trueu` or `tpu`."
    else:
        result = "Registered " + post_type + " as true positive."

    if comment:
        Tasks.do(Metasmoke.post_auto_comment, comment, feedback.owner, url=post_url)

    datahandling.last_feedbacked = ((post_id, site), time.time() + 60)

    return result if not feedback_type.always_silent else ""


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(message, reply=True, aliases=['wtf'])
def why(msg):
    """
    Returns reasons a post was reported
    :param msg:
    :return: A string
    """
    post_data = get_report_data(msg)
    if not post_data:
        raise CmdException("That's not a report.")
    else:
        *post, _ = fetch_post_id_and_site_from_url(post_data[0])
        why_info = get_why(post[1], post[0])
        if why_info:
            return why_info
        else:
            raise CmdException("There is no `why` data for that user (anymore).")


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(message, reply=True)
def autoflagged(msg):
    """
    Determines whether a post was automatically flagged by Metasmoke
    :param msg:
    :return: A string
    """
    post_data = get_report_data(msg)

    if not post_data:
        raise CmdException("That's not a report.")

    is_autoflagged, names = Metasmoke.determine_if_autoflagged(post_data[0])

    if is_autoflagged:
        return "That post was automatically flagged, using flags from: {}.".format(", ".join(names))
    else:
        return "That post was **not** automatically flagged by metasmoke."
