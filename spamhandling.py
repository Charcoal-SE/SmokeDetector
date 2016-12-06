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
import json
import time


def should_whitelist_prevent_alert(user_url, reasons):
    is_whitelisted = datahandling.is_whitelisted_user(parsing.get_user_from_url(user_url))
    if not is_whitelisted:
        return False
    reasons_comparison = [r for r in set(reasons) if "username" not in r]
    return len(reasons_comparison) == 0


def should_reasons_prevent_tavern_posting(reasons):
    reasons_comparison = [r for r in set(reasons) if r not in GlobalVars.non_tavern_reasons]
    return len(reasons_comparison) == 0


def check_if_spam(title, body, user_name, user_url, post_site, post_id, is_answer, body_is_summary, owner_rep, post_score):
    if not body:
        body = ""
    test, why = FindSpam.test_post(title, body, user_name, post_site, is_answer, body_is_summary, owner_rep, post_score)
    if datahandling.is_blacklisted_user(parsing.get_user_from_url(user_url)):
        test.append("blacklisted user")
        blacklisted_user_data = datahandling.get_blacklisted_user_data(parsing.get_user_from_url(user_url))
        if len(blacklisted_user_data) > 1:
            message_url = 'http:' + blacklisted_user_data[1]
            blacklisted_post_url = blacklisted_user_data[2]
            if blacklisted_post_url:
                rel_url = blacklisted_post_url.replace("http:", "", 1)
                why += u"\nBlacklisted user - blacklisted for {} (https://m.erwaysoftware.com/posts/by-url?url={}) by {}".format(blacklisted_post_url, rel_url, message_url)
            else:
                why += u"\n" + u"Blacklisted user - blacklisted by {}".format(message_url)
    if 0 < len(test):
        if datahandling.has_already_been_posted(post_site, post_id, title) or datahandling.is_false_positive((post_id, post_site)) \
                or should_whitelist_prevent_alert(user_url, test) \
                or datahandling.is_ignored_post((post_id, post_site)) \
                or datahandling.is_auto_ignored_post((post_id, post_site)):
            return False, None, ""  # Don't repost. Reddit will hate you.
        return True, test, why
    return False, None, ""


def check_if_spam_json(json_data):
    text_data = json.loads(json_data)["data"]
    if text_data == "hb":
        return False, None, ""
    try:
        data = json.loads(text_data)
    except ValueError:
        GlobalVars.charcoal_hq.send_message(u"Encountered ValueError parsing the following:\n{0}".format(json_data), False)
        return False, None, ""
    if "ownerUrl" not in data:
        # owner's account doesn't exist anymore, no need to post it in chat:
        # http://chat.stackexchange.com/transcript/message/18380776#18380776
        return False, None, ""
    title = data["titleEncodedFancy"]
    title = parsing.unescape_title(title)
    body = data["bodySummary"]
    poster = data["ownerDisplayName"]
    url = data["url"]
    post_id = str(data["id"])
    print time.strftime("%Y-%m-%d %H:%M:%S"), title.encode("ascii", errors="replace")
    site = data["siteBaseHostAddress"]
    site = site.encode("ascii", errors="replace")
    sys.stdout.flush()
    is_spam, reason, why = check_if_spam(title=title,
                                         body=body,
                                         user_name=poster,
                                         user_url=url,
                                         post_site=site,
                                         post_id=post_id,
                                         is_answer=False,
                                         body_is_summary=True,
                                         owner_rep=1,
                                         post_score=0)
    return is_spam, reason, why


