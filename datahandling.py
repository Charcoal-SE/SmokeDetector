# coding=utf-8
import os
import pickle
import sys
import zlib
import base64
from datetime import datetime
import json
import time
import math
import threading
import copy
from pathlib import Path

import requests
# noinspection PyCompatibility
import regex

from globalvars import GlobalVars
import metasmoke
from parsing import api_parameter_from_link, post_id_from_link
import blacklists
from helpers import ErrorLogs, log, log_current_exception, redact_passwords
from tasks import Tasks

last_feedbacked = None
PICKLE_STORAGE = "pickles/"

queue_timings_data = list()
queue_timings_data_lock = threading.Lock()
FLUSH_TIMINGS_THRESHOLD = 128

SE_SITE_IDS_MAX_AGE_IN_SECONDS = 24 * 60 * 60
SE_SITE_IDS_MINIMUM_VALID_LENGTH = 200

bodyfetcher_max_ids_save_handle = None
bodyfetcher_max_ids_save_handle_lock = threading.Lock()
bodyfetcher_queue_save_handle = None
bodyfetcher_queue_save_handle_lock = threading.Lock()
recently_scanned_posts_save_handle = None
recently_scanned_posts_save_handle_lock = threading.Lock()


class Any:
    def __eq__(self, _):
        return True


def _save_problem_pickle(path):
    # Keep the most recent copy of a pickle file which had an error.
    errorpath = path + '-error'
    if os.path.isfile(errorpath):
        os.remove(errorpath)
    if os.path.isfile(path):
        os.rename(path, errorpath)


def create_pickle_storage_if_not_exist():
    Path(PICKLE_STORAGE).mkdir(exist_ok=True)


def load_pickle(path, encoding='utf-8'):
    create_pickle_storage_if_not_exist()
    newpath = os.path.join(PICKLE_STORAGE, path)
    if os.path.isfile(newpath):
        path = newpath
    try:
        with open(path, mode="rb") as f:
            return pickle.load(f, encoding=encoding)
    except UnicodeDecodeError:
        _save_problem_pickle(path)

        if "apicalls" in path.lower():
            return {}

        if "bodyfetcher" in path.lower():
            return {}
    except EOFError:
        _save_problem_pickle(path)
        raise
    except pickle.UnpicklingError as err:
        if 'pickle data was truncated' in str(err).lower():
            _save_problem_pickle(path)
        raise


def dump_pickle(path, item, protocol=pickle.HIGHEST_PROTOCOL):
    create_pickle_storage_if_not_exist()
    if os.path.isfile(path):  # Remove old one
        os.remove(path)
    newpath = os.path.join(PICKLE_STORAGE, path)
    with open(newpath, "wb") as f:
        pickle.dump(item, f, protocol=protocol)


def remove_pickle(path):
    try:
        os.remove(path)
    except OSError:
        pass
    path = os.path.join(PICKLE_STORAGE, path)
    try:
        os.remove(path)
    except OSError:
        pass


def has_pickle(path):
    newpath = os.path.join(PICKLE_STORAGE, path)
    return os.path.isfile(newpath) or os.path.isfile(path)


