import json
import sys
import time
from findspam import FindSpam
from datahandling import *
from parsing import get_user_from_url, fetch_unescaped_title_from_encoded
from bayesianfuncs import *


def check_if_spam(title, body, user_name, user_url, post_site, post_id, is_answer):
    if not body:
        body = ""
    test = FindSpam.test_post(title, body, user_name, post_site, is_answer)
    if is_blacklisted_user(get_user_from_url(user_url)):
        test.append("Blacklisted user")
    if 0 < len(test):
        if has_already_been_posted(post_site, post_id, title) or is_false_positive((post_id, post_site)) \
                or is_whitelisted_user(get_user_from_url(user_url)) \
                or is_ignored_post((post_id, post_site)) \
                or is_auto_ignored_post((post_id, post_site)):
            return False, None # Don't repost. Reddit will hate you.
        return True, test
    return False, None


def check_if_spam_json(data):
    d = json.loads(json.loads(data)["data"])
    try:
        _ = d["ownerUrl"]
    except:
        return False, None # owner's account doesn't exist anymore, no need to post it in chat:
                           # http://chat.stackexchange.com/transcript/message/18380776#18380776
    title = d["titleEncodedFancy"]
    title = fetch_unescaped_title_from_encoded(title)
    poster = d["ownerDisplayName"]
    url = d["url"]
    print time.strftime("%Y-%m-%d %H:%M:%S"),title.encode("ascii",errors="replace")
    quality_score = bayesian_score(title)
    print quality_score
    if quality_score < 0.3 and d["siteBaseHostAddress"] == "stackoverflow.com":
        print GlobalVars.bayesian_testroom.send_message("[ SmokeDetector | BayesianBeta ] Quality score " + str(quality_score * 100) + ": [" + title + "](" + url + ")")
    site = d["siteBaseHostAddress"]
    site = site.encode("ascii",errors="replace")
    sys.stdout.flush()
    is_spam, reason = check_if_spam(title, None, poster, d["ownerUrl"], site, str(d["id"]), False)
    return is_spam, reason


def handle_spam(title, poster, site, post_url, poster_url, post_id, reasons):
    reason = ", ".join(reasons)
    append_to_latest_questions(site, post_id, title)
    if len(reasons) == 1 and ("All-caps title" in reasons or "Repeating characters" in reasons):
        add_auto_ignored_post((post_id, site, datetime.now()))
    try:
        owner = poster_url
        users_file = open("users.txt", "a")
        users_file.write(site + " " + owner + " " + title + " " + post_url + "\n")
        users_file.close()
    except Exception as e:
        print e
    try:
        s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % \
          (reason, title.strip(), post_url, poster.strip(), poster_url, site)
        print GlobalVars.parser.unescape(s).encode('ascii',errors='replace')
        if time.time() >= GlobalVars.blockedTime:
            append_to_latest_questions(site, post_id, title)
            GlobalVars.charcoal_hq.send_message(s)
            GlobalVars.tavern_on_the_meta.send_message(s)
            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if site in sites and reason not in specialroom["unwantedReasons"]:
                    specialroom["room"].send_message(s)
    except:
        print "NOP"


def handle_spam_json(data, reason):
    try:
        d=json.loads(json.loads(data)["data"])
        title = d["titleEncodedFancy"]
        poster = d["ownerDisplayName"]
        site = d["siteBaseHostAddress"]
        url = d["url"]
        poster_url = d["ownerUrl"]
        post_id = d["id"]
        title_to_post = fetch_unescaped_title_from_encoded(title)
        handle_spam(title_to_post, poster, site, url, poster_url, post_id, reason)
    except:
        print "NOP"