def handle_spam(title, body, poster, site, post_url, poster_url, post_id, reasons, is_answer, why="", owner_rep=None, post_score=None, up_vote_count=None, down_vote_count=None, question_id=None):
    post_url = parsing.to_protocol_relative(parsing.url_to_shortlink(post_url))
    poster_url = parsing.to_protocol_relative(parsing.user_url_to_shortlink(poster_url))
    reason = ", ".join(reasons)
    reason = reason[:1].upper() + reason[1:]  # reason is capitalised, unlike the entries of reasons list
    datahandling.append_to_latest_questions(site, post_id, title if not is_answer else "")
    if len(reasons) == 1 and ("all-caps title" in reasons or
                              "repeating characters in title" in reasons or
                              "repeating characters in body" in reasons or
                              "repeating characters in answer" in reasons or
                              "repeating words in title" in reasons or
                              "repeating words in body" in reasons or
                              "repeating words in answer" in reasons):
        datahandling.add_auto_ignored_post((post_id, site, datetime.now()))
    if why is not None and why != "":
        datahandling.add_why(site, post_id, why)
    if is_answer and question_id is not None:
        datahandling.add_post_site_id_link((post_id, site, "answer"), question_id)
    try:
        title = parsing.escape_special_chars_in_title(title)
        sanitized_title = regex.sub('(https?://|\n)', '', title)

        prefix = u"[ [SmokeDetector](//git.io/vgx7b) ]"
        if GlobalVars.metasmoke_key:
            prefix_ms = u"[ [SmokeDetector](//git.io/vgx7b) | [MS](//m.erwaysoftware.com/posts/by-url?url=" + post_url + ") ]"
        else:
            prefix_ms = prefix

        if not poster.strip():
            s = u" {}: [{}]({}) by a deleted user on `{}`".format(reason, sanitized_title.strip(), post_url, site)
            username = ""
            user_link = ""
        else:
            s = u" {}: [{}]({}) by [{}]({}) on `{}`" .format(reason, sanitized_title.strip(), post_url, poster.strip(), poster_url, site)
            username = poster.strip()
            user_link = poster_url

        t_metasmoke = Thread(target=metasmoke.Metasmoke.send_stats_on_post,
                             args=(title, post_url, reason.split(", "), body, username, user_link, why, owner_rep, post_score, up_vote_count, down_vote_count))
        t_metasmoke.start()

        print GlobalVars.parser.unescape(s).encode('ascii', errors='replace')
        if time.time() >= GlobalVars.blockedTime["all"]:
            datahandling.append_to_latest_questions(site, post_id, title)
            if reason not in GlobalVars.experimental_reasons:
                if time.time() >= GlobalVars.blockedTime[GlobalVars.charcoal_room_id]:
                    chq_pings = datahandling.get_user_names_on_notification_list("stackexchange.com", GlobalVars.charcoal_room_id, site, GlobalVars.wrap)
                    chq_msg = prefix + s
                    chq_msg_pings = prefix + datahandling.append_pings(s, chq_pings)
                    chq_msg_pings_ms = prefix_ms + datahandling.append_pings(s, chq_pings)
                    msg_to_send = chq_msg_pings_ms if len(chq_msg_pings_ms) <= 500 else chq_msg_pings if len(chq_msg_pings) <= 500 else chq_msg[0:500]
                    GlobalVars.charcoal_hq.send_message(msg_to_send)
                if not should_reasons_prevent_tavern_posting(reasons) and site not in GlobalVars.non_tavern_sites and time.time() >= GlobalVars.blockedTime[GlobalVars.meta_tavern_room_id]:
                    tavern_pings = datahandling.get_user_names_on_notification_list("meta.stackexchange.com", GlobalVars.meta_tavern_room_id, site, GlobalVars.wrapm)
                    tavern_msg = prefix + s
                    tavern_msg_pings = prefix + datahandling.append_pings(s, tavern_pings)
                    tavern_msg_pings_ms = prefix_ms + datahandling.append_pings(s, tavern_pings)
                    msg_to_send = tavern_msg_pings_ms if len(tavern_msg_pings_ms) <= 500 else tavern_msg_pings if len(tavern_msg_pings) <= 500 else tavern_msg[0:500]
                    t_check_websocket = Thread(target=deletionwatcher.DeletionWatcher.post_message_if_not_deleted, args=((post_id, site, "answer" if is_answer else "question"), post_url, msg_to_send, GlobalVars.tavern_on_the_meta))
                    t_check_websocket.daemon = True
                    t_check_websocket.start()
                if site == "stackoverflow.com" and reason not in GlobalVars.non_socvr_reasons and time.time() >= GlobalVars.blockedTime[GlobalVars.socvr_room_id]:
                    socvr_pings = datahandling.get_user_names_on_notification_list("stackoverflow.com", GlobalVars.socvr_room_id, site, GlobalVars.wrapso)
                    socvr_msg = prefix + s
                    socvr_msg_pings = prefix + datahandling.append_pings(s, socvr_pings)
                    socvr_msg_pings_ms = prefix_ms + datahandling.append_pings(s, socvr_pings)
                    msg_to_send = socvr_msg_pings_ms if len(socvr_msg_pings_ms) <= 500 else socvr_msg_pings if len(socvr_msg_pings) <= 500 else socvr_msg[0:500]
                    GlobalVars.socvr.send_message(msg_to_send)

            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if site in sites and reason not in specialroom["unwantedReasons"]:
                    room = specialroom["room"]
                    if room.id not in GlobalVars.blockedTime or time.time() >= GlobalVars.blockedTime[room.id]:
                        room_site = room._client.host
                        room_id = int(room.id)
                        room_pings = datahandling.get_user_names_on_notification_list(room_site, room_id, site, room._client)
                        room_msg = prefix + s
                        room_msg_pings = prefix + datahandling.append_pings(s, room_pings)
                        room_msg_pings_ms = prefix_ms + datahandling.append_pings(s, room_pings)
                        msg_to_send = room_msg_pings_ms if len(room_msg_pings_ms) <= 500 else room_msg_pings if len(room_msg_pings) <= 500 else room_msg[0:500]
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
        if site in specialroom["sites"] and (room.id not in GlobalVars.blockedTime or time.time() >= GlobalVars.blockedTime[room.id]):
            room.send_message(s)
