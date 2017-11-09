# coding=utf-8

import platform
import time
import json
from datetime import datetime
from threading import Lock

import regex
import requests
from requests.auth import HTTPBasicAuth

from urllib.parse import quote_plus
if 'windows' in str(platform.platform()).lower():
    # noinspection PyPep8Naming
    from classes import Git as git
else:
    from sh import git

from helpers import log
from globalvars import GlobalVars


# noinspection PyRedundantParentheses,PyClassHasNoInit,PyBroadException
class GitManager:

    gitmanager_lock = Lock()

    @classmethod
    def add_to_blacklist(cls, **kwargs):
        blacklist = kwargs.get("blacklist", "")
        item_to_blacklist = kwargs.get("item_to_blacklist", "")
        username = kwargs.get("username", "")
        chat_profile_link = kwargs.get("chat_profile_link", "http://chat.stackexchange.com/users")
        code_permissions = kwargs.get("code_permissions", False)

        # Make sure git credentials are set up
        if git.config("--get", "user.name", _ok_code=[0, 1]) == "":
            return (False, "Tell someone to run `git config user.name \"SmokeDetector\"`")

        if git.config("--get", "user.email", _ok_code=[0, 1]) == "":
            return (False, "Tell someone to run `git config user.email \"smokey@erwaysoftware.com\"`")

        if blacklist == "":
            # If we broke the code, and this isn't assigned, error out before doing anything, but do
            # so gracefully with a nice error message.
            return (False, "Programming Error - Critical information missing for GitManager: blacklist")

        if item_to_blacklist == "":
            # If we broke the code, and this isn't assigned, error out before doing anything, but do
            # so gracefully with a nice error message.
            return (False, "Programming Error - Critical information missing for GitManager: item_to_blacklist")

        item_to_blacklist = item_to_blacklist.replace("\s", " ")

        if blacklist == "website":
            blacklist_file_name = "blacklisted_websites.txt"
            ms_search_option = "&body="
        elif blacklist == "keyword":
            blacklist_file_name = "bad_keywords.txt"
            ms_search_option = "&body="
        elif blacklist == "username":
            blacklist_file_name = "blacklisted_usernames.txt"
            ms_search_option = "&username="
        elif blacklist == "watch_keyword":
            blacklist_file_name = "watched_keywords.txt"
            ms_search_option = "&body="
        else:
            # Just checking all bases, but blacklist_file_name *might* have empty value
            # if we don't address it here.
            return (False, "Invalid blacklist type specified, something has broken badly!")

        try:
            cls.gitmanager_lock.acquire()

            # Fetch remote changes and checkout into detached head
            git.fetch("origin", "master")
            git.checkout("origin/master")

            # Set up parameters for watch vs blacklist
            if blacklist_file_name in ['watched_keywords.txt']:
                op = 'watch'
                now = datetime.now().strftime('%s')
                item = item_to_blacklist
                item_to_blacklist = "\t".join([now, username, item])
                item_regex = regex.compile(r'\t\L<item>$', item=[item])
            else:
                op = 'blacklist'
                item = item_to_blacklist
                item_regex = regex.compile(r'^\L<item>$', item=[item])

            # Prevent duplicates
            with open(blacklist_file_name, "r") as blacklist_file:
                for lineno, line in enumerate(blacklist_file, 1):
                    if item_regex.search(line):
                        return (False, '{0} already {1}ed on {2} line {3}'.format(
                            item, op, blacklist_file_name, lineno))

            # Remove from watch if watched
            write_lines = False
            if blacklist_file_name not in ['watched_keywords.txt']:
                watch_lines = []
                watch_regex = regex.compile(r'\t\L<item>$', item=[item])
                with open('watched_keywords.txt', 'r') as watch_file:
                    for lineno, line in enumerate(watch_file, 1):
                        if watch_regex.search(line):
                            write_lines = True
                            continue
                        watch_lines.append(line)
                if write_lines:
                    with open('watched_keywords.txt', 'w') as watch_file:
                        for line in watch_lines:
                            watch_file.write(line)

            # Add item to file
            with open(blacklist_file_name, "a+") as blacklist_file:
                last_character = blacklist_file.read()[-1:]
                if last_character not in ["", "\n"]:
                    blacklist_file.write("\n")
                blacklist_file.write(item_to_blacklist + "\n")

            git.add(blacklist_file_name)
            if write_lines:
                git.add('watched_keywords.txt')

            git.commit("--author='SmokeDetector <smokey@erwaysoftware.com>'",
                       "-m", u"Auto {0} of {1} by {2} --autopull".format(op, item, username))

            if code_permissions:
                git.push("origin", "HEAD:master")
            else:
                # Checkout a new branch from detached HEAD
                branch = "auto-blacklist-{0}".format(str(time.time()))
                git.checkout("-b", branch)

                git.push("origin", branch)

                if GlobalVars.github_username is None or GlobalVars.github_password is None:
                    return (False, "Tell someone to set a GH password")

                payload = {"title": u"{0}: {1} {2}".format(username, op.title(), item),
                           "body": u"[{0}]({1}) requests the {2} of the {3} {4}. See the Metasmoke search [here]"
                                   "(https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93{5}{6}) and the "
                                   "Stack Exchange search [here](https://stackexchange.com/search?q=%22{6}%22).\n"
                                   u"<!-- METASMOKE-BLACKLIST-{7} {4} -->".format(
                                       username, chat_profile_link, op, blacklist,
                                       item, ms_search_option,
                                       quote_plus(item.replace("\\W", " ").replace("\\.", ".")),
                                       blacklist.upper()),
                           "head": branch,
                           "base": "master"}
                response = requests.post("https://api.github.com/repos/Charcoal-SE/SmokeDetector/pulls",
                                         auth=HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password),
                                         data=json.dumps(payload))
                log('debug', response.json())
                try:
                    url = response.json()["html_url"]
                    return (True,
                            "You don't have code privileges, but I've [created PR#{1} for you]({0}).".format(
                                url, url.split('/')[-1]))
                except KeyError:
                    # Error capture/checking for any "invalid" GH reply without an 'html_url' item,
                    # which will throw a KeyError.
                    if "bad credentials" in str(response.json()['message']).lower():
                        # Capture the case when GH credentials are bad or invalid
                        return (False, "Something is wrong with the GH credentials, tell someone to check them.")
                    else:
                        # Capture any other invalid response cases.
                        return (False, "A bad or invalid reply was received from GH, the message was: %s" %
                                response.json()['message'])
        except Exception:
            return (False, "Git functions failed for unspecified reasons.")
        finally:
            # Always return to `deploy` branch when done with anything.
            git.checkout("deploy")

            cls.gitmanager_lock.release()

        if op == 'blacklist':
            return (True, "Blacklisted {0}".format(item))
        elif op == 'watch':
            return (True, "Added {0} to watchlist".format(item))

    @staticmethod
    def current_git_status():
        if 'windows' in platform.platform().lower():
            return git.status_stripped()
        else:
            return git("-c", "color.status=false", "status")

    @staticmethod
    def get_remote_diff():
        git.fetch()
        if 'windows' in platform.platform().lower():
            return git.diff_filenames("deploy", "origin/deploy")
        else:
            return git("-c", "color.diff=false", "diff", "--name-only", "deploy", "origin/deploy")

    @staticmethod
    def pull_remote():
        git.pull()
