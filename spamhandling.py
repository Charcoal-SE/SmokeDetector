import json
import re
import sys
import time
from findspam import FindSpam
from datahandling import *
from parsing import get_user_from_url
from bayesianfuncs import *


def get_spam_reasons(title, body, user_name, site):
    reasons = []
    if title is not None:
        reasons += FindSpam.testpost(title, user_name, site)
    if body is not None:
        reasons += FindSpam.testbody(body, site)
    return reasons


def checkifspam(title, body, user_name, user_url, post_site, post_id, post_url):
    test = get_spam_reasons(title, body, user_name, post_site)
    if 0 < len(test):
        if is_blacklisted_user(get_user_from_url(user_url)):
            test.append("Blacklisted user")
        if 0 < len(test):
            if has_already_been_posted(post_site, post_id, title) or is_false_positive(post_id, post_site) \
                    or is_whitelisted_user(get_user_from_url(user_url)) \
                    or is_ignored_post((post_id, post_site)) \
                    or is_auto_ignored_post((post_id, post_site)):
                return False # Don't repost. Reddit will hate you.
            append_to_latest_questions(post_site, post_id, title)
            if len(test) == 1 and "All-caps title" in test:
                add_auto_ignored_post((post_id, post_site, datetime.now()))
            try:
                owner = user_url
                users_file = open("users.txt", "a")
                users_file.write(post_site + " " + owner + " " + title + " " + post_url + "\n")
                users_file.close()
            except Exception as e:
                print e
            return True
        return False


def checkifspam_json(data):
    d = json.loads(json.loads(data)["data"])
    try:
        _ = d["ownerUrl"]
    except:
        return False # owner's account doesn't exist anymore, no need to post it in chat:
                     # http://chat.stackexchange.com/transcript/message/18380776#18380776
    title = d["titleEncodedFancy"]
    title = GlobalVars.parser.unescape(re.sub(r"([_*\\`\[\]])", r"\\\1", title))
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
    return checkifspam(title, None, poster, d["ownerUrl"], site, str(d["id"]), url)


def handlespam(title, body, poster, site, post_url, poster_url):
    try:
        reason = ", ".join(get_spam_reasons(title, body, poster, site))
        s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % \
          (reason, title.strip(), post_url, poster.strip(), poster_url, site)
        print GlobalVars.parser.unescape(s).encode('ascii',errors='replace')
        if time.time() >= GlobalVars.blockedTime:
            GlobalVars.charcoal_hq.send_message(s)
            GlobalVars.tavern_on_the_meta.send_message(s)
            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if site in sites and reason not in specialroom["unwantedReasons"]:
                    specialroom["room"].send_message(s)
    except:
        print "NOP"


def handlespam_json(data):
    try:
        d=json.loads(json.loads(data)["data"])
        title = d["titleEncodedFancy"]
        poster = d["ownerDisplayName"]
        site = d["siteBaseHostAddress"]
        url = d["url"]
        poster_url = d["ownerUrl"]
        title_to_post = GlobalVars.parser.unescape(re.sub(r"([_*\\`\[\]])", r"\\\1", title)).strip()
        handlespam(title_to_post, None, poster, site, url, poster_url)
    except:
        print "NOP"