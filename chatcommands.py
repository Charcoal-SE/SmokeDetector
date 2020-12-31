# coding=utf-8
# noinspection PyUnresolvedReferences
from chatcommunicate import add_room, block_room, CmdException, command, get_report_data, is_privileged, message, \
    tell_rooms, tell_rooms_with, get_message
# noinspection PyUnresolvedReferences
from globalvars import GlobalVars
import findspam
# noinspection PyUnresolvedReferences
from datetime import datetime
from apigetpost import api_get_post, PostData
import datahandling
from datahandling import *
from metasmoke import Metasmoke
from blacklists import load_blacklists, Blacklist
from parsing import *
from spamhandling import check_if_spam, handle_spam
from gitmanager import GitManager
import threading
import random
import requests
import sys
import os
import time
import collections
import subprocess
from html import unescape
from ast import literal_eval
# noinspection PyCompatibility
import regex
from helpers import exit_mode, only_blacklists_changed, only_modules_changed, log, expand_shorthand_link, \
    reload_modules, chunk_list
from classes import Post
from classes.feedback import *
from classes.dnsresolver import dns_resolve
from tasks import Tasks


# TODO: Do we need uid == -2 check?  Turn into "is_user_valid" check
#
#
# System command functions below here

# This "null" command is just bypass for the "unrecognized command" message,
# so that pingbot can respond instead.
@command(aliases=['ping-help', 'groups'])
def null():
    return None


