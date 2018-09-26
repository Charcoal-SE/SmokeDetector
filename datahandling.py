# coding=utf-8
import os
# noinspection PyPep8Naming
import pickle
from datetime import datetime
import metasmoke
import requests
import json
import time
import math
# noinspection PyCompatibility
import regex

from globalvars import GlobalVars
import blacklists

last_feedbacked = None
PICKLE_STORAGE = "pickles/"


class Any:
    def __eq__(self, _):
        return True


def _load_pickle(path, encoding='utf-8'):
    newpath = os.path.join(PICKLE_STORAGE, path)
    if os.path.isfile(newpath):
        path = newpath
    with open(path, mode="rb") as f:
        try:
            return pickle.load(f, encoding=encoding)
        except UnicodeDecodeError:
            os.remove(path)

            if "apicalls" in path.lower():
                return {}

            if "bodyfetcher" in path.lower():
                return {}
        except EOFError:
            os.remove(path)
            raise
        except pickle.UnpicklingError as err:
            if 'pickle data was truncated' in str(err).lower():
                os.remove(path)
            raise


def _dump_pickle(path, item, protocol=pickle.HIGHEST_PROTOCOL):
    if not os.path.isdir(PICKLE_STORAGE):
        os.mkdir(PICKLE_STORAGE)
    if os.path.isfile(path):  # Remove old one
        os.remove(path)
    newpath = os.path.join(PICKLE_STORAGE, path)
    with open(newpath, "wb") as f:
        pickle.dump(item, f, protocol=protocol)


def _remove_pickle(path):
    try:
        os.remove(path)
    except OSError:
        pass
    path = os.path.join(PICKLE_STORAGE, path)
    try:
        os.remove(path)
    except OSError:
        pass


def _has_pickle(path):
    newpath = os.path.join(PICKLE_STORAGE, path)
    return os.path.isfile(newpath) or os.path.isfile(path)


# methods to load files and filter data in them:
# load_blacklists() is defined in a separate module blacklists.py, though
def load_files():
    if _has_pickle("falsePositives.p"):
        GlobalVars.false_positives = _load_pickle("falsePositives.p", encoding='utf-8')
    if _has_pickle("whitelistedUsers.p"):
        GlobalVars.whitelisted_users = _load_pickle("whitelistedUsers.p", encoding='utf-8')
    if _has_pickle("blacklistedUsers.p"):
        GlobalVars.blacklisted_users = _load_pickle("blacklistedUsers.p", encoding='utf-8')
    if _has_pickle("ignoredPosts.p"):
        GlobalVars.ignored_posts = _load_pickle("ignoredPosts.p", encoding='utf-8')
    if _has_pickle("autoIgnoredPosts.p"):
        GlobalVars.auto_ignored_posts = _load_pickle("autoIgnoredPosts.p", encoding='utf-8')
    if _has_pickle("notifications.p"):
        GlobalVars.notifications = _load_pickle("notifications.p", encoding='utf-8')
    if _has_pickle("whyData.p"):
        GlobalVars.why_data = _load_pickle("whyData.p", encoding='utf-8')
    if _has_pickle("apiCalls.p"):
        GlobalVars.api_calls_per_site = _load_pickle("apiCalls.p", encoding='utf-8')
    if _has_pickle("bodyfetcherQueue.p"):
        GlobalVars.bodyfetcher.queue = _load_pickle("bodyfetcherQueue.p", encoding='utf-8')
    if _has_pickle("bodyfetcherMaxIds.p"):
        GlobalVars.bodyfetcher.previous_max_ids = _load_pickle("bodyfetcherMaxIds.p", encoding='utf-8')
    if _has_pickle("bodyfetcherQueueTimings.p"):
        GlobalVars.bodyfetcher.queue_timings = _load_pickle("bodyfetcherQueueTimings.p", encoding='utf-8')
    if _has_pickle("codePrivileges.p"):
        GlobalVars.code_privileged_users = _load_pickle("codePrivileges.p", encoding='utf-8')
    if _has_pickle("reasonWeights.p"):
        GlobalVars.reason_weights = _load_pickle("reasonWeights.p", encoding='utf-8')
    blacklists.load_blacklists()


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
    _dump_pickle("autoIgnoredPosts.p", GlobalVars.auto_ignored_posts)


