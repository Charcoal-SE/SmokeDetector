import sys
from threading import Thread
from findspam import FindSpam
import datahandling
from globalvars import GlobalVars
from datetime import datetime
import parsing
import metasmoke
import deletionwatcher
import excepthook
import regex
import time
from classes import Post


# noinspection PyMissingTypeHints
def should_whitelist_prevent_alert(user_url, reasons):
    is_whitelisted = datahandling.is_whitelisted_user(parsing.get_user_from_url(user_url))
    if not is_whitelisted:
        return False
    reasons_comparison = [r for r in set(reasons) if "username" not in r]
    return len(reasons_comparison) == 0


def should_reasons_prevent_tavern_posting(reasons):
    reasons_comparison = [r for r in set(reasons) if r not in GlobalVars.non_tavern_reasons]
    return len(reasons_comparison) == 0


# noinspection PyMissingTypeHints
def check_if_spam(post):
    # if not post.body:
    #     body = ""
    # test, why = FindSpam.test_post(title, body, user_name, post_site,
    # is_answer, body_is_summary, owner_rep, post_score)
    test, why = FindSpam.test_post(post)
    if datahandling.is_blacklisted_user(parsing.get_user_from_url(post.user_url)):
        test.append("blacklisted user")
        blacklisted_user_data = datahandling.get_blacklisted_user_data(parsing.get_user_from_url(post.user_url))
        if len(blacklisted_user_data) > 1:
            message_url = 'http:' + blacklisted_user_data[1]
            blacklisted_post_url = blacklisted_user_data[2]
            if blacklisted_post_url:
                rel_url = blacklisted_post_url.replace("http:", "", 1)
                why += u"\nBlacklisted user - blacklisted for {} (" \
                       u"https://m.erwaysoftware.com/posts/by-url?url={}) by {}".format(blacklisted_post_url, rel_url,
                                                                                        message_url)
            else:
                why += u"\n" + u"Blacklisted user - blacklisted by {}".format(message_url)
    if 0 < len(test):
        if datahandling.has_already_been_posted(post.post_site, post.post_id, post.title) \
                or datahandling.is_false_positive((post.post_id, post.post_site)) \
                or should_whitelist_prevent_alert(post.user_url, test) \
                or datahandling.is_ignored_post((post.post_id, post.post_site)) \
                or datahandling.is_auto_ignored_post((post.post_id, post.post_site)):
            return False, None, ""  # Don't repost. Reddit will hate you.
        return True, test, why
    return False, None, ""


# noinspection PyMissingTypeHints
def check_if_spam_json(json_data):
    post = Post(json_data=json_data)
    is_spam, reason, why = check_if_spam(post)
    return is_spam, reason, why