# --- Blacklist Functions --- #
# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(str, whole_msg=True, privileged=True)
def addblu(msg, user):
    """
    Adds a user to site blacklist
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
    raise CmdException("The `!!/blacklist` command has been deprecated. "
                       "Please use `!!/blacklist-website`, `!!/blacklist-username`, "
                       "`!!/blacklist-keyword`, or perhaps `!!/watch-keyword`. "
                       "Remember to escape dots in URLs using \\.")


def minimally_validate_content_source(msg):
    """
    Raises a CmdException if the msg.content and msg.content_source don't match to the first space (i.e. same command).
    """
    # If the chat message has been edited or deleted, then content_source can be invalid, or
    # even a completely different command. Checking that it's for the same command covers the deleted
    # message case and that we don't use arguments intended for a different command. This is, however,
    # not a full re-validation. It just covers the most common case, and the definite problem of using
    # the arguments intended for one command with another one.
    # For more information, see the discussion starting with:
    # https://chat.stackexchange.com/transcript/11540?m=54465107#54465107
    if msg.content.split(" ")[0] != msg.content_source.split(" ")[0]:
        raise CmdException("There was a problem with this command. Was the chat message edited or deleted?")


def get_pattern_from_content_source(msg):
    """
    Returns a string containing the raw chat message content, except for the !!/command .
    :return: A string
    """
    try:
        msg_parts = msg.content_source.split(" ", 1)
        if msg_parts[0] == "sdc":
            return msg_parts[1].split(" ", 1)[1]
        else:
            return msg_parts[1]
    except IndexError:
        # If there's nothing after the space, then raise an error. The chat message may have been edited or deleted,
        # but the deleted case is normally handled in minimally_validate_content_source(), which should be called first.
        # For more information, see the discussion starting with:
        # https://chat.stackexchange.com/transcript/11540?m=54465107#54465107
        raise CmdException("An invalid pattern was provided, please check your command. Was the command edited?")


def check_blacklist(string_to_test, is_username, is_watchlist, is_phone):
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

    question_reasons, _ = findspam.FindSpam.test_post(question)
    answer_reasons, _ = findspam.FindSpam.test_post(answer)

    # Filter out duplicates
    reasons = list(set(question_reasons) | set(answer_reasons))

    # Filter out watchlist results
    filter_out = ["potentially bad ns", "potentially bad asn", "potentially problematic",
                  "potentially bad ip"]
    if not is_watchlist:
        filter_out.append("potentially bad keyword")
    # Ignore "Mostly non-latin body/answer" for phone number watches
    if is_phone:
        filter_out.extend(["mostly non-latin", "phone number detected", "messaging number detected"])

    # Filter out some reasons which commonly find the things added to the watch/blacklists
    # If these are detected, then the user should almost always -force. Showing them gets people too used
    # to just automatically using -force. Maybe a better UX strategy would be to have other reasons shown in bold.
    filter_out.extend(["pattern-matching email", "pattern-matching website", "bad keyword with email",
                       "bad ns for domain", "bad ip for hostname"])
    if filter_out:
        reasons = [reason for reason in reasons if all([x not in reason.lower() for x in filter_out])]

    return reasons


def format_blacklist_reasons(reasons):
    # Capitalize
    reasons = [reason.capitalize() for reason in reasons]

    # Join
    if len(reasons) < 3:
        reason_string = " and ".join(reasons)
    else:
        reason_string = ", and ".join([", ".join(reasons[:-1]), reasons[-1]])

    return reason_string


def sub_to_unchanged(reg_exp, replace, text, max_passes=10, count=0, flags=0):
    """
    Applies a regex substitution as many times as is needed to no longer make a change.
    :param regex:
    :param replace:
    :param text:
    :param max_passes:
    :param count:
    :param flags:
    :return: A string
    """
    prev_text = ""
    max_passes = max_passes + 1 if max_passes else max_passes
    while (text and text != prev_text and max_passes != 1):
        prev_text = text
        text = regex.sub(reg_exp, replace, text, count=count, flags=flags)
        max_passes -= 1
    return text


def get_test_text_from_regex(pattern):
    """
    Converts regex text supplied in a command to text which can be tested for double-dipping
    :param A string:
    :return: A string
    """
    # Handle a specific common pattern that's now matched by a watch for obfuscated gmail.com.
    pattern = pattern.replace(r"(?:[\W_]*+(?:at[\W_]*+)?gmail(?:[\W_]*+(?:dot[\W_]*+)?com)?)?", "@gmail.com")
    pattern = regex.sub(r"(?<!\\)\(\?\#[^\)]*\)", "", pattern)  # Remove comments: comments can have no nested ()
    pattern = regex.sub(r"(?<!\\)\[\\W_\][*?+]*", "-", pattern)  # Replace typical sets
    pattern = regex.sub(r"(?<!\\)\[\\da-f\]\{4,\}+?", "0123", pattern)  # Replace typical sets
    pattern = regex.sub(r"(?<!\\)\[\\da-f\][*?+]*", "0", pattern)  # Replace typical sets
    pattern = regex.sub(r"(?<!\\)\[\^a-z0-9-\][*?+]*", "_", pattern)  # Replace typical sets
    # Replace common named sets
    pattern = pattern.replace(r"\W", "-").replace(r"\w", "a").replace(r"\.", ".").replace(r"\d", "8")
    pattern = pattern.replace(r"\s", " ").replace(r"\S", "b").replace(r"\n", "\n").replace(r"\r", "\r")
    pattern = regex.sub(r"(?<!\\)\$", "", pattern)  # Remove end assertion
    pattern = regex.sub(r"(?<![\\\[])\^", "", pattern)  # Remove start assertion
    pattern = regex.sub(r"(?<!\\)\\[Bb]", "", pattern)  # Remove wordbreak assertion
    pattern = regex.sub(r"(?<!\\)\[(?!\^|\\)(.)(?:[^\]]|(?<=\\)])*\]", r"\1", pattern)  # Replace positive sets
    # Remove optional groups (still want to test this text)
    # pattern = sub_to_unchanged(r"\((?:\?:|(?!\?))(?:[^\(\)]|(?<=\\)[()])*\)(?:[*?][+?]?|\{0?,\d+\}[+?]?)",
    #                            "", pattern)
    # Remove optional characters
    pattern = regex.sub(r"(?:\\.|(?<!\\)[^+*}()[\]])(?:[*?][+?]?|\{0?,\d+\}[+?]?)", "", pattern)
    # Remove lookarounds.
    pattern = sub_to_unchanged(r"\(\?<?[!=](?:[^\(\)]|(?<=\\)[()])*\)", "", pattern)
    # Remove () and (?:) from non-optional groupings
    pattern = sub_to_unchanged(r"\((?:\?:|(?!\?))((?:[^\(\)]|(?<=\\)[()])*)\)(?![*?][+?]?|\{0?,\d+\}[+?]?)",
                               r"\1", pattern)
    # Remove optional groups (still want to test this text)
    # pattern = sub_to_unchanged(r"\((?:\?:|(?!\?))(?:[^\(\)]|(?<=\\)[()])*\)(?:[*?][+?]?|\{0?,\d+\}[+?]?)",
    #                            "", pattern)
    # drop flags: https://regex101.com/r/smAiks/1/
    pattern = sub_to_unchanged(r"(?<!\\)\(\?[a-zA-Z-]+(?::((?:[^\(\)]|(?<=\\)[()])*))?\)", r"\1", pattern)
    pattern = regex.sub(r"(?<!\\)(?:(?<!(?<!\\)\()[+*?][+?]?|\{\d*(?:,\d*)?\}[+?]?)", "", pattern)  # Common quantifiers
    # Remove () and (?:) from groupings
    pattern = sub_to_unchanged(r"\((?:\?:|(?!\?))((?:[^\(\)]|(?<=\\)[()])*)\)", r"\1", pattern)
    # Remove lookarounds (again).
    pattern = sub_to_unchanged(r"\(\?<?[!=](?:[^\(\)]|(?<=\\)[()])*\)", "", pattern)
    return pattern


def do_blacklist(blacklist_type, msg, force=False):
    """
    Adds a string to the website blacklist and commits/pushes to GitHub
    :param raw_pattern:
    :param blacklist_type:
    :param msg:
    :param force:
    :return: A string
    """

    minimally_validate_content_source(msg)
    chat_user_profile_link = "https://chat.{host}/users/{id}".format(host=msg._client.host,
                                                                     id=msg.owner.id)
    append_force_to_do = "; append `-force` if you really want to do that."

    pattern = get_pattern_from_content_source(msg)

    has_u202d = ""
    if '\u202d' in pattern:
        has_u202d = (
            "The pattern contains an invisible U+202D whitespace character;"
            " - in most cases, you don't want that")

    has_unescaped_dot = ""
    if "number" not in blacklist_type:
        # Test for . without \., but not in comments.
        test_for_unescaped_dot = regex.sub(r"(?<!\\)\(\?\#[^\)]*\)", "", pattern)  # remove comments
        # Remove character sets, where . doesn't need to be escaped.
        test_for_unescaped_dot = regex.sub(r"(?<!\\)\[(?:[^\]]|(?<=\\)\])*\]", "", test_for_unescaped_dot)
        if regex.search(r"(?<!\\)\.", test_for_unescaped_dot):
            has_unescaped_dot = 'The regex contains an unescaped "`.`"; in most cases, it should be "`\\.`"'

        try:
            r = regex.compile(pattern, city=findspam.city_list, ignore_unused=True)
        except regex._regex_core.error:
            raise CmdException("An invalid pattern was provided, please check your command.")
        if r.search(GlobalVars.valid_content) is not None:
            raise CmdException("That pattern is probably too broad, refusing to commit.")

    if not force:
        if "number" in blacklist_type or \
                regex.match(r'(?:\[a-z_]\*)?(?:\(\?:)?\d+(?:[][\\W_*()?:]+\d+)+(?:\[a-z_]\*)?$', pattern):
            is_phone = True
        else:
            is_phone = False

        is_watchlist = bool("watch" in blacklist_type)

        concretized_pattern = get_test_text_from_regex(pattern)

        for username in False, True:
            reasons = check_blacklist(
                concretized_pattern, is_username=username, is_watchlist=is_watchlist, is_phone=is_phone)

            if reasons:
                has_u202d = "; in addition, " + has_u202d.lower() if has_u202d else ""
                has_unescaped_dot = "; in addition, " + has_unescaped_dot.lower() if has_unescaped_dot else ""
                raise CmdException(
                    "That pattern looks like it's already caught by " +
                    format_blacklist_reasons(reasons) + has_unescaped_dot + has_u202d + append_force_to_do)

        if has_u202d:
            raise CmdException(has_u202d + has_unescaped_dot + append_force_to_do)

        if has_unescaped_dot:
            raise CmdException(has_unescaped_dot + append_force_to_do)

    metasmoke_down = False

    try:
        code_permissions = is_code_privileged(msg._client.host, msg.owner.id)
    except (requests.exceptions.ConnectionError, ValueError, TypeError):
        code_permissions = False  # Because we need the system to assume that we don't have blacklister privs.
        metasmoke_down = True

    _status, result = GitManager.add_to_blacklist(
        blacklist=blacklist_type,
        item_to_blacklist=pattern,
        username=msg.owner.name,
        chat_profile_link=chat_user_profile_link,
        code_permissions=code_permissions,
        metasmoke_down=metasmoke_down
    )

    if not _status:
        raise CmdException(result)

    if code_permissions and only_blacklists_changed(GitManager.get_local_diff()):
        try:
            if not GlobalVars.on_branch:
                # Restart if HEAD detached
                log('warning', "Pulling local with HEAD detached, checkout deploy", f=True)
                exit_mode("checkout_deploy")
            GitManager.pull_local()
            GlobalVars.reload()
            findspam.FindSpam.reload_blacklists()
            tell_rooms_with('debug', GlobalVars.s_norestart_blacklists)
            time.sleep(2)
            return None
        except Exception:
            pass
    return result


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, give_name=True, aliases=["blacklist-keyword",
                                                                        "blacklist-website",
                                                                        "blacklist-username",
                                                                        "blacklist-number",
                                                                        "blacklist-keyword-force",
                                                                        "blacklist-website-force",
                                                                        "blacklist-username-force",
                                                                        "blacklist-number-force"])
def blacklist_keyword(msg, pattern, alias_used="blacklist-keyword"):
    """
    Adds a pattern to the blacklist and commits/pushes to GitHub
    :param msg:
    :param pattern:
    :return: A string
    """

    parts = alias_used.split("-")
    return do_blacklist(parts[1], msg, force=len(parts) > 2)


# noinspection PyIncorrectDocstring
@command(str, whole_msg=True, privileged=True, give_name=True,
         aliases=["watch-keyword", "watch-force", "watch-keyword-force",
                  "watch-number", "watch-number-force"])
def watch(msg, pattern, alias_used="watch"):
    """
    Adds a pattern to the watched keywords list and commits/pushes to GitHub
    :param msg:
    :param pattern:
    :return: A string
    """

    return do_blacklist("watch_number" if "number" in alias_used else "watch_keyword",
                        msg, force=alias_used.split("-")[-1] == "force")


@command(str, whole_msg=True, privileged=True, give_name=True, aliases=["unwatch"])
def unblacklist(msg, item, alias_used="unwatch"):
    """
    Removes a pattern from watchlist/blacklist and commits/pushes to GitHub
    :param msg:
    :param pattern:
    :return: A string
    """
    if alias_used == "unwatch":
        blacklist_type = "watch"
    elif alias_used == "unblacklist":
        blacklist_type = "blacklist"
    else:
        raise CmdException("Invalid blacklist type.")

    minimally_validate_content_source(msg)

    metasmoke_down = False
    try:
        code_privs = is_code_privileged(msg._client.host, msg.owner.id)
    except (requests.exceptions.ConnectionError, ValueError):
        code_privs = False
        metasmoke_down = True

    pattern = get_pattern_from_content_source(msg)
    _status, result = GitManager.remove_from_blacklist(
        rebuild_str(pattern), msg.owner.name, blacklist_type,
        code_privileged=code_privs, metasmoke_down=metasmoke_down)

    if not _status:
        raise CmdException(result)

    if only_blacklists_changed(GitManager.get_local_diff()):
        try:
            if not GlobalVars.on_branch:
                # Restart if HEAD detached
                log('warning', "Pulling local with HEAD detached, checkout deploy", f=True)
                exit_mode("checkout_deploy")
            GitManager.pull_local()
            GlobalVars.reload()
            findspam.FindSpam.reload_blacklists()
            tell_rooms_with('debug', GlobalVars.s_norestart_blacklists)
            time.sleep(2)
            return None
        except Exception:
            pass
    return result


@command(int, privileged=True, whole_msg=True, aliases=["accept"])
def approve(msg, pr_id):
    code_permissions = is_code_privileged(msg._client.host, msg.owner.id)
    if not code_permissions:
        raise CmdException("You need blacklist manager privileges to approve pull requests")

    # Forward this, because checks are better placed in gitmanager.py
    try:
        message_url = "https://chat.{}/transcript/{}?m={}".format(msg._client.host, msg.room.id, msg.id)
        chat_user_profile_link = "https://chat.{}/users/{}".format(
            msg._client.host, msg.owner.id)
        comment = "[Approved]({}) by [{}]({}) in {}\n\n![Approved with SmokeyApprove]({})".format(
            message_url, msg.owner.name, chat_user_profile_link, msg.room.name,
            # The image of (blacklisters|approved) from PullApprove
            "https://camo.githubusercontent.com/7d7689a88a6788541a0a87c6605c4fdc2475569f/68747470733a2f2f696d672e"
            "736869656c64732e696f2f62616467652f626c61636b6c6973746572732d617070726f7665642d627269676874677265656e")
        message = GitManager.merge_pull_request(pr_id, comment)
        if only_blacklists_changed(GitManager.get_local_diff()):
            try:
                if not GlobalVars.on_branch:
                    # Restart if HEAD detached
                    log('warning', "Pulling local with HEAD detached, checkout deploy", f=True)
                    exit_mode("checkout_deploy")
                GitManager.pull_local()
                GlobalVars.reload()
                findspam.FindSpam.reload_blacklists()
                tell_rooms_with('debug', GlobalVars.s_norestart_blacklists)
                time.sleep(2)
                return None
            except Exception:
                pass
        return message
    except Exception as e:
        raise CmdException(str(e))


@command(str, privileged=True, whole_msg=True, give_name=True, aliases=["close", "reject-force", "close-force"])
def reject(msg, args, alias_used="reject"):
    argsraw = args.split(' "', 1)
    try:
        pr_id = int(argsraw[0].split(' ')[0])
    except ValueError:
        reason = ''
        pr_id = int(args.split(' ')[2])
    try:
        # Custom handle trailing quotation marks at the end of the custom reason, which could happen.
        if argsraw[1][-1] == '"':
            reason = argsraw[1][:-1]
        else:
            reason = argsraw[1]
    except IndexError:
        reason = ''
    force = alias_used.split("-")[-1] == "force"
    code_permissions = is_code_privileged(msg._client.host, msg.owner.id)
    if not code_permissions:
        raise CmdException("You need blacklist manager privileges to reject pull requests")
    if len(reason) < 20 and not force:
        raise CmdException("Please provide an adequate reason for rejection (at least 20 characters long) so the user"
                           " can learn from their mistakes. Use `-force` to force the reject")
    rejected_image = "https://camo.githubusercontent.com/" \
                     "77d8d14b9016e415d36453f27ccbe06d47ef5ae2/68747470733a" \
                     "2f2f7261737465722e736869656c64732e696f2f62616467652f626c6" \
                     "1636b6c6973746572732d72656a65637465642d7265642e706e67"
    message_url = "https://chat.{}/transcript/{}?m={}".format(msg._client.host, msg.room.id, msg.id)
    chat_user_profile_link = "https://chat.{}/users/{}".format(msg._client.host, msg.owner.id)
    rejected_by_text = "[Rejected]({}) by [{}]({}) in {}.".format(message_url, msg.owner.name,
                                                                  chat_user_profile_link, msg.room.name)
    reject_reason_text = " No rejection reason was provided.\n\n"
    if reason:
        reject_reason_text = " Reason: '{}'".format(reason)
    reject_reason_image_text = "\n\n![Rejected with SmokeyReject]({})".format(rejected_image)
    comment = rejected_by_text + reject_reason_text + reject_reason_image_text
    try:
        message = GitManager.reject_pull_request(pr_id, comment)
        return message
    except Exception as e:
        raise CmdException(str(e))


@command(privileged=True, aliases=["remote-diff"])
def remotediff():
    will_require_full_restart = "SmokeDetector will require a full restart to pull changes: " \
                                "{}".format(str(not only_blacklists_changed(GitManager.get_remote_diff())))

    return "{}\n\n{}".format(GitManager.get_remote_diff(), will_require_full_restart)


# --- Joke Commands --- #
@command(whole_msg=True)
def blame(msg):
    unlucky_victim = msg._client.get_user(random.choice(msg.room.get_current_user_ids()))

    return "It's [{}](https://chat.{}/users/{})'s fault.".format(
        unlucky_victim.name, msg._client.host, unlucky_victim.id)


@command(str, whole_msg=True, aliases=["blame\u180E"])
def blame2(msg, x):
    base = {"\u180E": 0, "\u200B": 1, "\u200C": 2, "\u200D": 3, "\u2060": 4, "\u2063": 5, "\uFEFF": 6}
    try:
        user = sum([(len(base)**i) * base[char] for i, char in enumerate(reversed(x))])

        unlucky_victim = msg._client.get_user(user)
        return "It's [{}](https://chat.{}/users/{})'s fault.".format(
            unlucky_victim.name, msg._client.host, unlucky_victim.id)

    except (KeyError, requests.exceptions.HTTPError):
        unlucky_victim = msg.owner
        return "It's [{}](https://chat.{}/users/{})'s fault.".format(
            unlucky_victim.name, msg._client.host, unlucky_victim.id)


# noinspection PyIncorrectDocstring
@command()
def brownie():
    """
    Returns a string equal to "Brown!" (This is a joke command)
    :return: A string
    """
    return "Brown!"


COFFEES = ['Espresso', 'Macchiato', 'Ristretto', 'Americano', 'Latte', 'Cappuccino', 'Mocha', 'Affogato', 'jQuery']


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


"""
@command(aliases=["zomg_hats"])
def hats():
    wb_start = datetime(2018, 12, 12, 0, 0, 0)
    wb_end = datetime(2019, 1, 2, 0, 0, 0)
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
"""


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
ALIVE_MSG = [
    'Yup', 'You doubt me?', 'Of course', '... did I miss something?', 'plz send teh coffee',
    'Watching this endless list of new questions *never* gets boring', 'Kinda sorta',
    'You should totally drop that and use jQuery', r'¯\\_(ツ)\_/¯', '... good question',
]


# noinspection PyIncorrectDocstring
@command(aliases=["live"])
def alive():
    """
    Returns a string indicating the process is still active
    :return: A string
    """
    return random.choice(ALIVE_MSG)


# noinspection PyIncorrectDocstring
@command(int, privileged=True, arity=(0, 1), aliases=["errlogs", "errlog", "errorlog"])
def errorlogs(count):
    """
    Shows the most recent lines in the error logs
    :param count:
    :return: A string
    """
    return fetch_lines_from_error_log(count or 2)


@command(whole_msg=True, aliases=["ms-status", "ms-down", "ms-up", "ms-down-force", "ms-up-force"], give_name=True)
def metasmoke(msg, alias_used):
    if alias_used in {"metasmoke", "ms-status"}:
        status_text = [
            "metasmoke is up. Current failure count: {} ({id})".format(GlobalVars.MSStatus.get_failure_count(),
                                                                       id=GlobalVars.location),
            "metasmoke is down. Current failure count: {} ({id})".format(GlobalVars.MSStatus.get_failure_count(),
                                                                         id=GlobalVars.location),
        ]
        if GlobalVars.MSStatus.is_up():
            # True = 1 and False = 0 is a legacy feature
            # Better not to use them
            return status_text[0]
        else:
            return status_text[1]

    # The next aliases/functionalities require privilege
    if not is_privileged(msg.owner, msg.room):
        raise CmdException(GlobalVars.not_privileged_warning)

    to_up = "up" in alias_used
    forced = "force" in alias_used
    Metasmoke.AutoSwitch.reset_switch()  # If manually switched, reset the internal counter
    Metasmoke.AutoSwitch.enable_autoswitch(not forced)
    if to_up:
        Metasmoke.set_ms_up()
    else:
        Metasmoke.set_ms_down()
    return "Metasmoke status is now: **{}**;".format("up" if to_up else "down") +\
           " Auto status switch: **{}abled**.".format("dis" if forced else "en")


@command(aliases=["scan-stat", "statistics"])
def stat():
    """ Return post scan statistics. """
    posts_scanned, scan_time, posts_per_second = GlobalVars.PostScanStat.get_stat()
    stat_msg = "Posts scanned: {}; Scan time: {}".format(posts_scanned, scan_time)

    rate_msg = ""
    if posts_per_second:
        rate_msg = "; Posts scanned per second: {}".format(posts_per_second)

    return stat_msg + rate_msg


@command(aliases=["counter", "internal-counter", "ping-failure"])
def ping_failure_counter():
    """ Return ping failure counter value of Metasmoke: AutoSwitch. """
    counter = Metasmoke.AutoSwitch.get_ping_failure()
    return "Current ping failure counter value: {}".format(counter)


# noinspection PyIncorrectDocstring
@command(aliases=["commands", "help"])
def info():
    """
    Returns the help text
    :return: A string
    """
    return "I'm " + GlobalVars.chatmessage_prefix +\
           ", a bot that detects spam and offensive posts on the network and"\
           " posts alerts to chat."\
           " [A command list is available here](https://git.io/SD-Commands)."


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


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(privileged=True)
def master():
    """
    Forces a system exit with exit code = 8
    :return: None
    """
    exit_mode("checkout_deploy")


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(privileged=True, aliases=["pull-force"])
def pull(alias_used='pull'):
    """
    Pull an update from GitHub
    :return: String on failure, None on success
    """
    remote_diff = GitManager.get_remote_diff()
    if (not alias_used == "pull-force") and only_blacklists_changed(remote_diff):
        GitManager.pull_remote()
        findspam.FindSpam.reload_blacklists()
        GlobalVars.reload()
        tell_rooms_with('debug', GlobalVars.s_norestart_blacklists)
        return

    request = requests.get('https://api.github.com/repos/{}/git/refs/heads/deploy'.format(
        GlobalVars.bot_repo_slug))
    latest_sha = request.json()["object"]["sha"]
    request = requests.get(
        'https://api.github.com/repos/{}/commits/{}/statuses'.format(
            GlobalVars.bot_repo_slug, latest_sha))
    states = []
    for ci_status in request.json():
        state = ci_status["state"]
        states.append(state)
    if "success" in states:
        if only_modules_changed(remote_diff):
            GitManager.pull_remote()
            reload_modules()
            GlobalVars.reload()
            tell_rooms_with('debug', GlobalVars.s_norestart_findspam)
            return
        else:
            exit_mode('pull_update', code=3)
    elif "error" in states or "failure" in states:
        raise CmdException("CI build failed! :( Please check your commit.")
    elif "pending" in states or not states:
        raise CmdException("CI build is still pending, wait until the build has finished and then pull again.")


@command(whole_msg=True, privileged=True, give_name=True, aliases=['pull-sync', 'pull-sync-force'])
def sync_remote(msg, alias_used='pull-sync'):
    """
    Force a branch sync from origin/master with [git branch -M]
    :param msg:
    :return: A string containing a response message
    """
    if not is_code_privileged(msg._client.host, msg.owner.id):
        raise CmdException("You don't have blacklist manager privileges to run this command.")
    if 'force' not in alias_used:
        raise CmdException("This command is deprecated, append `-force` if you really need to do that.")

    return GitManager.sync_remote()[1]


@command(whole_msg=True, privileged=True, give_name=True, aliases=['pull-sync-hard',
                                                                   'pull-sync-hard-force',
                                                                   'pull-sync-hard-reboot',
                                                                   'pull-sync-hard-reboot-force'])
def sync_remote_hard(msg, alias_used='pull-sync-hard'):
    """
    Force a branch sync from origin/master and origin/deploy
    :param msg:
    :return: A string containing a response message or None
    """
    if not is_code_privileged(msg._client.host, msg.owner.id):
        raise CmdException("You don't have blacklist manager privileges, which are required to run this command.")

    git_response = GitManager.sync_remote_hard()[1]
    # Not enough information is passed to commands to send an actual reply. Thus, the reboot
    # is scheduled to happen later and we return the results of the GitManager function, which
    # is the text that's sent as a reply to the user.
    if 'reboot' in alias_used:
        Tasks.later(reboot, msg, original_msg=msg, alias_used="reboot", after=5)
        return git_response + " Automatically rebooting in a few seconds."

    return git_response + " You'll probably want to !!/reboot now."


@command(privileged=True, give_name=True, aliases=[
    "gitstatus", "git-status", "git-help", "git-merge-abort", "git-reset"
])
def git(alias_used="git"):
    if alias_used == "git":
        raise CmdException("Bad alias. Try another command")
    if alias_used == "git-help":
        return "Available commands: git-help, git-status, git-merge-abort, git-reset"

    alias_used = alias_used.replace("-", "")
    if alias_used == "gitstatus":
        return GitManager.current_git_status()
    elif alias_used == "gitmergeabort":
        return GitManager.merge_abort()
    elif alias_used == "gitreset":
        return GitManager.reset_head()


# noinspection PyIncorrectDocstring,PyProtectedMember
@command(whole_msg=True, privileged=True, give_name=True, aliases=["restart", "reload"])
def reboot(msg, alias_used="reboot"):
    """
    Forces a system exit with exit code = 5
    :param msg:
    :return: None
    """
    if alias_used in {"reboot", "restart"}:
        tell_rooms("{}: Goodbye, cruel world".format(GlobalVars.location),
                   ("debug", (msg._client.host, msg.room.id)), ())
        time.sleep(3)
        exit_mode("reboot")
    elif alias_used in {"reload"}:
        reload_modules()
        tell_rooms_with('debug', GlobalVars.s_norestart_findspam)
        time.sleep(3)
    else:
        raise RuntimeError("Invalid alias!")


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
@command(whole_msg=True, aliases=["amicodeprivileged", "amiblacklisterprivileged", "amiblacklistmanagerprivileged"])
def amiblacklistprivileged(msg):
    """
    Tells user whether or not they have blacklister privileges
    :param msg:
    :return: A string
    """
    update_code_privileged_users_list()
    if is_code_privileged(msg._client.host, msg.owner.id):
        return "\u2713 You are a blacklist manager privileged user."

    return "\u2573 No, you are not a blacklist manager privileged user."


# noinspection PyIncorrectDocstring
@command()
def apiquota():
    """
    Report how many API hits remain for the day
    :return: A string
    """
    GlobalVars.apiquota_rw_lock.acquire()
    current_apiquota = GlobalVars.apiquota
    GlobalVars.apiquota_rw_lock.release()

    return "The current API quota remaining is {}.".format(current_apiquota)


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
        tell_rooms("{}: Goodbye, cruel world".format(GlobalVars.location),
                   ((msg._client.host, msg.room.id)), ())

        time.sleep(3)
        exit_mode("shutdown", code=6)


def td_format(td_object):
    # source: https://stackoverflow.com/a/13756038/5244995
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
    diff = now - GlobalVars.startup_utc_date

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
        exit_mode("standby", code=7)


# noinspection PyIncorrectDocstring
@command(str, aliases=["test-q", "test-question", "test-a", "test-answer", "test-u", "test-user",
                       "test-t", "test-title", "test-j", "test-json"],
         give_name=True)
def test(content, alias_used="test"):
    """
    Test content provided in chat to determine if it'd be automatically reported
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

    if alias_used in ["test-q", "test-question"]:
        kind = "a question"
        fakepost = Post(api_response={'title': 'Valid title', 'body': content,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})
    elif alias_used in ["test-a", "test-answer"]:
        kind = "an answer"
        fakepost = Post(api_response={'title': 'Valid title', 'body': content,
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': True, 'score': 0})
    elif alias_used in ["test-u", "test-user"]:
        kind = "a username"
        fakepost = Post(api_response={'title': 'Valid title', 'body': "Valid question body",
                                      'owner': {'display_name': content, 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})
    elif alias_used in ["test-t", "test-title"]:
        kind = "a title"
        fakepost = Post(api_response={'title': content, 'body': "Valid question body",
                                      'owner': {'display_name': "Valid username", 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})
    elif alias_used in ["test-j", "test-json"]:
        # Only load legit json object
        try:
            json_obj = json.loads(content)
        except ValueError as e:
            raise CmdException("Error: {}".format(e))
        if not isinstance(json_obj, dict):
            raise CmdException("Only accepts a json object as input")
        # List of valid keys and their corresponding classes
        valid_keys = [
            ('title', str), ('body', str), ('username', str), ('type', str),
            ('reputation', int), ('score', int)
        ]
        right_types = list(filter(lambda p: p[0] in json_obj and isinstance(json_obj[p[0]], p[1]), valid_keys))
        wrong_types = list(filter(lambda p: p[0] in json_obj and not isinstance(json_obj[p[0]], p[1]), valid_keys))
        # Alert if valid key is of wrong class
        if len(wrong_types) > 0:
            raise CmdException("Invalid type: {}".format(", ".join(
                ["{} should be {}".format(x, y.__name__) for (x, y) in wrong_types])))
        # Alert if none of the valid keys are used
        elif len(right_types) == 0:
            raise CmdException("At least one of the following keys needed: {}".format(", ".join(
                ["{} ({})".format(x, y.__name__) for (x, y) in valid_keys])))
        # Craft a fake response
        fake_response = {
            'title': json_obj['title'] if 'title' in json_obj else 'Valid post title',
            'body': json_obj['body'] if 'body' in json_obj else 'Valid post body',
            'owner': {
                'display_name': json_obj['username'] if 'username' in json_obj else 'Valid username',
                'reputation': json_obj['reputation'] if 'reputation' in json_obj else 0,
                'link': ''
            },
            'IsAnswer': 'type' in json_obj and not json_obj['type'] == "question",
            'site': site,
            'score': json_obj['score'] if 'score' in json_obj else 0
        }
        # Handle that pluralization bug
        kind = "an answer" if fake_response['IsAnswer'] else "a question"
        fakepost = Post(api_response=fake_response)
    else:
        kind = "a post, title or username"
        fakepost = Post(api_response={'title': content, 'body': content,
                                      'owner': {'display_name': content, 'reputation': 1, 'link': ''},
                                      'site': site, 'IsAnswer': False, 'score': 0})

    reasons, why_response = findspam.FindSpam.test_post(fakepost)

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


def bisect_regex(s, regexes, bookend=True, timeout=None):
    regex_to_format = r"(?is)(?:^|\b|(?w:\b))(?:{})(?:$|\b|(?w:\b))" if bookend else r"(?i)(?:{})"
    formatted_regex = regex_to_format.format("|".join([r for r, i in regexes]))
    start_time = time.time()
    try:
        compiled = regex.compile(formatted_regex, city=findspam.city_list, ignore_unused=True)
        match = compiled.search(s, timeout=timeout)
    except Exception:
        # Log wich regex caused the error:
        seconds = time.time() - start_time
        log('error', "bisect_regex: in {} seconds, got an error with the regex: {}".format(seconds, formatted_regex))
        raise

    seconds = time.time() - start_time
    if seconds > 0.1:
        # For debugging, if a regex is taking a long time, we want to know about it. This is about 5 times
        # longer than the high end of what one group of 64 regexes normally takes in our tests.
        log('debug', "bisect_regex: took {} seconds for the regex: {}".format(seconds, formatted_regex))
    if not match:
        return []
    if len(regexes) <= 1:  # atom element found
        return regexes

    mid_len = (len(regexes) - 1).bit_length() - 1
    mid = 2 ** mid_len
    return bisect_regex(s, regexes[:mid], bookend=bookend, timeout=timeout) + \
        bisect_regex(s, regexes[mid:], bookend=bookend, timeout=timeout)


def bisect_regex_one_by_one(test_text, regexes, bookend=True, timeout=None):
    regex_to_format = r"(?is)(?:^|\b|(?w:\b))(?:{})(?:$|\b|(?w:\b))" if bookend else r"(?i)(?:{})"
    results = []
    for expresion in regexes:
        compiled = regex.compile(regex_to_format.format(expresion[0]), city=findspam.city_list, ignore_unused=True)
        match = compiled.search(test_text, timeout=timeout)
        if match:
            results.append(expresion)
    return results


def bisect_regex_in_n_size_chunks(size, test_text, regexes, bookend=True, timeout=None):
    regex_chunks = chunk_list(regexes, size)
    results = []
    for chunk in regex_chunks:
        matches = bisect_regex(test_text, chunk, bookend=bookend, timeout=timeout)
        if matches:
            results.extend(matches)
    return results


@command(str, privileged=True, whole_msg=True, aliases=['what'])
def bisect(msg, s):
    bookended_regexes = []
    non_bookended_regexes = []
    regexes = []
    non_bookended_regexes.extend(Blacklist(Blacklist.USERNAMES).each(True))
    non_bookended_regexes.extend(Blacklist(Blacklist.WEBSITES).each(True))
    bookended_regexes.extend(Blacklist(Blacklist.KEYWORDS).each(True))
    bookended_regexes.extend(Blacklist(Blacklist.WATCHED_KEYWORDS).each(True))

    if msg is not None:
        minimally_validate_content_source(msg)

    try:
        s = rebuild_str(get_pattern_from_content_source(msg))
    except AttributeError:
        pass
    # A timeout of 1 second is about 50 times longer than we're currently seeing. It should give
    # us a good indication of when we have a regex that is not behaving as well as we'd like.
    # If there is a regex which needs more than this, feel free to adjust the timeout. However,
    # it would be better to look at how the regex might be rewritten.
    matching = bisect_regex_in_n_size_chunks(64, s, bookended_regexes, bookend=True, timeout=1)
    matching.extend(bisect_regex_in_n_size_chunks(64, s, non_bookended_regexes, bookend=False, timeout=1))

    if not matching:
        return "{!r} is not caught by a blacklist or watchlist item.".format(s)

    print('matching: {}'.format(matching))
    print('len(matching): {}'.format(len(matching)))
    if len(matching) == 1:
        r, (l, f) = matching[0]
        return "Matched by `{0}` on [line {1} of {2}](https://github.com/{3}/blob/{4}/{2}#L{1})".format(
            r, l, f, GlobalVars.bot_repo_slug, GlobalVars.commit.id)
    else:
        return "Matched by the following regexes:\n" + "\n".join(
            "{} on line {} of {}".format(r, l, f) for r, (l, f) in matching)


@command(str, privileged=True, whole_msg=True, aliases=['what-number'])
def bisect_number(msg, s):
    minimally_validate_content_source(msg)
    try:
        number = rebuild_str(get_pattern_from_content_source(msg))
    except AttributeError:
        pass
    normalized = regex.sub(r"\D", "", number)

    # Assume raw number strings don't duplicate
    numbers = dict(Blacklist(Blacklist.NUMBERS).each(True))
    numbers.update(Blacklist(Blacklist.WATCHED_NUMBERS).each(True))
    # But normalized numbers surely duplicate
    normalized_numbers = collections.defaultdict(list)
    for item, info in numbers.items():
        item_norm = regex.sub(r"\D", "", item)
        normalized_numbers[item_norm].append(info)

    normalized_match = normalized_numbers.get(normalized)
    if not normalized_match:
        return "{!r} is not caught by a blacklist or watchlist number.".format(number)
    verbatim_match = numbers.get(number)
    if verbatim_match:
        # A verbatim match is ALWAYS a normalized match as well
        # Something would be seriously wrong if this throws ValueError
        normalized_match.remove(verbatim_match)
        if normalized_match:
            l, f = verbatim_match
            response = "Matched verbatim on line {0} of {1}, and also normalized on".format(l, f)
            for l, f in normalized_match:
                response += "\n- line {0} of {1}".format(l, f)
            return response
        else:
            l, f = verbatim_match
            return "Matched verbatim on [line {0} of {1}](https://github.com/{2}/blob/{3}/{1}#L{0})".format(
                l, f, GlobalVars.bot_repo_slug, GlobalVars.commit.id)
    else:
        if len(normalized_match) == 1:
            l, f = normalized_match[0]
            return "Not matched verbatim, but normalized on " \
                   "[line {0} of {1}](https://github.com/{2}/blob/{3}/{1}#L{0})".format(
                       l, f, GlobalVars.bot_repo_slug, GlobalVars.commit.id)
        response = "Not matched verbatim, but normalized on"
        for l, f in normalized_match:
            response += "\n- line {0} of {1}".format(l, f)
        return response


# noinspection PyIncorrectDocstring
@command()
def threads():
    """
    Returns a description of current threads, for debugging
    :return: A string
    """

    # Note: One may see multiple threads named "message_sender", and they are started by ChatExchange,
    # one for each chat server.
    # The one started by SmokeDetector is named "message sender", without the underscore.
    threads_list = ["{ident}: {name}".format(ident=t.ident, name=t.name) for t in threading.enumerate()]

    return "\n".join(threads_list)


# noinspection PyIncorrectDocstring
@command(aliases=["rev", "ver", "location"])
def version():
    """
    Returns the current version of the application
    :return: A string
    """

    return '{id} [{commit_name}]({repository}/commit/{commit_code})'.format(
        id=GlobalVars.location,
        commit_name=GlobalVars.commit_with_author_escaped,
        commit_code=GlobalVars.commit.id,
        repository=GlobalVars.bot_repository
    )


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
@command(whole_msg=True)
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


RETURN_NAMES = {"admin": ["admin", "admins"], "blacklist_manager": ["blacklist manager", "blacklist managers"]}
VALID_ROLES = {"admin": "admin",
               "code_admin": "blacklist_manager",
               "admins": "admin",
               "codeadmins": "blacklist_manager",
               "blacklist_manager": "blacklist_manager",
               "blacklister": "blacklist_manager",
               "blacklisters": "blacklist_manager"}


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

    ms_route = "/api/v2.0/users/with_role/{}".format(VALID_ROLES[role])
    params = {
        'filter': 'HMMKFJ',
        'key': GlobalVars.metasmoke_key,
        'per_page': 100
    }
    user_response = Metasmoke.get(ms_route, params=params)
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
@command(str, whole_msg=True, privileged=False, give_name=True,
         aliases=["scan", "scan-force", "report-force", "report-direct"])
def report(msg, args, alias_used="report"):
    """
    Report a post (or posts)
    :param msg:
    :return: A string (or None)
    """
    if not is_privileged(msg.owner, msg.room) and alias_used != "scan":
        raise CmdException(GlobalVars.not_privileged_warning)

    crn, wait = can_report_now(msg.owner.id, msg._client.host)
    if not crn:
        raise CmdException("You can execute the !!/{} command again in {} seconds. "
                           "To avoid one user sending lots of reports in a few commands and "
                           "slowing SmokeDetector down due to rate-limiting, you have to "
                           "wait 30 seconds after you've reported multiple posts in "
                           "one go.".format(alias_used, wait))

    alias_used = alias_used or "report"

    argsraw = args.split(' "', 1)
    urls = argsraw[0].split(' ')

    message_url = "https://chat.{0}/transcript/{1}?m={2}".format(msg._client.host, msg.room.id, msg.id)

    # Handle determining whether a custom report reason was provided.
    try:
        # Custom handle trailing quotation marks at the end of the custom reason, which could happen.
        if argsraw[1][-1] == '"':
            custom_reason = argsraw[1][:-1]
        else:
            custom_reason = argsraw[1]
    except IndexError:
        custom_reason = None

    if len(urls) > 5:
        raise CmdException("To avoid SmokeDetector reporting posts too slowly, you can "
                           "{} at most 5 posts at a time. This is to avoid "
                           "SmokeDetector's chat messages getting rate-limited too much, "
                           "which would slow down reports.".format(alias_used))

    # report_posts(urls, reported_by_owner, reported_in, blacklist_by, operation="report", custom_reason=None):
    output = report_posts(urls, msg.owner, msg.room.name, message_url, alias_used, custom_reason)

    if output:
        if 1 < len(urls) > output.count("\n") + 1:
            add_or_update_multiple_reporter(msg.owner.id, msg._client.host, time.time())
        return output


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(str, whole_msg=True, privileged=True, aliases=['reportuser'])
def allspam(msg, url):
    """
    Reports all of a user's posts as spam
    :param msg:
    :param url: A user profile URL
    :return:
    """

    api_key = 'IAkbitmze4B8KpacUfLqkw(('
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
        request_url = "https://api.stackexchange.com/2.2/users/{}/associated".format(user[0])
        params = {
            'filter': '!6Pbp)--cWmv(1',
            'key': api_key
        }
        res = requests.get(request_url, params=params).json()
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
        request_url = "https://api.stackexchange.com/2.2/users/{}/posts".format(u_id)
        params = {
            'filter': '!fsv5ng(IaK_MBkZYCDWuA.U2DqLwdl*YEL_',
            'key': api_key,
            'site': u_site
        }
        res = requests.get(request_url, params=params).json()
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
                req_url = "https://api.stackexchange.com/2.2/answers/{}".format(post['post_id'])
                params = {
                    'filter': '!*Jxb9s5EOrE51WK*',
                    'key': api_key,
                    'site': u_site
                }
                answer_res = requests.get(req_url, params=params).json()
                if "backoff" in answer_res:
                    if GlobalVars.api_backoff_time < time.time() + answer_res["backoff"]:
                        GlobalVars.api_backoff_time = time.time() + answer_res["backoff"]
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


def report_posts(urls, reported_by_owner, reported_in=None, blacklist_by=None, operation="report", custom_reason=None):
    """
    Reports a list of URLs
    :param urls: A list of URLs
    :param reported_by_owner: The chatexchange User record for the user that reported the URLs, or a str.
    :param reported_in: The name of the room in which the URLs were reported, or True if reported by the MS API.
    :param blacklist_by: String of the URL for the transcript of the chat message causing the report.
    :param operation: String of which operation is being performed (e.g. report, scan, report-force, scan-force)
    :param custom_reason: String of the custom reason why the URLs are being reported.
    :return: String: the in-chat repsponse
    """
    # Use reported_by_owner.name (ChatExchange user record) unless reported_by_owner is a
    # str (e.g.  reports from the MS WebSocket).  If reported_by_owner isn't a ChatExchange
    # user record, we can't add the custom_reason as an MS comment later.
    reported_by_name = reported_by_owner if type(reported_by_owner) is str else reported_by_owner.name
    operation = operation or "report"
    is_forced = operation in {"scan-force", "report-force", "report-direct"}
    if operation == "scan-force":
        operation = "scan"
    action_done = "scanned" if operation == "scan" else "reported"
    if reported_in is None:
        reported_from = " by *{}*".format(reported_by_name)
    elif reported_in is True:
        reported_from = " by *{}* from the metasmoke API".format(reported_by_name)
    else:
        reported_from = " by user *{}* in room *{}*".format(reported_by_name, reported_in)

    if custom_reason:
        with_reason = " with reason: *{}*".format(custom_reason)
    else:
        with_reason = ""

    report_info = "Post manually {}{}{}.\n\n".format(action_done, reported_from, with_reason)

    normalized_urls = []
    for url in urls:
        t = url_to_shortlink(url)
        if not t:
            normalized_urls.append("That does not look like a valid post URL.")
        elif t not in normalized_urls:
            normalized_urls.append(t)
        else:
            normalized_urls.append("A duplicate URL was provided.")
    urls = normalized_urls

    users_to_blacklist = []
    output = []

    for index, url in enumerate(urls, start=1):
        if not url.startswith("http://") and not url.startswith("https://"):
            # Return the bad URL directly.
            output.append("Post {}: {}".format(index, url))
            continue

        post_data = api_get_post(rebuild_str(url))

        if post_data is None:
            output.append("Post {}: That does not look like a valid post URL.".format(index))
            continue

        if post_data is False:
            output.append("Post {}: Could not find data for this post in the API. "
                          "It may already have been deleted.".format(index))
            continue

        if has_already_been_posted(post_data.site, post_data.post_id, post_data.title) and not is_false_positive(
                (post_data.post_id, post_data.site)) and not is_forced:
            # Don't re-report if the post wasn't marked as a false positive. If it was marked as a false positive,
            # this re-report might be attempting to correct that/fix a mistake/etc.

            if GlobalVars.metasmoke_key is not None:
                se_link = to_protocol_relative(post_data.post_url)
                ms_link = resolve_ms_link(se_link) or to_metasmoke_link(se_link)
                output.append("Post {}: Already recently reported [ [MS]({}) ]".format(index, ms_link))
                continue
            else:
                output.append("Post {}: Already recently reported".format(index))
                continue

        url = to_protocol_relative(post_data.post_url)
        post = Post(api_response=post_data.as_dict)
        user = get_user_from_url(post_data.owner_url)

        if fetch_post_id_and_site_from_url(url)[2] == "answer":
            parent_data = api_get_post("https://{}/q/{}".format(post.post_site, post_data.question_id))
            post._is_answer = True
            post._parent = Post(api_response=parent_data.as_dict)

        # if operation == "report-direct":
        #     scan_spam, scan_reasons, scan_why = False, [], ""
        # else:
        if True:
            scan_spam, scan_reasons, scan_why = check_if_spam(post)  # Scan it first

        if operation in {"report", "report-force"}:  # Force blacklist user even if !!/report falls back to scan
            if user is not None:
                users_to_blacklist.append((user, blacklist_by, post_data.post_url))

        # scan_spam == False indicates that the post is not spam, but it is also set to False
        # when the post is spam, but has been previously reported. In that case, the scan_reasons
        # is a tuple with what would be the list of reasons as the first entry and what would
        # be the why as the second. This converts that output back into what they would be
        # if the post wasn't previously reported for the cases where we want to process it
        # as such.
        # Expand real scan results from dirty returm value when not "!!/scan"
        # Presence of "scan_why" indicates the post IS spam but ignored
        if (operation != "scan" or is_forced) and (not scan_spam) and scan_why:
            scan_spam = True
            scan_reasons, scan_why = scan_reasons

        # Always handle if reported
        if scan_spam and operation != "report-direct":
            comment = report_info + scan_why.lstrip()
            handle_spam(post=post, reasons=scan_reasons, why=comment)
            if custom_reason and type(reported_by_owner) is not str:
                Tasks.later(Metasmoke.post_auto_comment, custom_reason, reported_by_owner, url=url, after=15)
            continue

        # scan_spam == False
        if operation in {"report", "report-force", "report-direct"}:
            batch = ""
            if len(urls) > 1:
                batch = " (batch report: post {} out of {})".format(index, len(urls))

            if scan_spam:
                why_append = "This post would have also been caught for: " + ", ".join(scan_reasons).capitalize() + \
                    '\n' + scan_why
            else:
                why_append = "This post would not have been caught otherwise."

            comment = report_info + why_append
            handle_spam(post=post,
                        reasons=["Manually reported " + post_data.post_type + batch],
                        why=comment)
            if custom_reason and type(reported_by_owner) is not str:
                Tasks.later(Metasmoke.post_auto_comment, custom_reason, reported_by_owner, url=url, after=15)
            continue

        # scan_spam == False and "scan"
        else:
            if scan_why:
                output.append("Post {}: Looks like spam but not reported: {}".format(index, scan_why.capitalize()))
            else:
                output.append("Post {}: This does not look like spam".format(index))

    for item in users_to_blacklist:
        add_blacklisted_user(*item)

    if len(output):
        return "\n".join(output)
    return None


@command(str, str, privileged=True, whole_msg=True)
def feedback(msg, post_url, feedback):
    post_url = url_to_shortlink(post_url)[6:]
    if not post_url:
        raise CmdException("No such feedback.")

    for feedbacks in (TRUE_FEEDBACKS, FALSE_FEEDBACKS, NAA_FEEDBACKS):
        if feedback in feedbacks:
            feedbacks[feedback].send(post_url, msg)
            return

    raise CmdException("No such feedback.")


@command(privileged=True)
def dump_data():
    try:
        s, metadata = SmokeyTransfer.dump()
        s = "{}, {}, {}\n{}".format(metadata['time'], metadata['location'], metadata['rev'], s)
        tell_rooms_with('dump', s)
    except Exception:
        log_exception(*sys.exc_info())
        raise CmdException("Failed to dump data. Run `!!/errorlogs` for details.")
    return "Data successfully dumped"


@command(int, privileged=True)
def load_data(msg_id):
    msg = get_message(msg_id)
    if msg.owner.id != 120914:  # TODO: implement an is_self() in chatcommunicate, don't use magic numbers
        raise CmdException("Message owner is not SmokeDetector, refusing to load")
    minimally_validate_content_source(msg)
    try:
        SmokeyTransfer.load(msg.content_source)
    except ValueError as e:
        raise CmdException(str(e)) from None
    except Exception:
        log_exception(*sys.exc_info())
        raise CmdException("Failed to load data. Run `!!/errorlogs` for details.")
    return "Data successfully loaded"


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
    except Exception:  # I don't want to dig into ChatExchange
        pass  # couldn't delete message


# noinspection PyIncorrectDocstring,PyUnusedLocal,PyBroadException
@command(message, reply=True, privileged=True, aliases=DELETE_ALIASES)
def delete(msg):
    """
    Delete a post from a chatroom, with an override for Charcoal HQ.
    :param msg:
    :return: None
    """

    if msg.room.id == 11540:
        return "Messages/reports from SmokeDetector in Charcoal HQ are generally kept "\
               "as records. If you really need to delete a message, please use "\
               "`sd delete-force`. See [this note on message deletion]"\
               "(https://charcoal-se.org/smokey/Commands"\
               "#a-note-on-message-deletion) for more details."
    else:
        try:
            msg.delete()
        except Exception:  # I don't want to dig into ChatExchange
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
    except Exception:  # I don't want to dig into ChatExchange
        pass

    if comment:
        Tasks.do(Metasmoke.post_auto_comment, comment, feedback.owner, url=post_url)

    return result if not feedback_type.always_silent else ""


# noinspection PyIncorrectDocstring,PyMissingTypeHints
@command(message, str, reply=True, privileged=True, whole_msg=True, arity=(1, 2), give_name=True, aliases=["ig"])
def ignore(feedback, msg, comment, alias_used="ignore"):
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

    if alias_used == "ig":
        return None
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
    try:
        user = get_user_from_url(owner_url)
    except TypeError as e:
        raise CmdException('Could not get user from URL {0!r}'.format(owner_url))

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
            raise CmdException("I don't have the `why` data for that post (anymore?). "
                               "You should be able to find it on metasmoke.")


# noinspection PyIncorrectDocstring,PyUnusedLocal
@command(message, reply=True)
def autoflagged(msg):
    """
    Determines whether a post was automatically flagged by Metasmoke
    :param msg:
    :return: A string
    """
    # sneaky!
    update_reason_weights()

    post_data = get_report_data(msg)

    if not post_data:
        raise CmdException("That's not a report.")

    is_autoflagged, names = Metasmoke.determine_if_autoflagged(post_data[0])

    if is_autoflagged:
        return "That post was automatically flagged, using flags from: {}.".format(", ".join(names))
    else:
        return "That post was **not** automatically flagged by metasmoke."


# noinspection PyMissingTypeHints
@command(str, privileged=True)
def dig(domain):
    """
    Runs a DNS query using pydns and returns the
    list of A and AAAA records as output.
    :param domain: the domain to get DNS records for
    :return: A comma-separated string of IPs
    """
    results = dns_resolve(domain)
    if results:
        return ", ".join(result for result in results)
    else:
        return "No data found."
