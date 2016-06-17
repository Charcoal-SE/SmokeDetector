from globalvars import GlobalVars
from findspam import FindSpam
from datetime import datetime
from utcdate import UtcDate
from datahandling import is_privileged
from datahandling import will_i_be_notified
from datahandling import get_all_notification_sites
from datahandling import remove_from_notification_list
from datahandling import add_to_notification_list
from chatcommunicate import post_message_in_room
from parsing import get_user_from_url
from spamhandling import handle_user_with_all_spam
import random
import requests
import os
import time


# TODO: pull out code block to get user_id, chat_site, room_id into function
# TODO: Order functions by groups
# TODO: Return result for all functions should be similar (tuple/named tuple?)
# TODO: Do we need uid == -2 check?

# Functions go before the final dictionary of command to function mappings


def is_report(post_site_id):
    """
    Checks if a post is a report
    :param post_site_id: Report to check
    :return: Boolean stating if it is a report
    """
    if post_site_id is None:
        return False
    return True


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


def command_allnotifications(*args, *kwargs):
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


def command_clean_blacklist(*args, **kwargs):
    """
    Clears the existing black list
    :param kwargs: Requires 'ev_room', 'ev_user_id', 'wrap2' is passed as kwarg
    :return: A string
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        if os.path.isfile("blacklistedUsers.txt"):
            os.remove("blacklistedUsers.txt")
            GlobalVars.blacklisted_users = []
            return "Kaboom, blacklisted users cleared."
        return "There are no blacklisted users at the moment."


def command_coffee(*args, **kwargs):
    """
    Returns a string stating who the coffee is for (This is a joke command)
    :param kwargs: Requires that 'ev_user_name' is passed as a kwarg
    :return: A string
    """
    return "*brews coffee for @" + kwargs['ev_user_name'].replace(" ", "") + "*"


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


def command_lick(*args, **kwargs):
    """
    Returns a string when a user says 'lick' (This is a joke command)
    :return: A string
    """
    return "*licks ice cream cone*"


def command_master(*args, **kwargs):
    """
    Forces a system exit with exit code = 8
    :param kwargs: Requires 'ev_room', 'ev_user_id' and 'wrap2' is passed as kwarg
    :return: None
    """
    if is_privileged(kwargs['ev_room'], kwargs['ev_user_id'], kwargs['wrap2']):
        os._exit(8)


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


def command_tea(*args, **kwargs):
    """
    Returns a string stating who the tea is for (This is a joke command)
    :param kwargs: Requires that 'ev_user_name' is passed as a kwarg
    :return: A string
    """
    return "*brews a cup of {choice} tea for @{user}*".format(
        choice=random.choice(['earl grey', 'green', 'chamomile', 'lemon', 'darjeeling', 'mint', 'jasmine']),
        user=kwargs['ev_user_name'].replace(" ", ""))


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


def command_unblock(*args, *kwargs):
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


def command_version(*args, **kwargs):
    """
    Returns the current version of the application
    :return: A string
    """
    return '[{commit_name}](https://github.com/Charcoal-SE/SmokeDetector/commit/{commit_code})'.format(
        commit_name=GlobalVars.commit_with_author, commit_code=GlobalVars.commit)

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


def command_whoami(*args, **kwargs):
    """
    Returns user id of smoke detector
    :param kwargs: Requires 'ev_room' is passed as a kwarg
    :return:
    """
    if kwargs['ev_room'] in GlobalVars.smokeDetector_user_id:
        return "My id for this room is {}.".format(GlobalVars.smokeDetector_user_id[kwargs['ev_room']])
    return "I don't know my user ID for this room. (Something is wrong, and it's apnorton's fault.)"


def command_wut(*args, **kwargs):
    """
    Returns a string when a user asks 'wut' (This is a joke command)
    :return: A string
    """
    return "Whaddya mean, 'wut'? Humans..."

#
#
#
# This dictionary defines our commands and the associated function to call
# To use this your calling code will look like this
#    command_dict['command'](paramer1, parameter2, ...)
# Each key can have a different set of parameters so 'command1' could look like this
#    command_dict['command1'](paramer1)
command_dict = {
    "!!/alive": command_alive,
    "!!/allnotificationsites": command_allnotifications,
    "!!/allspam": command_allspam,
    "!!/amiprivileged": command_privileged,
    "!!/apiquota": command_quota,
    "!!/blame": command_blame,
    "!!/block": command_block,
    "!!/brownie": command_brownie,
    "!!/clearbl": command_clean_blacklist,
    "!!/commands": command_help,
    "!!/coffee": command_coffee,
    "!!/help": command_help,
    "!!/info": command_help,
    "!!/lick": command_lick,
    "!!/location": command_location,
    "!!/master": command_master,
    "!!/notify": command_notify,
    "!!/pull": command_pull,
    "!!/reboot": command_reboot,
    "!!/reportuser": command_allspam,
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
