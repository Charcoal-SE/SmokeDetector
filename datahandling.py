import os
import pickle
from datetime import datetime
from globalvars import GlobalVars
import requests
import json
import regex
import time
import math


# methods to load files and filter data in them:


def load_files():
    if os.path.isfile("falsePositives.txt"):
        with open("falsePositives.txt", "r") as f:
            GlobalVars.false_positives = pickle.load(f)
    if os.path.isfile("whitelistedUsers.txt"):
        with open("whitelistedUsers.txt", "r") as f:
            GlobalVars.whitelisted_users = pickle.load(f)
    if os.path.isfile("blacklistedUsers.txt"):
        with open("blacklistedUsers.txt", "r") as f:
            GlobalVars.blacklisted_users = pickle.load(f)
    if os.path.isfile("ignoredPosts.txt"):
        with open("ignoredPosts.txt", "r") as f:
            GlobalVars.ignored_posts = pickle.load(f)
    if os.path.isfile("autoIgnoredPosts.txt"):
        with open("autoIgnoredPosts.txt", "r") as f:
            GlobalVars.auto_ignored_posts = pickle.load(f)
    if os.path.isfile("notifications.txt"):
        with open("notifications.txt", "r") as f:
            GlobalVars.notifications = pickle.load(f)
    if os.path.isfile("frequentSentences.txt"):
        with open("frequentSentences.txt", "r") as f:
            lines = f.readlines()
            for line in lines:
                GlobalVars.frequent_sentences.append(line.strip())
    if os.path.isfile("whyData.txt"):
        with open("whyData.txt", "r") as f:
            GlobalVars.why_data = pickle.load(f)
    if os.path.isfile("latestMessages.txt"):
        with open("latestMessages.txt", "r") as f:
            GlobalVars.latest_smokedetector_messages = pickle.load(f)
    if os.path.isfile("apiCalls.txt"):
        with open("apiCalls.txt", "r") as f:
            GlobalVars.api_calls_per_site = pickle.load(f)


def filter_auto_ignored_posts():
    today_date = datetime.today()
    to_remove = []
    for aip in GlobalVars.auto_ignored_posts:
        day_ignored = aip[2]
        day_diff = (today_date - day_ignored).days
        if day_diff > 7:
            to_remove.append(aip)
    for tr in to_remove:
        GlobalVars.auto_ignored_posts.remove(tr)
    with open("autoIgnoredPosts.txt", "w") as f:
        pickle.dump(GlobalVars.auto_ignored_posts, f)


# methods to check whether a post/user is whitelisted/blacklisted/...


def is_false_positive(postid_site_tuple):
    return postid_site_tuple in GlobalVars.false_positives


def is_whitelisted_user(user):
    return user in GlobalVars.whitelisted_users


def is_blacklisted_user(user):
    for blacklisted_user in GlobalVars.blacklisted_users:
        if user == blacklisted_user[0]:
            return True
    return False


def get_blacklisted_user_data(user):
    for blacklisted_user in GlobalVars.blacklisted_users:
        if user == blacklisted_user[0]:
            return blacklisted_user
    return ()


def is_ignored_post(postid_site_tuple):
    return postid_site_tuple in GlobalVars.ignored_posts


def is_auto_ignored_post(postid_site_tuple):
    for p in GlobalVars.auto_ignored_posts:
        if p[0] == postid_site_tuple[0] and p[1] == postid_site_tuple[1]:
            return True
    return False


def is_privileged(room_id_str, user_id_str, wrap2):
    if room_id_str in GlobalVars.privileged_users and user_id_str in GlobalVars.privileged_users[room_id_str]:
        return True
    user = wrap2.get_user(user_id_str)
    return user.is_moderator

# methods to add/remove whitelisted/blacklisted users, ignored posts, ...