# methods to load files and filter data in them:
# load_blacklists() is defined in a separate module blacklists.py, though
def load_files():
    if has_pickle("falsePositives.p"):
        GlobalVars.false_positives = load_pickle("falsePositives.p", encoding='utf-8')
    if has_pickle("whitelistedUsers.p"):
        GlobalVars.whitelisted_users = load_pickle("whitelistedUsers.p", encoding='utf-8')
        if not isinstance(GlobalVars.whitelisted_users, set):
            GlobalVars.whitelisted_users = set(GlobalVars.whitelisted_users)
    if has_pickle("blacklistedUsers.p"):
        GlobalVars.blacklisted_users = load_pickle("blacklistedUsers.p", encoding='utf-8')
        if not isinstance(GlobalVars.blacklisted_users, dict):
            GlobalVars.blacklisted_users = {data[0]: data[1:] for data in GlobalVars.blacklisted_users}
    if has_pickle("ignoredPosts.p"):
        GlobalVars.ignored_posts = load_pickle("ignoredPosts.p", encoding='utf-8')
    if has_pickle("autoIgnoredPosts.p"):
        GlobalVars.auto_ignored_posts = load_pickle("autoIgnoredPosts.p", encoding='utf-8')
    if has_pickle("notifications.p"):
        GlobalVars.notifications = load_pickle("notifications.p", encoding='utf-8')
    if has_pickle("whyData.p"):
        GlobalVars.why_data = load_pickle("whyData.p", encoding='utf-8')
    # Switch from apiCalls.pickle to apiCalls.p
    # Correction was on 2020-11-02. Handling the apiCalls.pickle file should be able to be removed shortly thereafter.
    if has_pickle("apiCalls.pickle"):
        GlobalVars.api_calls_per_site = load_pickle("apiCalls.pickle", encoding='utf-8')
        # Remove the incorrectly named pickle file.
        remove_pickle("apiCalls.pickle")
        # Put the pickle in the "correct" file, from which it will be immediately reloaded.
        dump_pickle("apiCalls.p", GlobalVars.api_calls_per_site)
    if has_pickle("apiCalls.p"):
        GlobalVars.api_calls_per_site = load_pickle("apiCalls.p", encoding='utf-8')
    if has_pickle("bodyfetcherQueue.p"):
        GlobalVars.bodyfetcher.queue = load_pickle("bodyfetcherQueue.p", encoding='utf-8')
    if has_pickle("bodyfetcherMaxIds.p"):
        GlobalVars.bodyfetcher.previous_max_ids = load_pickle("bodyfetcherMaxIds.p", encoding='utf-8')
    if has_pickle("codePrivileges.p"):
        GlobalVars.code_privileged_users = load_pickle("codePrivileges.p", encoding='utf-8')
    if has_pickle("reasonWeights.p"):
        GlobalVars.reason_weights = load_pickle("reasonWeights.p", encoding='utf-8')
    if has_pickle("cookies.p"):
        GlobalVars.cookies = load_pickle("cookies.p", encoding='utf-8')
    if has_pickle("metasmokePostIds.p"):
        GlobalVars.metasmoke_ids = load_pickle("metasmokePostIds.p", encoding='utf-8')
    if has_pickle("ms_ajax_queue.p"):
        with metasmoke.Metasmoke.ms_ajax_queue_lock:
            metasmoke.Metasmoke.ms_ajax_queue = load_pickle("ms_ajax_queue.p")
            log("debug", "Loaded {} entries into ms_ajax_queue".format(len(metasmoke.Metasmoke.ms_ajax_queue)))
    if has_pickle("seSiteIds.p"):
        with GlobalVars.site_id_dict_lock:
            (GlobalVars.site_id_dict_timestamp,
             GlobalVars.site_id_dict_issues_into_chat_timestamp,
             GlobalVars.site_id_dict) = load_pickle("seSiteIds.p", encoding='utf-8')
            fill_site_id_dict_by_id_from_site_id_dict()
    if has_pickle("recentlyScannedPosts.p"):
        with GlobalVars.recently_scanned_posts_lock:
            GlobalVars.recently_scanned_posts = load_pickle("recentlyScannedPosts.p", encoding='utf-8')
    if has_pickle("postScanStats2.p"):
        with GlobalVars.PostScanStat.rw_lock:
            GlobalVars.PostScanStat.stats = load_pickle("postScanStats2.p", encoding='utf-8')
        GlobalVars.PostScanStat.reset('uptime')
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
    dump_pickle("autoIgnoredPosts.p", GlobalVars.auto_ignored_posts)


# methods to check whether a post/user is whitelisted/blacklisted/...

# noinspection PyMissingTypeHints
def is_false_positive(postid_site_tuple):
    return postid_site_tuple in GlobalVars.false_positives


# noinspection PyMissingTypeHints
def is_whitelisted_user(user):
    return user in GlobalVars.whitelisted_users


# noinspection PyMissingTypeHints
def is_blacklisted_user(user):
    return user in GlobalVars.blacklisted_users


def get_blacklisted_user_data(user):
    try:
        return (user,) + tuple(GlobalVars.blacklisted_users[user])
    except KeyError:
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
    # GlobalVars.code_privileged_users can now be a set, or may still be None.
    if GlobalVars.code_privileged_users is None:
        if len(GlobalVars.config_blacklisters) > 0:
            # Only change away from None if there are pre-configured blacklisters
            GlobalVars.code_privileged_users = set(GlobalVars.config_blacklisters)
    else:
        # Add the users in the config file, if any
        GlobalVars.code_privileged_users.update(GlobalVars.config_blacklisters)
    dump_pickle("codePrivileges.p", GlobalVars.code_privileged_users)


def is_code_privileged(site, user_id):
    if GlobalVars.code_privileged_users is None:
        update_code_privileged_users_list()

    try:
        # For now, disable the moderator override on code/blacklist changes
        return (site, user_id) in GlobalVars.code_privileged_users
    except TypeError:
        return False


