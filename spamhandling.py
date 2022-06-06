# coding=utf-8
import sys
import random
import findspam
import datahandling
import chatcommunicate
from globalvars import GlobalVars
from datetime import datetime, timedelta
import regex
import parsing
import metasmoke
import excepthook
from classes import Post, PostParseError
from helpers import log, escape_format
from parsing import to_metasmoke_link
from tasks import Tasks


# noinspection PyMissingTypeHints
def should_whitelist_prevent_alert(user_url, reasons):
    is_whitelisted = datahandling.is_whitelisted_user(parsing.get_user_from_url(user_url))
    if not is_whitelisted:
        return False
    return not any(r for r in set(reasons) if "username" not in r)


def sum_weight(reasons: list):
    with GlobalVars.reason_weights_lock:
        globalvars_reason_weights = GlobalVars.reason_weights
    if not globalvars_reason_weights:
        datahandling.update_reason_weights()
    now = datetime.utcnow() - timedelta(minutes=15)
    with GlobalVars.reason_weights_lock:
        weights = GlobalVars.reason_weights
        if (not weights.get('updating', False) and now.date() != weights.get('last_updated', 0) and now.hour >= 1):
            weights['updating'] = True
            Tasks.do(datahandling.update_reason_weights)
        s = 0
        for r in reasons:
            try:
                if "(" in r:
                    r = regex.sub(r"\s*\(.*$", "", r)
                s += weights[r.lower()]
            except KeyError:
                pass  # s += 0
    return s


# noinspection PyMissingTypeHints
def check_if_spam(post, dont_ignore_for=None):
    test, why = findspam.FindSpam.test_post(post)
    if datahandling.is_blacklisted_user(parsing.get_user_from_url(post.user_url)):
        test.append("blacklisted user")
        blacklisted_user_data = datahandling.get_blacklisted_user_data(parsing.get_user_from_url(post.user_url))
        if len(blacklisted_user_data) > 1:
            if blacklisted_user_data[1] == "metasmoke":
                blacklisted_by = "the metasmoke API"
            else:
                blacklisted_by = blacklisted_user_data[1]
            blacklisted_post_url = blacklisted_user_data[2]
            if why and why[-1] == "\n":
                why = why[:-1]
            if blacklisted_post_url:
                rel_url = blacklisted_post_url.replace("http:", "", 1)
                ms_url = datahandling.resolve_ms_link(rel_url) or to_metasmoke_link(rel_url)
                why += "\nBlacklisted user - blacklisted for {} ({}) by {}".format(
                    blacklisted_post_url, ms_url, blacklisted_by)
            else:
                why += "\n" + u"Blacklisted user - blacklisted by {}".format(blacklisted_by)
    if test:
        result = None
        if datahandling.has_already_been_posted(post.post_site, post.post_id, post.title):
            result = "post has already been reported"
        elif datahandling.is_false_positive((post.post_id, post.post_site)):
            result = "post is marked as false positive"
        elif should_whitelist_prevent_alert(post.user_url, test):
            result = "user is whitelisted"
        elif datahandling.is_ignored_post((post.post_id, post.post_site)):
            result = "post is ignored"
        elif datahandling.is_auto_ignored_post((post.post_id, post.post_site)):
            result = "post is automatically ignored"
        elif datahandling.has_community_bumped_post(post.post_url, post.body):
            result = "post is bumped by Community \u2666\uFE0F"
        # Dirty approach
        if result is None or (dont_ignore_for is not None and result in dont_ignore_for):  # Post not ignored
            return True, test, why
        else:
            return False, (test, why), result

    return False, None, ""
    # Return value: (True, reasons, why) if post is spam
    #               (False, None, "") if post is not spam
    #               (False, (reasons, why), ignore_info) if post is spam but ignored
    # This is required because !!/report will check for 3rd tuple item to decide if it's not spam or spam but ignored


# noinspection PyMissingTypeHints
def check_if_spam_json(json_data):
    try:
        post = Post(json_data=json_data)
    except PostParseError as err:
        log('error', 'Parse error {0} when parsing json_data {1!r}'.format(
            err, json_data))
        return False, '', ''
    is_spam, reason, why = check_if_spam(post)
    return is_spam, reason, why