# noinspection PyBroadException,PyProtectedMember
def handle_spam(post, reasons, why):
    post_url = parsing.to_protocol_relative(parsing.url_to_shortlink(post.post_url))
    poster_url = parsing.to_protocol_relative(parsing.user_url_to_shortlink(post.user_url))
    reason = ", ".join(reasons[:5])
    if len(reasons) > 5:
        reason += ", +{} more".format(len(reasons) - 5)
    reason = reason[:1].upper() + reason[1:]  # reason is capitalised, unlike the entries of reasons list
    shortened_site = post.post_site.replace("stackexchange.com", "SE")  # site.stackexchange.com -> site.SE
    datahandling.append_to_latest_questions(post.post_site, post.post_id, post.title if not post.is_answer else "")
    if len(reasons) == 1 and ("all-caps title" in reasons or
                              "repeating characters in title" in reasons or
                              "repeating characters in body" in reasons or
                              "repeating characters in answer" in reasons or
                              "repeating words in title" in reasons or
                              "repeating words in body" in reasons or
                              "repeating words in answer" in reasons):
        datahandling.add_auto_ignored_post((post.post_id, post.post_site, datetime.now()))
    if why is not None and why != "":
        datahandling.add_why(post.post_site, post.post_id, why)
    if post.is_answer and post.question_id is not None:
        datahandling.add_post_site_id_link((post.post_id, post.post_site, "answer"), post.question_id)
    try:
        post.title = parsing.escape_special_chars_in_title(post.title)
        sanitized_title = regex.sub('(https?://|\n)', '', post.title)

        prefix = u"[ [SmokeDetector](//goo.gl/eLDYqh) ]"
        if GlobalVars.metasmoke_key:
            prefix_ms = u"[ [SmokeDetector](//goo.gl/eLDYqh) | [MS](//m.erwaysoftware.com/posts/by-url?url=" + \
                        post_url + ") ]"
        else:
            prefix_ms = prefix

        if not post.user_name.strip():
            s = u" {}: [{}]({}) by a deleted user on `{}`".format(reason, sanitized_title.strip(), post_url,
                                                                  shortened_site)
            username = ""
        else:
            s = u" {}: [{}]({}) by [{}]({}) on `{}`".format(reason, sanitized_title.strip(), post_url,
                                                            post.user_name.strip(), poster_url, shortened_site)
            username = post.user_name.strip()

        t_metasmoke = Thread(name="metasmoke send post",
                             target=metasmoke.Metasmoke.send_stats_on_post,
                             args=(post.title, post.post_url, reasons, post.body, username,
                                   post.user_link, why, post.owner_rep, post.post_score,
                                   post.up_vote_count, post.down_vote_count))
        t_metasmoke.start()

        print GlobalVars.parser.unescape(s).encode('ascii', errors='replace')
        if time.time() >= GlobalVars.blockedTime["all"]:
            datahandling.append_to_latest_questions(post.post_site, post.post_id, post.title)
            if reason not in GlobalVars.experimental_reasons:
                if time.time() >= GlobalVars.blockedTime[GlobalVars.charcoal_room_id]:
                    chq_pings = datahandling.get_user_names_on_notification_list("stackexchange.com",
                                                                                 GlobalVars.charcoal_room_id,
                                                                                 post.post_site,
                                                                                 GlobalVars.wrap)
                    chq_msg = prefix + s
                    chq_msg_pings = prefix + datahandling.append_pings(s, chq_pings)
                    chq_msg_pings_ms = prefix_ms + datahandling.append_pings(s, chq_pings)
                    msg_to_send = chq_msg_pings_ms if len(chq_msg_pings_ms) <= 500 else chq_msg_pings \
                        if len(chq_msg_pings) <= 500 else chq_msg[0:500]
                    GlobalVars.charcoal_hq.send_message(msg_to_send)
                if not should_reasons_prevent_tavern_posting(reasons) \
                        and post.post_site not in GlobalVars.non_tavern_sites \
                        and time.time() >= GlobalVars.blockedTime[GlobalVars.meta_tavern_room_id]:
                    tavern_pings = datahandling.get_user_names_on_notification_list("meta.stackexchange.com",
                                                                                    GlobalVars.meta_tavern_room_id,
                                                                                    post.post_site, GlobalVars.wrapm)
                    tavern_msg = prefix + s
                    tavern_msg_pings = prefix + datahandling.append_pings(s, tavern_pings)
                    tavern_msg_pings_ms = prefix_ms + datahandling.append_pings(s, tavern_pings)
                    msg_to_send = tavern_msg_pings_ms if len(tavern_msg_pings_ms) <= 500 else tavern_msg_pings \
                        if len(tavern_msg_pings) <= 500 else tavern_msg[0:500]
                    t_check_websocket = Thread(name="deletionwatcher post message if not deleted",
                                               target=deletionwatcher.DeletionWatcher.post_message_if_not_deleted,
                                               args=((post.post_id, post.post_site,
                                                      "answer" if post.is_answer else "question"),
                                                     post_url, msg_to_send, GlobalVars.tavern_on_the_meta))
                    t_check_websocket.daemon = True
                    t_check_websocket.start()
                if post.post_site == "stackoverflow.com" and reason not in GlobalVars.non_socvr_reasons \
                        and time.time() >= GlobalVars.blockedTime[GlobalVars.socvr_room_id]:
                    socvr_pings = datahandling.get_user_names_on_notification_list("stackoverflow.com",
                                                                                   GlobalVars.socvr_room_id,
                                                                                   post.post_site,
                                                                                   GlobalVars.wrapso)
                    socvr_msg = prefix + s
                    socvr_msg_pings = prefix + datahandling.append_pings(s, socvr_pings)
                    socvr_msg_pings_ms = prefix_ms + datahandling.append_pings(s, socvr_pings)
                    msg_to_send = socvr_msg_pings_ms if len(socvr_msg_pings_ms) <= 500 else socvr_msg_pings \
                        if len(socvr_msg_pings) <= 500 else socvr_msg[0:500]
                    GlobalVars.socvr.send_message(msg_to_send)

            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if post.post_site in sites and reason not in specialroom["unwantedReasons"]:
                    room = specialroom["room"]
                    if room.id not in GlobalVars.blockedTime or time.time() >= GlobalVars.blockedTime[room.id]:
                        room_site = room._client.host
                        room_id = int(room.id)
                        room_pings = datahandling.get_user_names_on_notification_list(room_site, room_id,
                                                                                      post.post_site, room._client)
                        room_msg = prefix + s
                        room_msg_pings = prefix + datahandling.append_pings(s, room_pings)
                        room_msg_pings_ms = prefix_ms + datahandling.append_pings(s, room_pings)
                        msg_to_send = room_msg_pings_ms if len(room_msg_pings_ms) <= 500 else room_msg_pings \
                            if len(room_msg_pings) <= 500 else room_msg[0:500]
                        specialroom["room"].send_message(msg_to_send)
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        excepthook.uncaught_exception(exc_type, exc_obj, exc_tb)


def handle_user_with_all_spam(user, why):
    user_id = user[0]
    site = user[1]
    tab = "activity" if site == "stackexchange.com" else "topactivity"
    s = "[ [SmokeDetector](//git.io/vgx7b) ] All of this user's posts are spam: [user {} on {}](//{}/users/{}?tab={})" \
        .format(user_id, site, site, user_id, tab)
    print GlobalVars.parser.unescape(s).encode('ascii', errors='replace')
    datahandling.add_why_allspam(user, why)
    if time.time() >= GlobalVars.blockedTime[GlobalVars.charcoal_room_id]:
        GlobalVars.charcoal_hq.send_message(s)
    for specialroom in GlobalVars.specialrooms:
        room = specialroom["room"]
        if site in specialroom["sites"] and (room.id not in GlobalVars.blockedTime or
                                             time.time() >= GlobalVars.blockedTime[room.id]):
            room.send_message(s)