def update_reason_weights():
    d = {'last_updated': datetime.utcnow().date()}
    items = metasmoke.Metasmoke.get_reason_weights()
    if not items:
        return  # No update
    for item in items:
        d[item['reason_name'].lower()] = item['weight']
    GlobalVars.reason_weights = d
    dump_pickle("reasonWeights.p", GlobalVars.reason_weights)


def resolve_ms_link(post_url):
    identifier = (api_parameter_from_link(post_url), post_id_from_link(post_url))
    if identifier in GlobalVars.metasmoke_ids:
        if isinstance(GlobalVars.metasmoke_ids[identifier], int):
            ms_url = (GlobalVars.metasmoke_host.rstrip("/") + "/post/{}").format(
                GlobalVars.metasmoke_ids[identifier])
            return ms_url
        else:
            del GlobalVars.metasmoke_ids[identifier]

    ms_posts = metasmoke.Metasmoke.get_post_bodies_from_ms(post_url)
    if not ms_posts:  # Empty
        ms_post_id = None
        ms_url = None
    else:
        ms_post_id = max([post['id'] for post in ms_posts])
        ms_url = (GlobalVars.metasmoke_host.rstrip("/") + "/post/{}").format(ms_post_id)
    GlobalVars.metasmoke_ids[identifier] = ms_post_id  # Store numeric IDs, strings are hard to handle
    dump_pickle("metasmokePostIds.p", GlobalVars.metasmoke_ids)
    return ms_url


# methods to add/remove whitelisted/blacklisted users, ignored posts, ...


# noinspection PyMissingTypeHints
def add_whitelisted_user(user):
    if user in GlobalVars.whitelisted_users or user is None:
        return
    GlobalVars.whitelisted_users.add(user)
    dump_pickle("whitelistedUsers.p", GlobalVars.whitelisted_users)


def add_blacklisted_user(user, message_url, post_url):
    if is_blacklisted_user(user) or user is None:
        return
    GlobalVars.blacklisted_users[user] = (message_url, post_url)
    dump_pickle("blacklistedUsers.p", GlobalVars.blacklisted_users)


def add_auto_ignored_post(postid_site_tuple):
    if postid_site_tuple is None or is_auto_ignored_post(postid_site_tuple):
        return
    GlobalVars.auto_ignored_posts.append(postid_site_tuple)
    dump_pickle("autoIgnoredPosts.p", GlobalVars.auto_ignored_posts)


def add_false_positive(site_post_id_tuple):
    if site_post_id_tuple is None or site_post_id_tuple in GlobalVars.false_positives:
        return
    GlobalVars.false_positives.append(site_post_id_tuple)
    dump_pickle("falsePositives.p", GlobalVars.false_positives)

    global last_feedbacked
    last_feedbacked = (site_post_id_tuple, time.time() + 60)


# noinspection PyMissingTypeHints
def add_ignored_post(postid_site_tuple):
    if postid_site_tuple is None or postid_site_tuple in GlobalVars.ignored_posts:
        return
    GlobalVars.ignored_posts.append(postid_site_tuple)
    dump_pickle("ignoredPosts.p", GlobalVars.ignored_posts)

    global last_feedbacked
    last_feedbacked = (postid_site_tuple, time.time() + 60)


def remove_blacklisted_user(user):
    blacklisted_user_data = get_blacklisted_user_data(user)
    if not blacklisted_user_data:
        return False
    GlobalVars.blacklisted_users.pop(blacklisted_user_data[0])
    dump_pickle("blacklistedUsers.p", GlobalVars.blacklisted_users)
    return True


# noinspection PyMissingTypeHints
def remove_whitelisted_user(user):
    if user not in GlobalVars.whitelisted_users:
        return False
    GlobalVars.whitelisted_users.remove(user)
    dump_pickle("whitelistedUsers.p", GlobalVars.whitelisted_users)
    return True


def add_why(site, post_id, why):
    key = site + "/" + str(post_id)
    why_data_tuple = (key, why)
    GlobalVars.why_data.append(why_data_tuple)
    filter_why()
    dump_pickle("whyData.p", GlobalVars.why_data)


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
    dump_pickle("apiCalls.p", GlobalVars.api_calls_per_site)


def clear_api_data():
    GlobalVars.api_calls_per_site = {}
    dump_pickle("apiCalls.p", GlobalVars.api_calls_per_site)


