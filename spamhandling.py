import json
import re
import sys
import time
from findspam import FindSpam
from datahandling import *
from parsing import get_user_from_url
from bayesianfuncs import *

def checkifspam(data):
    d = json.loads(json.loads(data)["data"])
    try:
        _ = d["ownerUrl"]
    except:
        return False # owner's account doesn't exist anymore, no need to post it in chat:
                     # http://chat.stackexchange.com/transcript/message/18380776#18380776
    s = d["titleEncodedFancy"]
    poster = d["ownerDisplayName"]
    print time.strftime("%Y-%m-%d %H:%M:%S"),GlobalVars.parser.unescape(s).encode("ascii",errors="replace")
    quality_score = bayesian_score(s)
    print quality_score
    if quality_score < 0.3 and d["siteBaseHostAddress"] == "stackoverflow.com":
        print GlobalVars.bayesian_testroom.send_message("[ SmokeDetector | BayesianBeta ] Quality score " + str(quality_score*100) + ": [" + s + "](" + d["url"] + ")")
    site = d["siteBaseHostAddress"]
    site=site.encode("ascii",errors="replace")
    sys.stdout.flush()
    test=FindSpam.testpost(s,poster,site)
    if is_blacklisted_user(get_user_from_url(d["ownerUrl"])):
        test.append("Blacklisted user")
    if 0 < len(test):
        post_id = d["id"]
        if has_already_been_posted(site, post_id, s) or is_false_positive(post_id, site) \
                or is_whitelisted_user(get_user_from_url(d["ownerUrl"])) or is_ignored_post((str(post_id), site)) \
                or is_auto_ignored_post((str(post_id), site)):
            return False # Don't repost. Reddit will hate you.
        append_to_latest_questions(site, post_id, s)
        if len(test) == 1 and "All-caps title" in test:
            add_auto_ignored_post( (str(post_id), site, datetime.now()) )
        try:
            owner = d["ownerUrl"]
            users_file = open("users.txt", "a")
            users_file.write(site + " " + owner + " " + d["titleEncodedFancy"] + " " + d["url"] + "\n")
            users_file.close()
        except Exception as e:
            print e
        return True
    return False


def handlespam(data):
    try:
        d=json.loads(json.loads(data)["data"])
        title = d["titleEncodedFancy"]
        poster = d["ownerDisplayName"]
        reason = ", ".join(FindSpam.testpost(title,poster,d["siteBaseHostAddress"]))
        title_to_post = GlobalVars.parser.unescape(re.sub(r"([_*\\`\[\]])", r"\\\1", title)).strip()
        s = "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % \
          (reason,title_to_post.strip(), d["url"],poster.strip(), d["ownerUrl"], d["siteBaseHostAddress"])
        print GlobalVars.parser.unescape(s).encode('ascii',errors='replace')
        if time.time() >= GlobalVars.blockedTime:
            GlobalVars.charcoal_hq.send_message(s)
            GlobalVars.tavern_on_the_meta.send_message(s)
            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if d["siteBaseHostAddress"] in sites and reason not in specialroom["unwantedReasons"]:
                    specialroom["room"].send_message(s)
    except:
        print "NOP"