# methods to check whether a post/user is whitelisted/blacklisted/...

# noinspection PyMissingTypeHints
def is_false_positive(postid_site_tuple):
    return postid_site_tuple in GlobalVars.false_positives


# noinspection PyMissingTypeHints
def is_whitelisted_user(user):
    return user in GlobalVars.whitelisted_users


# noinspection PyMissingTypeHints
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


# noinspection PyMissingTypeHints
def is_ignored_post(postid_site_tuple):
    return postid_site_tuple in GlobalVars.ignored_posts


# noinspection PyMissingTypeHints
def is_auto_ignored_post(postid_site_tuple):
    for p in GlobalVars.auto_ignored_posts:
        if p[0] == postid_site_tuple[0] and p[1] == postid_site_tuple[1]:
            return True
    return False


def update_code_privileged_users_list():
    metasmoke.Metasmoke.update_code_privileged_users_list()
    _dump_pickle("codePrivileges.p", GlobalVars.code_privileged_users)


def is_code_privileged(site, user_id):
    if GlobalVars.code_privileged_users is None:
        update_code_privileged_users_list()

    # For now, disable the moderator override on code/blacklist changes
    return (site, user_id) in GlobalVars.code_privileged_users


def update_reason_weights():
    d = {'last_updated': datetime.utcnow().date()}
    items = metasmoke.Metasmoke.get_reason_weights()
    if not items:
        return  # No update
    for item in items:
        d[item['reason_name'].lower()] = item['weight']
    GlobalVars.reason_weights = d
    _dump_pickle("reasonWeights.p", GlobalVars.reason_weights)

# methods to add/remove whitelisted/blacklisted users, ignored posts, ...


# noinspection PyMissingTypeHints
def add_whitelisted_user(user):
    if user in GlobalVars.whitelisted_users or user is None:
        return
    GlobalVars.whitelisted_users.append(user)
    _dump_pickle("whitelistedUsers.p", GlobalVars.whitelisted_users)


def add_blacklisted_user(user, message_url, post_url):
    if is_blacklisted_user(user) or user is None:
        return
    GlobalVars.blacklisted_users.append((user, message_url, post_url))
    _dump_pickle("blacklistedUsers.p", GlobalVars.blacklisted_users)


def add_auto_ignored_post(postid_site_tuple):
    if postid_site_tuple is None or is_auto_ignored_post(postid_site_tuple):
        return
    GlobalVars.auto_ignored_posts.append(postid_site_tuple)
    _dump_pickle("autoIgnoredPosts.p", GlobalVars.auto_ignored_posts)


def add_false_positive(site_post_id_tuple):
    if site_post_id_tuple is None or site_post_id_tuple in GlobalVars.false_positives:
        return
    GlobalVars.false_positives.append(site_post_id_tuple)
    _dump_pickle("falsePositives.p", GlobalVars.false_positives)

    global last_feedbacked
    last_feedbacked = (site_post_id_tuple, time.time() + 60)


# noinspection PyMissingTypeHints
def add_ignored_post(postid_site_tuple):
    if postid_site_tuple is None or postid_site_tuple in GlobalVars.ignored_posts:
        return
    GlobalVars.ignored_posts.append(postid_site_tuple)
    _dump_pickle("ignoredPosts.p", GlobalVars.ignored_posts)

    global last_feedbacked
    last_feedbacked = (postid_site_tuple, time.time() + 60)


def remove_blacklisted_user(user):
    blacklisted_user_data = get_blacklisted_user_data(user)
    if not blacklisted_user_data:
        return False
    GlobalVars.blacklisted_users.remove(blacklisted_user_data)
    _dump_pickle("blacklistedUsers.p", GlobalVars.blacklisted_users)
    return True