def schedule_store_bodyfetcher_queue():
    global bodyfetcher_queue_save_handle
    with bodyfetcher_queue_save_handle_lock:
        if bodyfetcher_queue_save_handle:
            bodyfetcher_queue_save_handle.cancel()
        bodyfetcher_queue_save_handle = Tasks.do(store_bodyfetcher_queue)


def store_bodyfetcher_queue():
    with GlobalVars.bodyfetcher.queue_lock:
        dump_pickle("bodyfetcherQueue.p", GlobalVars.bodyfetcher.queue)


def schedule_store_bodyfetcher_max_ids():
    global bodyfetcher_max_ids_save_handle
    with bodyfetcher_max_ids_save_handle_lock:
        if bodyfetcher_max_ids_save_handle:
            bodyfetcher_max_ids_save_handle.cancel()
        bodyfetcher_max_ids_save_handle = Tasks.do(store_bodyfetcher_max_ids)


def store_bodyfetcher_max_ids():
    with bodyfetcher_max_ids_save_handle_lock:
        if bodyfetcher_max_ids_save_handle:
            bodyfetcher_max_ids_save_handle.cancel()
    with GlobalVars.bodyfetcher.max_ids_lock:
        max_ids_copy = GlobalVars.bodyfetcher.previous_max_ids.copy()
    dump_pickle("bodyfetcherMaxIds.p", max_ids_copy)


def store_ms_ajax_queue():
    with metasmoke.Metasmoke.ms_ajax_queue_lock:
        dump_pickle("ms_ajax_queue.p", metasmoke.Metasmoke.ms_ajax_queue)


def add_queue_timing_data(site, times_in_queue):
    global queue_timings_data
    new_times = ["{} {}".format(site, time_in_queue) for time_in_queue in times_in_queue]
    with queue_timings_data_lock:
        queue_timings_data.extend(new_times)
        queue_length = len(queue_timings_data)
    if queue_length >= FLUSH_TIMINGS_THRESHOLD:
        flush_queue_timings_data()


def flush_queue_timings_data():
    global queue_timings_data
    # Use .txt for cross platform compatibility
    create_pickle_storage_if_not_exist()
    with queue_timings_data_lock:
        with open("pickles/bodyfetcherQueueTimings.txt", mode="a", encoding="utf-8") as stat_file:
            stat_file.write("\n".join(queue_timings_data) + "\n")
        queue_timings_data = list()


def schedule_store_recently_scanned_posts():
    global recently_scanned_posts_save_handle
    with recently_scanned_posts_save_handle_lock:
        if recently_scanned_posts_save_handle:
            recently_scanned_posts_save_handle.cancel()
        recently_scanned_posts_save_handle = Tasks.do(store_recently_scanned_posts)


def store_recently_scanned_posts():
    # While using a copy to avoid holding the lock while storing is generally desired,
    # the expectation is that this will only be stored when shutting down.
    with GlobalVars.recently_scanned_posts_lock:
        with recently_scanned_posts_save_handle_lock:
            if recently_scanned_posts_save_handle:
                recently_scanned_posts_save_handle.cancel()
        dump_pickle("recentlyScannedPosts.p", GlobalVars.recently_scanned_posts)


def store_post_scan_stats():
    with GlobalVars.PostScanStat.rw_lock:
        stats = copy.deepcopy(GlobalVars.PostScanStat.stats)
    dump_pickle("postScanStats2.p", stats)


# methods that help avoiding reposting alerts:


def append_to_latest_questions(host, post_id, title):
    with GlobalVars.latest_questions_lock:
        GlobalVars.latest_questions.insert(0, (host, str(post_id), title))
        if len(GlobalVars.latest_questions) > 50:
            GlobalVars.latest_questions.pop()


# noinspection PyMissingTypeHints
def has_already_been_posted(host, post_id, title):
    with GlobalVars.latest_questions_lock:
        for post in GlobalVars.latest_questions:
            if post[0] == host and post[1] == str(post_id):
                return True
        return False


# method to get data from the error log:


# noinspection PyUnusedLocal
def fetch_lines_from_error_log(count):
    if not os.path.isfile("errorLogs.db"):
        return "The error log database does not exist."
    if count <= 0:
        return "Please request an exception count greater than zero."
    logs = ErrorLogs.fetch_last(count)
    s = '\n'.join([
        "### {2} on {0} at {1}Z: {3}\n{4}".format(
            GlobalVars.location, datetime.utcfromtimestamp(time).isoformat()[:-7],
            name, message, tb)
        for time, name, message, tb in logs])
    if s:
        return redact_passwords(s)
    else:
        return "The fetched log is empty."