# noinspection PyBroadException,PyProtectedMember
def handle_spam(post, reasons, why):
    datahandling.append_to_latest_questions(post.post_site, post.post_id, post.title if not post.is_answer else "")

    if len(reasons) == 1 and ("all-caps title" in reasons or
                              "repeating characters in title" in reasons or
                              "repeating characters in body" in reasons or
                              "repeating characters in answer" in reasons or
                              "repeating words in title" in reasons or
                              "repeating words in body" in reasons or
                              "repeating words in answer" in reasons):
        datahandling.add_auto_ignored_post((post.post_id, post.post_site, datetime.utcnow()))

    if why is not None and why != "":
        datahandling.add_why(post.post_site, post.post_id, why)

    if post.is_answer and post.post_id is not None and post.post_id != "":
        datahandling.add_post_site_id_link((post.post_id, post.post_site, "answer"), post.parent.post_id)

    try:
        post_url = parsing.to_protocol_relative(parsing.url_to_shortlink(post.post_url))
        poster_url = parsing.to_protocol_relative(parsing.user_url_to_shortlink(post.user_url))
        if not post.user_name.strip() or (not poster_url or poster_url.strip() == ""):
            username = ""
        else:
            username = post.user_name.strip()

        Tasks.do(metasmoke.Metasmoke.send_stats_on_post,
                 post.title_ignore_type, post_url, reasons, post.body, post.markdown,
                 username, post.user_link, why, post.owner_rep, post.post_score,
                 post.up_vote_count, post.down_vote_count)

        offensive_mask = 'offensive title detected' in reasons
        message = build_message(post, reasons)
        if offensive_mask:
            post.title = "(potentially offensive title -- see MS for details)"
            clean_message = build_message(post, reasons)

        log('debug', GlobalVars.parser.unescape(message).encode('ascii', errors='replace'))
        GlobalVars.deletion_watcher.subscribe(post_url)

        without_roles = tuple(["no-" + reason for reason in reasons]) + ("site-no-" + post.post_site,)

        if set(reasons) - GlobalVars.experimental_reasons == set() and \
                not why.startswith("Post manually "):
            chatcommunicate.tell_rooms(message, ("experimental-all-sites", "experimental-site-" + post.post_site),
                                       without_roles, notify_site=post.post_site, report_data=(post_url, poster_url))
        else:
            if offensive_mask:
                chatcommunicate.tell_rooms(message, ("all-sites", "site-" + post.post_site),
                                           without_roles + ("offensive-mask",), notify_site=post.post_site,
                                           report_data=(post_url, poster_url))
                chatcommunicate.tell_rooms(clean_message, ("all-sites", "site-" + post.post_site),
                                           without_roles + ("no-offensive-mask",), notify_site=post.post_site,
                                           report_data=(post_url, poster_url))
            else:
                chatcommunicate.tell_rooms(message, ("all-sites", "site-" + post.post_site),
                                           without_roles, notify_site=post.post_site,
                                           report_data=(post_url, poster_url))
    except Exception as e:
        excepthook.uncaught_exception(*sys.exc_info())


def build_message(post, reasons):
    # This is the main report format. Username and user link are deliberately not separated as with title and post
    # link, because we may want to use "by a deleted user" rather than a username+link.
    message_format = "{prefix_ms} {{reasons}} ({reason_weight}): [{title}\u202D]({post_url}) by {user} on `{site}`"

    # Post URL, user URL, and site details are all easy - just data from the post object, transformed a bit
    # via datahandling.
    post_url = parsing.to_protocol_relative(parsing.url_to_shortlink(post.post_url))
    poster_url = parsing.to_protocol_relative(parsing.user_url_to_shortlink(post.user_url))
    shortened_site = post.post_site.replace("stackexchange.com", "SE")  # site.stackexchange.com -> site.SE

    # Message prefix. There's always a link to SmokeDetector; if we have a metasmoke key, there's also a link to the
    # post's MS record. If we *don't* have a MS key, it's a fair assumption that the post won't be in metasmoke as
    # we didn't have a key to create a record for it.
    prefix = u"[ [SmokeDetector](//git.io/vyDZv) ]"
    if GlobalVars.metasmoke_key:
        prefix = u"[ [SmokeDetector](//git.io/vyDZv) | [MS]({}) ]".format(
            to_metasmoke_link(post_url, protocol=False))

    # If we have reason weights cached (GlobalVars.reason_weights) we can calculate total weight for this report;
    # likewise, if we have a MS key, we can fetch the weights and then calculate. If we have neither, tough luck.
    with GlobalVars.reason_weights_lock:
        globalvars_reason_weights = GlobalVars.reason_weights
    if globalvars_reason_weights or GlobalVars.metasmoke_key:
        reason_weight = sum_weight(reasons)
        if reason_weight >= 1000:
            reason_weight = "**{}**".format(reason_weight)
        else:
            reason_weight = "{}".format(reason_weight)
    else:
        reason_weight = ""

    # If the post is an answer, it doesn't have a title, so we use the question's title instead. Either way, we
    # make sure it's escaped. We also add the edited indicator here.
    sanitized_title = parsing.sanitize_title(post.title if not post.is_answer else post.parent.title)
    sanitized_title = escape_format(sanitized_title).strip()
    if post.edited:  # Append a pencil emoji for edited posts
        sanitized_title += ' \u270F\uFE0F'

    # If we have user details available, we'll linkify the username. If we don't, we call it a deleted user.
    if not post.user_name.strip() or (not poster_url or poster_url.strip() == ""):
        user = "a deleted user"
    else:
        username = post.user_name.strip()
        escaped_username = escape_format(parsing.escape_markdown(username))
        user = "[{}\u202D]({})".format(escaped_username, poster_url)

    # Build the main body of the message. The next step is to insert the reason list while keeping the message
    # under 500 characters long.
    message = message_format.format(prefix_ms=prefix, reason_weight=reason_weight, title=sanitized_title,
                                    post_url=post_url, user=user, site=shortened_site)

    for reason_count in range(5, 0, -1):
        reason = ", ".join(reasons[:reason_count])
        if len(reasons) > reason_count:
            reason += ", +{} more".format(len(reasons) - reason_count)
        reason = reason.capitalize()
        attempt = message.format(reasons=reason)
        if len(attempt) <= 500:
            message = attempt
            break

    # If the message is still longer than 500 chars after trying to reduce the reason list, we're out of options,
    # so just cut the end of the message off.
    if len(message) > 500:
        message = message[:500]

    return message