# noinspection PyMissingTypeHints
def remove_whitelisted_user(user):
    if user not in GlobalVars.whitelisted_users:
        return False
    GlobalVars.whitelisted_users.remove(user)
    _dump_pickle("whitelistedUsers.p", GlobalVars.whitelisted_users)
    return True


def add_why(site, post_id, why):
    key = site + "/" + str(post_id)
    why_data_tuple = (key, why)
    GlobalVars.why_data.append(why_data_tuple)
    filter_why()
    _dump_pickle("whyData.p", GlobalVars.why_data)


def get_why(site, post_id):
    key = site + "/" + str(post_id)
    for post in GlobalVars.why_data:
        if post[0] == key:
            return post[1]
    return None


def filter_why(max_size=50):
    GlobalVars.why_data = GlobalVars.why_data[-max_size:]


def add_post_site_id_link(post_site_id, question_id):
    GlobalVars.post_site_id_to_question[post_site_id] = question_id


def get_post_site_id_link(post_site_id):
    if post_site_id in GlobalVars.post_site_id_to_question:
        return GlobalVars.post_site_id_to_question[post_site_id]
    return None


def add_or_update_api_data(site):
    if site in GlobalVars.api_calls_per_site:
        GlobalVars.api_calls_per_site[site] += 1
    else:
        GlobalVars.api_calls_per_site[site] = 1
    _dump_pickle("apiCalls.pickle", GlobalVars.api_calls_per_site)


def clear_api_data():
    GlobalVars.api_calls_per_site = {}
    _dump_pickle("apiCalls.pickle", GlobalVars.api_calls_per_site)


def store_bodyfetcher_queue():
    _dump_pickle("bodyfetcherQueue.p", GlobalVars.bodyfetcher.queue)


def store_bodyfetcher_max_ids():
    _dump_pickle("bodyfetcherMaxIds.p", GlobalVars.bodyfetcher.previous_max_ids)


def store_queue_timings():
    _dump_pickle("bodyfetcherQueueTimings.p", GlobalVars.bodyfetcher.queue_timings)


# methods that help avoiding reposting alerts:


def append_to_latest_questions(host, post_id, title):
    GlobalVars.latest_questions.insert(0, (host, str(post_id), title))
    if len(GlobalVars.latest_questions) > 50:
        GlobalVars.latest_questions.pop()


# noinspection PyMissingTypeHints
def has_already_been_posted(host, post_id, title):
    for post in GlobalVars.latest_questions:
        if post[0] == host and post[1] == str(post_id):
            return True
    return False


# method to get data from the error log:


# noinspection PyUnusedLocal
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


# noinspection PyMissingTypeHints
def refresh_sites():
    has_more = True
    page = 1
    while has_more:
        response = requests.get("https://api.stackexchange.com/2.2/sites"
                                "?filter=!%29Qpa1bTB_jCkeaZsqiQ8pDwI&pagesize=500&page=" + str(page) +
                                "&key=IAkbitmze4B8KpacUfLqkw((")
        data = json.loads(response.text)
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


# noinspection PyMissingTypeHints
def check_site_and_get_full_name(site):
    if len(GlobalVars.se_sites) == 0:
        refreshed, msg = refresh_sites()
        if not refreshed:
            return False, "Could not fetch sites: " + msg
    for item in GlobalVars.se_sites:
        full_name = regex.sub(r'https?://', '', item['site_url'])
        short_name = item["api_site_parameter"]
        if site == full_name or site == short_name:
            return True, full_name
    return False, "Could not find the given site."


# methods to add/remove/check users on the "notification" list
# (that is, being pinged when Smokey reports something on a specific site)