# method to check whether a SE site exists:


# noinspection PyMissingTypeHints
def refresh_sites():
    has_more = True
    page = 1
    url = "https://api.stackexchange.com/2.2/sites"
    while has_more:
        params = {
            'filter': '!)Qpa1bTB_jCkeaZsqiQ8pDwI',
            'key': 'IAkbitmze4B8KpacUfLqkw((',
            'page': page,
            'pagesize': 500
        }
        response = requests.get(url, params=params)

        data = response.json()
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
#
# The list of notifications is stored in GlobalVars.notifications.
# It is a tuple with the following format:
# notification_tuple = (int(user_id), chat_site, int(room_id), se_site, always_ping)
# always_ping is used to indicate if the user should always be pinged, or only pinged
# when they are present in the room.

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
    dump_pickle("notifications.p", GlobalVars.notifications)
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
    dump_pickle("notifications.p", GlobalVars.notifications)
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
    non_always_ids = []
    for user_id, always in get_user_ids_on_notification_list(chat_site, room_id, se_site):
        if always:
            try:
                names.append(client.get_user(user_id).name)
            except Exception:
                # The user is probably deleted, or we're having communication problems with chat.
                log_current_exception()
                log('warn', 'ChatExchange failed to get user for a report notification. '
                            'See Error log for more details. Tried client.host: '
                            '{}:: user_id: {}:: chat_site: {}'.format(client.host, user_id, chat_site))
        else:
            non_always_ids.append(user_id)

    if non_always_ids:
        # If there are no users who have requested to be pinged only when present in the room, then we
        # don't fetch the current_users list for this room (doing so makes an HTTPS request to chat).
        # If people use the feature of not being pinged when not in the room for high-traffic rooms, then
        # we should implement a cache for the current_users in each room, so we're not fetching it on each
        # of a large number of messages/reports. If this feature is only used on low traffic rooms, then
        # we don't really need a cache.
        # Note: for a considerable time (years), we fetched the current users on *every* report, so it is
        # something SD can do. It's just better if we don't have to have the extra request for *every*
        # report posted into a high-traffic room.
        try:
            current_users = client._br.get_current_users_in_room(room_id)
        except Exception:
            # ChatExchange had a problem getting the current users. This shouldn't be allowed to
            # cause us to crash, as it's on the path we take for going into standby.
            # It should be noted that this *could* be caused by a discontinuity between room_id and
            # client.
            log_current_exception()
            log('warn', 'ChatExchange failed to get current users. See Error log for more details. Tried '
                        'client.host: {}:: room: {}:: passed chat_site: {}'.format(client.host, room_id, chat_site))
            current_users = []

        for i in non_always_ids:
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
    try:
        ms_posts = metasmoke.Metasmoke.get_post_bodies_from_ms(post_url)
        if not ms_posts:
            return False

        return any(post['body'] == post_content for post in ms_posts)
    except (requests.exceptions.ConnectionError, ValueError):
        return False  # MS is down, so assume it is not bumped

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


def dump_cookies():
    dump_pickle("cookies.p", GlobalVars.cookies)


