import json
import sys
import time
from threading import Thread
from findspam import FindSpam
from datahandling import *
from parsing import get_user_from_url, unescape_title,\
    escape_special_chars_in_title, to_protocol_relative
from bayesianfuncs import bayesian_score
from globalvars import GlobalVars
from datetime import datetime
from parsing import url_to_shortlink
from metasmoke import Metasmoke


def should_whitelist_prevent_alert(user_url, reasons):
    is_whitelisted = is_whitelisted_user(get_user_from_url(user_url))
    if not is_whitelisted:
        return False
    reasons_copy = list(set(reasons))
    reasons_copy_copy = list(reasons_copy)
    for reason in reasons_copy:
        if "username" in reason:
            reasons_copy_copy.remove(reason)
    return len(reasons_copy_copy) == 0


def check_if_spam(title, body, user_name, user_url, post_site, post_id, is_answer, body_is_summary):
    if not body:
        body = ""
    test, why = FindSpam.test_post(title, body, user_name, post_site, is_answer, body_is_summary)
    if is_blacklisted_user(get_user_from_url(user_url)):
        test.append("Blacklisted user")
    if 0 < len(test):
        if has_already_been_posted(post_site, post_id, title) or is_false_positive((post_id, post_site)) \
                or should_whitelist_prevent_alert(user_url, test) \
                or is_ignored_post((post_id, post_site)) \
                or is_auto_ignored_post((post_id, post_site)):
            return False, None, ""  # Don't repost. Reddit will hate you.
        return True, test, why
    return False, None, ""


def check_if_spam_json(data):
    d = json.loads(json.loads(data)["data"])
    try:
        _ = d["ownerUrl"]  # noqa
    except:
        # owner's account doesn't exist anymore, no need to post it in chat:
        # http://chat.stackexchange.com/transcript/message/18380776#18380776
        return False, None, ""
    title = d["titleEncodedFancy"]
    title = unescape_title(title)
    body = d["bodySummary"]
    poster = d["ownerDisplayName"]
    url = d["url"]
    post_id = str(d["id"])
    print time.strftime("%Y-%m-%d %H:%M:%S"), title.encode("ascii", errors="replace")
    quality_score = bayesian_score(title)
    print quality_score
    if quality_score < 0.3 and d["siteBaseHostAddress"] == "stackoverflow.com":
        print GlobalVars.bayesian_testroom.send_message("[ SmokeDetector | BayesianBeta ] Quality score " + str(quality_score * 100) + ": [" + title + "](" + url + ")")
    site = d["siteBaseHostAddress"]
    site = site.encode("ascii", errors="replace")
    sys.stdout.flush()
    is_spam, reason, why = check_if_spam(title, body, poster, url, site, post_id, False, True)
    return is_spam, reason, why


def handle_spam(title, body, poster, site, post_url, poster_url, post_id, reasons, is_answer, why=""):
    post_url = to_protocol_relative(url_to_shortlink(post_url))
    poster_url = to_protocol_relative(poster_url)
    reason = ", ".join(reasons).capitalize()
    if "Url" in reason:
        reason = reason.replace("Url", "URL")
    append_to_latest_questions(site, post_id, title if not is_answer else "")
    if len(reasons) == 1 and ("All-caps title" in reasons or
                              "Repeating characters in title" in reasons or
                              "Repeating characters in body" in reasons or
                              "Repeating characters in answer" in reasons or
                              "Repeating words in title" in reasons or
                              "Repeating words in body" in reasons or
                              "Repeating words in answer" in reasons):
        add_auto_ignored_post((post_id, site, datetime.now()))
    if why is not None and why != "":
        add_why(site, post_id, why)
    try:
        owner = poster_url
        users_file = open("users.txt", "a")
        users_file.write(site + " " + owner + " " + title + " " + post_url + "\n")
        users_file.close()
    except Exception as e:
        print e
    try:
        title = escape_special_chars_in_title(title)

        t_metasmoke = Thread(target=Metasmoke.send_stats_on_post,
                             args=(title, post_url, reason.split(", "), body,))
        t_metasmoke.start()

        if not poster.strip():
            s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by a deleted user on `%s`" % \
                (reason, title.strip(), post_url, site)
        else:
            s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % \
                (reason, title.strip(), post_url, poster.strip(), poster_url, site)
        print GlobalVars.parser.unescape(s).encode('ascii', errors='replace')
        if time.time() >= GlobalVars.blockedTime:
            append_to_latest_questions(site, post_id, title)

            if reason not in GlobalVars.experimental_reasons:
                GlobalVars.charcoal_hq.send_message(s)
                GlobalVars.tavern_on_the_meta.send_message(s)
                if site == "stackoverflow.com":
                    GlobalVars.socvr.send_message(s)

            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if site in sites and reason not in specialroom["unwantedReasons"]:
                    specialroom["room"].send_message(s)
    except:
        print "NOP"


def handle_spam_json(data, reason, why=""):
    try:
        d = json.loads(json.loads(data)["data"])
        title = unescape_title(d["titleEncodedFancy"])
        body = d["bodySummary"]
        poster = d["ownerDisplayName"]
        site = d["siteBaseHostAddress"]
        url = d["url"]
        poster_url = d["ownerUrl"]
        post_id = str(d["id"])
        handle_spam(title, body, poster, site, url, poster_url, post_id, reason, False, why)
    except:
        print "NOP"
