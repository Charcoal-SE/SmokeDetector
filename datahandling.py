import os
import pickle
from datetime import datetime
from globalvars import GlobalVars


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
    return user in GlobalVars.blacklisted_users


def is_ignored_post(postid_site_tuple):
    return postid_site_tuple in GlobalVars.ignored_posts


def is_auto_ignored_post(postid_site_tuple):
    for p in GlobalVars.auto_ignored_posts:
        if p[0] == postid_site_tuple[0] and p[1] == postid_site_tuple[1]:
            return True
    return False


def is_privileged(room_id_str, user_id_str):
    return room_id_str in GlobalVars.privileged_users and user_id_str in GlobalVars.privileged_users[room_id_str]

# methods to add/remove whitelisted/blacklisted users, ignored posts, ...


def add_whitelisted_user(user):
    if user in GlobalVars.whitelisted_users or user is None:
        return
    GlobalVars.whitelisted_users.append(user)
    with open("whitelistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.whitelisted_users, f)


def add_blacklisted_user(user):
    if user in GlobalVars.blacklisted_users or user is None:
        return
    GlobalVars.blacklisted_users.append(user)
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
    if user not in GlobalVars.blacklisted_users:
        return False
    GlobalVars.blacklisted_users.remove(user)
    with open("blacklistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.blacklisted_users, f)
    return True

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
    if fetched == "":
        return "The fetched part is empty. Please try another line count."
    return fetched