class SmokeyTransfer:
    HEADER = "-----BEGIN SMOKEY DATA BLOCK-----"
    ENDING = "-----END SMOKEY DATA BLOCK-----"

    ITEMS = [
        # (dict_key, object, attr, type, post_processing)
        ('blacklisted_users', GlobalVars, 'blacklisted_users', None, None),
        ('whitelisted_users', GlobalVars, 'whitelisted_users', None, None),
        ('ignored_posts', GlobalVars, 'ignored_posts', None, None),
        ('notifications', GlobalVars, 'notifications', None, None),
    ]

    @classmethod
    def dump(cls):
        # Trust Python's GIL here
        data = {'_metadata': {
            'time': time.time(),
            'location': GlobalVars.location,
            'rev': GlobalVars.commit.id_full,
            'lengths': {},  # can be used for validation
        }}  # some metadata, in case they're useful
        for item_info in cls.ITEMS:
            key, obj, attr, obj_type, _ = item_info
            item = getattr(obj, attr)
            data[key] = item
            try:
                length = len(item)
            except TypeError:
                length = None  # len() is inapplicable
            data['_metadata']['lengths'][key] = length

        # hopefully the pickle won't be more than a few MiB
        # For backward compatibility, we use protocol=4, which was introduced in Python 3.4.
        # protocol=5 was introduced with Python 3.8, so we can move to that once we no longer
        # support Python 3.7.
        raw_data = pickle.dumps(data, protocol=4)
        # let's save some traffic
        z_data = zlib.compress(raw_data, 9)
        # need to transfer via chat, so text only
        b64_s = base64.b64encode(z_data).decode('ascii')

        chunk_size = 64  # The same value as GnuPG armored output
        s = "{}\n\n{}\n\n{}".format(
            cls.HEADER,
            '\n'.join([b64_s[i:i + chunk_size] for i in range(0, len(b64_s), chunk_size)]),
            cls.ENDING)
        return s, data['_metadata']

    @classmethod
    def load(cls, s, merge=False):
        try:
            # While it generates a blank line after the header and before the ending,
            # it should also accept data that does not contain the blank lines
            lbound, rbound = s.index(cls.HEADER + "\n"), s.rindex("\n" + cls.ENDING)
            s = s[lbound + len(cls.HEADER):rbound].strip()
        except ValueError:
            raise ValueError("Invalid data (invalid header or ending)")
        s = ''.join(s.split())  # Clear whitespaces

        try:
            z_data = base64.b64decode(s.encode('ascii'))
            raw_data = zlib.decompress(z_data)
            data = pickle.loads(raw_data, encoding='utf-8')
            if type(data) is not dict:
                raise ValueError("Invalid data (data type is not dict)")

            # happy extracting
            warnings = []
            for item_info in cls.ITEMS:
                key, obj, attr, obj_type, proc = item_info
                if key not in data:
                    continue  # Allow partial transfer
                item = data[key]
                try:
                    length = len(item)
                except TypeError:
                    length = None
                if length != data['_metadata']['lengths'][key]:
                    warnings.append("Length of {!r} mismatch (recorded {}, actual {})".format(
                        key, data['_metadata']['lengths'][key], length))
                setattr(obj, attr, item)
            if warnings:
                raise Warning("Warning: " + ', '.join(warnings))
        except (ValueError, zlib.error) as e:
            raise ValueError(str(e)) from None


def store_site_id_dict():
    with GlobalVars.site_id_dict_lock:
        to_dump = (GlobalVars.site_id_dict_timestamp,
                   GlobalVars.site_id_dict_issues_into_chat_timestamp,
                   GlobalVars.site_id_dict.copy())
    dump_pickle("seSiteIds.p", to_dump)


def fill_site_id_dict_by_id_from_site_id_dict():
    GlobalVars.site_id_dict_by_id = {site_id: site for site, site_id in GlobalVars.site_id_dict.items()}


def refresh_site_id_dict():
    message = requests.get('https://meta.stackexchange.com/topbar/site-switcher/all-pinnable-sites')
    data = json.loads(message.text)
    site_ids_dict = {entry['hostname']: entry['siteid'] for entry in data}
    if len(site_ids_dict) >= SE_SITE_IDS_MINIMUM_VALID_LENGTH:
        with GlobalVars.site_id_dict_lock:
            GlobalVars.site_id_dict = site_ids_dict
            fill_site_id_dict_by_id_from_site_id_dict()
            GlobalVars.site_id_dict_timestamp = time.time()


def is_se_site_id_list_length_valid():
    with GlobalVars.site_id_dict_lock:
        to_return = len(GlobalVars.site_id_dict) >= SE_SITE_IDS_MINIMUM_VALID_LENGTH
    return to_return


def is_se_site_id_list_out_of_date():
    return GlobalVars.site_id_dict_timestamp < time.time() - SE_SITE_IDS_MAX_AGE_IN_SECONDS


def refresh_site_id_dict_if_needed_and_get_issues():
    issues = []
    if not is_se_site_id_list_length_valid() or is_se_site_id_list_out_of_date():
        try:
            refresh_site_id_dict()
        except Exception:
            # We ignore any problems with getting or refreshing the list of SE sites, as we handle it by
            # testing to see if we have valid data (i.e. SD doesn't need to fail for an exception here).
            log_current_exception()
            issues.append("An exception occurred when trying to get the SE site ID list."
                          " See the error log for details.")
        if is_se_site_id_list_length_valid():
            store_site_id_dict()
    if is_se_site_id_list_out_of_date():
        issues.insert(0, "The site ID list is more than a day old.")
    if not is_se_site_id_list_length_valid():
        with GlobalVars.site_id_dict_lock:
            issues.insert(0, "The SE site ID list has "
                             "{} entries, which isn't considered valid.".format(len(GlobalVars.site_id_dict)))
    return issues