# noinspection PyMissingTypeHints
def add_to_notification_list(user_id, chat_site, room_id, se_site, always_ping=True):
    if se_site[0] != "/":
        exists, se_site = check_site_and_get_full_name(se_site)
        if not exists:
            return -2, None
    notification_tuple = (int(user_id), chat_site, int(room_id), se_site, Any())
    if notification_tuple in GlobalVars.notifications:
        return -1, None
    GlobalVars.notifications.append((int(user_id), chat_site, int(room_id), se_site, always_ping))
    _dump_pickle("notifications.p", GlobalVars.notifications)
    return 0, se_site


# noinspection PyMissingTypeHints
def remove_from_notification_list(user_id, chat_site, room_id, se_site):
    if se_site[0] != "/":
        exists, se_site = check_site_and_get_full_name(se_site)
        if not exists:
            return False
    notification_tuple = (int(user_id), chat_site, int(room_id), se_site, Any())
    if notification_tuple not in GlobalVars.notifications:
        return False
    GlobalVars.notifications.remove(notification_tuple)
    _dump_pickle("notifications.p", GlobalVars.notifications)
    return True


# noinspection PyMissingTypeHints
def will_i_be_notified(user_id, chat_site, room_id, se_site):
    exists, site = check_site_and_get_full_name(se_site)
    if not exists:
        return False
    notification_tuple = (int(user_id), chat_site, int(room_id), site, Any())
    return notification_tuple in GlobalVars.notifications


# noinspection PyMissingTypeHints
def remove_all_from_notification_list(user_id):
    user_id = int(user_id)
    my_notifications = []

    for notification in GlobalVars.notifications:
        if notification[0] == user_id:
            my_notifications.append(notification[:4])

    for notification in my_notifications:
        remove_from_notification_list(*notification)


def get_all_notification_sites(user_id, chat_site, room_id):
    sites = []
    for notification in GlobalVars.notifications:
        if notification[0] == int(user_id) and notification[1] == chat_site and notification[2] == int(room_id):
            sites.append(notification[3])
    return sorted(sites)


def get_user_ids_on_notification_list(chat_site, room_id, se_site):
    uids = []
    for notification in GlobalVars.notifications:
        if notification[1] == chat_site and notification[2] == int(room_id) and notification[3] == se_site:
            uids.append((notification[0], notification[4]))
    return uids


def get_user_names_on_notification_list(chat_site, room_id, se_site, client):
    names = []
    current_users = client._br.get_current_users_in_room(room_id)

    for i, always in get_user_ids_on_notification_list(chat_site, room_id, se_site):
        if always:
            names.append(client.get_user(i).name)
        else:
            try:
                names.append(current_users[current_users.index((i, Any()))][1])
            except ValueError:  # user not in room
                pass

    return names


# noinspection PyMissingTypeHints
def append_pings(original_message, names):
    if len(names) != 0:
        new_message = u"{0} ({1})".format(original_message, " ".join("@" + x.replace(" ", "") for x in names))
        if len(new_message) <= 500:
            return new_message
    return original_message

# method to check if a post has been bumped by Community


def has_community_bumped_post(post_url, post_content):
    if GlobalVars.metasmoke_key is not None and GlobalVars.metasmoke_host is not None:
        try:
            ms_posts = metasmoke.Metasmoke.get_post_bodies_from_ms(post_url)
            if not ms_posts:
                return False

            return any(post['body'] == post_content for post in ms_posts)
        except (requests.exceptions.ConnectionError, ValueError):
            return False  # MS is down, so assume it is not bumped
    return False

# methods to check if someone waited long enough to use another !!/report with multiple URLs
# (to avoid SmokeDetector's chat messages to be rate-limited too much)


def add_or_update_multiple_reporter(user_id, chat_host, time_integer):
    user_id = str(user_id)
    for i in range(len(GlobalVars.multiple_reporters)):
        if GlobalVars.multiple_reporters[i][0] == user_id and GlobalVars.multiple_reporters[i][1] == chat_host:
            GlobalVars.multiple_reporters[i] = (GlobalVars.multiple_reporters[i][0],
                                                GlobalVars.multiple_reporters[i][1], time_integer)
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
            return False, math.ceil(can_report_again - now)
    return True, True