def add_whitelisted_user(user):
    if user in GlobalVars.whitelisted_users or user is None:
        return
    GlobalVars.whitelisted_users.append(user)
    with open("whitelistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.whitelisted_users, f)


def add_blacklisted_user(user, message_url, post_url):
    if is_blacklisted_user(user) or user is None:
        return
    GlobalVars.blacklisted_users.append((user, message_url, post_url))
    with open("blacklistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.blacklisted_users, f)


def add_auto_ignored_post(postid_site_tuple):
    if postid_site_tuple is None or is_auto_ignored_post(postid_site_tuple):
        return
    GlobalVars.auto_ignored_posts.append(postid_site_tuple)
    with open("autoIgnoredPosts.txt", "w") as f:
        pickle.dump(GlobalVars.auto_ignored_posts, f)


def add_false_positive(site_post_id_tuple):
    if site_post_id_tuple is None or site_post_id_tuple in GlobalVars.false_positives:
        return
    GlobalVars.false_positives.append(site_post_id_tuple)
    with open("falsePositives.txt", "w") as f:
        pickle.dump(GlobalVars.false_positives, f)


def add_ignored_post(postid_site_tuple):
    if postid_site_tuple is None or postid_site_tuple in GlobalVars.ignored_posts:
        return
    GlobalVars.ignored_posts.append(postid_site_tuple)
    with open("ignoredPosts.txt", "w") as f:
        pickle.dump(GlobalVars.ignored_posts, f)


def remove_blacklisted_user(user):
    blacklisted_user_data = get_blacklisted_user_data(user)
    if not blacklisted_user_data:
        return False
    GlobalVars.blacklisted_users.remove(blacklisted_user_data)
    with open("blacklistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.blacklisted_users, f)
    return True


def remove_whitelisted_user(user):
    if user not in GlobalVars.whitelisted_users:
        return False
    GlobalVars.whitelisted_users.remove(user)
    with open("whitelistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.whitelisted_users, f)
    return True


def add_why(site, post_id, why):
    key = site + "/" + str(post_id)
    t = (key, why)
    GlobalVars.why_data.append(t)
    filter_why()
    with open("whyData.txt", "w") as f:
        pickle.dump(GlobalVars.why_data, f)


def get_why(site, post_id):
    key = site + "/" + str(post_id)
    for w in GlobalVars.why_data:
        if w[0] == key:
            return w[1]
    return None


def filter_why(max_size=50):
    GlobalVars.why_data = GlobalVars.why_data[-max_size:]


def add_latest_smokedetector_message(room, message_id):
    GlobalVars.latest_smokedetector_messages[room].append(message_id)
    # Keep the last 100 messages
    max_size = 100
    GlobalVars.latest_smokedetector_messages[room] = GlobalVars.latest_smokedetector_messages[room][-max_size:]
    with open("latestMessages.txt", "w") as f:
        pickle.dump(GlobalVars.latest_smokedetector_messages, f)


def add_or_update_api_data(site):
    if site in GlobalVars.api_calls_per_site:
        GlobalVars.api_calls_per_site[site] += 1
    else:
        GlobalVars.api_calls_per_site[site] = 1
    with open("apiCalls.txt", "w") as f:
        pickle.dump(GlobalVars.api_calls_per_site, f)


def clear_api_data():
    GlobalVars.api_calls_per_site = {}
    with open("apiCalls.txt", "w") as f:
        pickle.dump(GlobalVars.api_calls_per_site, f)


# methods that help avoiding reposting alerts:


def append_to_latest_questions(host, post_id, title):
    GlobalVars.latest_questions.insert(0, (host, str(post_id), title))
    if len(GlobalVars.latest_questions) > 15:
        GlobalVars.latest_questions.pop()


def has_already_been_posted(host, post_id, title):
    for post in GlobalVars.latest_questions:
        if post[0] == host and post[1] == str(post_id) and post[2] == title:
            return True
    return False


# method to get data from the error log:


def fetch_lines_from_error_log(line_count):
    if not os.path.isfile("errorLogs.txt"):
        return "The error log file does not exist."
    if line_count <= 0:
        return "Please request a line count greater than zero."
    lines = []
    with open("errorLogs.txt", "r") as f:
        lines = f.readlines()[-line_count:]
    formatted_lines = []
    for line in lines:
        formatted_lines.append("    " + line.rstrip())
    fetched = os.linesep.join(formatted_lines)
    if fetched.rstrip() == "":
        return "The fetched part is empty. Please try another line count."
    return fetched


# method to check whether a SE site exists:


def refresh_sites():
    has_more = True
    page = 1
    while has_more:
        resp = requests.get("https://api.stackexchange.com/2.2/sites?filter=!%29Qpa1bTB_jCkeaZsqiQ8pDwI&pagesize=500&page=" + str(page) + "&key=IAkbitmze4B8KpacUfLqkw((")
        data = json.loads(resp.text)
        if "error_message" in data:
            return False, data["error_message"]
        if "items" not in data:
            return False, "`items` not in JSON data"
        if "has_more" not in data:
            return False, "`has_more` not in JSON data"
        GlobalVars.se_sites.extend(data["items"])
        has_more = data["has_more"]
        page += 1
    return True, "OK"


def check_site_and_get_full_name(site):
    if len(GlobalVars.se_sites) == 0:
        refreshed, msg = refresh_sites()
        if not refreshed:
            return False, "Could not fetch sites: " + msg
    for item in GlobalVars.se_sites:
        full_name = item["site_url"].replace("http://", "")
        short_name = item["api_site_parameter"]
        if site == full_name or site == short_name:
            return True, full_name
    return False, "Could not find the given site."

# method to check whether a sentence is frequent of occurrence:


def is_frequent_sentence(sentence):
    no_punctuation = regex.sub(r"[^a-zA-Z0-9\s]", "", sentence).lower()
    merged_whitespace = regex.sub(r"\s+", " ", no_punctuation).strip()
    return merged_whitespace in GlobalVars.frequent_sentences


# methods to add/remove/check users on the "notification" list
# (that is, being pinged when Smokey reports something on a specific site)


def add_to_notification_list(user_id, chat_site, room_id, se_site):
    exists, site = check_site_and_get_full_name(se_site)
    if not exists:
        return -2, None
    t = (int(user_id), chat_site, int(room_id), site)
    if t in GlobalVars.notifications:
        return -1, None
    GlobalVars.notifications.append(t)
    with open("notifications.txt", "w") as f:
        pickle.dump(GlobalVars.notifications, f)
    return 0, site


def remove_from_notification_list(user_id, chat_site, room_id, se_site):
    t = (int(user_id), chat_site, int(room_id), se_site)
    if t not in GlobalVars.notifications:
        return False
    GlobalVars.notifications.remove(t)
    with open("notifications.txt", "w") as f:
        pickle.dump(GlobalVars.notifications, f)
    return True


def will_i_be_notified(user_id, chat_site, room_id, se_site):
    t = (int(user_id), chat_site, int(room_id), se_site)
    return t in GlobalVars.notifications


def get_user_ids_on_notification_list(chat_site, room_id, se_site):
    uids = []
    for t in GlobalVars.notifications:
        if t[1] == chat_site and t[2] == int(room_id) and t[3] == se_site:
            uids.append(t[0])
    return uids


def get_user_names_on_notification_list(chat_site, room_id, se_site, client):
    return [client.get_user(i).name for i in get_user_ids_on_notification_list(chat_site, room_id, se_site)]


def append_pings(original_message, names):
    if len(names) == 0:
        return original_message
    else:
        new_message = "{0} ({1})".format(original_message, " ".join(["@" + x.replace(" ", "") for x in names]))
        if len(new_message) > 500:
            return original_message
        else:
            return new_message


# methods to check if someone waited long enough to use another !!/report with multiple URLs
# (to avoid SmokeDetector's chat messages to be rate-limited too much)


def add_or_update_multiple_reporter(user_id, chat_host, time_integer):
    user_id = str(user_id)
    for i in range(len(GlobalVars.multiple_reporters)):
        if GlobalVars.multiple_reporters[i][0] == user_id and GlobalVars.multiple_reporters[i][1] == chat_host:
            GlobalVars.multiple_reporters[i] = (GlobalVars.multiple_reporters[i][0], GlobalVars.multiple_reporters[i][1], time_integer)
            return 1
    GlobalVars.multiple_reporters.append((user_id, chat_host, time_integer))


def can_report_now(user_id, chat_host):
    user_id = str(user_id)
    for reporter in GlobalVars.multiple_reporters:
        if reporter[0] == user_id and reporter[1] == chat_host:
            now = time.time()
            latest_report = reporter[2]
            can_report_again = latest_report + 30
            if now > can_report_again:
                return True, True
            else:
                return False, math.ceil(can_report_again - now)
    return True, True
