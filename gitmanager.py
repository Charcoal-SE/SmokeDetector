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
    from classes import Git as git, GitError
else:
    from sh.contrib import git
    from sh import ErrorReturnCode as GitError

from helpers import log, only_blacklists_changed
from globalvars import GlobalVars
from blacklists import *


# noinspection PyRedundantParentheses,PyClassHasNoInit,PyBroadException
class GitManager:
    gitmanager_lock = Lock()

    @classmethod
    def add_to_blacklist(cls, blacklist='', item_to_blacklist='', username='', chat_profile_link='',
                         code_permissions=False, metasmoke_down=False):
        if git.config("--get", "user.name", _ok_code=[0, 1]) == "":
            return (False, 'Tell someone to run `git config user.name "SmokeDetector"`')

        if git.config("--get", "user.email", _ok_code=[0, 1]) == "":
            return (False, 'Tell someone to run `git config user.email "smokey@erwaysoftware.com"`')

        if blacklist == "":
            return (False, 'GitManager: blacklist is not defined. Blame a developer.')

        if item_to_blacklist == "":
            return (False, 'GitManager: item_to_blacklist is not defined. Blame a developer.')

        item_to_blacklist = item_to_blacklist.replace("\\s", " ")

        if blacklist == "website":
            blacklist_type = Blacklist.WEBSITES
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "keyword":
            blacklist_type = Blacklist.KEYWORDS
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "username":
            blacklist_type = Blacklist.USERNAMES
            ms_search_option = "&username_is_regex=1&username="
        elif blacklist == "number":
            blacklist_type = Blacklist.NUMBERS
            ms_search_option = "&body="
        elif blacklist == "watch_keyword":
            blacklist_type = Blacklist.WATCHED_KEYWORDS
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "watch_number":
            blacklist_type = Blacklist.WATCHED_NUMBERS
            ms_search_option = "&body="
        else:
            return (False, 'GitManager: blacklist is not recognized. Blame a developer.')

        blacklister = Blacklist(blacklist_type)
        blacklist_file_name = blacklist_type[0]

        try:
            cls.gitmanager_lock.acquire()
            status, message = cls.prepare_git_for_operation(blacklist_file_name)
            if not status:
                return (False, message)

            now = str(int(time.time()))

            if blacklist_type in {Blacklist.WATCHED_KEYWORDS, Blacklist.WATCHED_NUMBERS}:
                op = 'watch'
                item = item_to_blacklist
                item_to_blacklist = "\t".join([now, username, item])
            else:
                op = 'blacklist'
                item = item_to_blacklist

            exists, line = blacklister.exists(item_to_blacklist)
            if exists:
                return (False, 'Already {}ed on line {} of {}'.format(op, line, blacklist_file_name))

            watch_removed = False
            if blacklist_type not in [Blacklist.WATCHED_KEYWORDS]:
                watcher = Blacklist(Blacklist.WATCHED_KEYWORDS)
                if watcher.exists(item_to_blacklist):
                    watch_removed = True
                    watcher.remove(item_to_blacklist)

            blacklister.add(item_to_blacklist)

            branch = "auto-blacklist-{0}".format(now)
            git.checkout("-b", branch)

            git.reset("HEAD")

            git.add(blacklist_file_name)
            if watch_removed:
                git.add('watched_keywords.txt')

            git.commit("--author='SmokeDetector <smokey@erwaysoftware.com>'",
                       "-m", u"Auto {0} of `{1}` by {2} --autopull".format(op, item, username))

            if code_permissions:
                git.checkout("master")
                git.merge(branch)
                git.push("origin", "master")
                git.branch('-D', branch)  # Delete the branch in the local git tree since we're done with it.
            else:
                git.push("origin", branch)
                git.checkout("master")

                if GlobalVars.github_username is None or GlobalVars.github_password is None:
                    return (False, "Tell someone to set a GH password")

                payload = {"title": "{0}: {1} {2}".format(username, op.title(), item),
                           "body": "[{0}]({1}) requests the {2} of the {3} `{4}`. See the MS search [here]"
                                   "(https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93{5}{6}) and the "
                                   "Stack Exchange search [here](https://stackexchange.com/search?q=%22{7}%22).\n"
                                   "<!-- METASMOKE-BLACKLIST-{8} {4} -->".format(
                                       username, chat_profile_link, op, blacklist,                # 0 1 2 3
                                       item, ms_search_option,                                    # 4 5
                                       quote_plus(item),                                          # 6
                                       quote_plus(item.replace("\\W", " ").replace("\\.", ".")),  # 7
                                       blacklist.upper()),                                        # 8
                           "head": branch,
                           "base": "master"}
                response = requests.post("https://api.github.com/repos/{}/pulls".format(GlobalVars.bot_repo_slug),
                                         auth=HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password),
                                         data=json.dumps(payload))
                log('debug', response.json())
                try:
                    git.checkout("deploy")  # Return to deploy, pending the accept of the PR in Master.
                    git.branch('-D', branch)  # Delete the branch in the local git tree since we're done with it.
                    url = response.json()["html_url"]
                    if metasmoke_down:
                        return (True,
                                "MS is not reachable, so I can't see if you have code privileges, but I've "
                                "[created PR#{1} for you]({0}).".format(
                                    url, url.split('/')[-1]))
                    else:
                        return (True,
                                "You don't have code privileges, but I've [created PR#{1} for you]({0}).".format(
                                    url, url.split('/')[-1]))

                except KeyError:
                    git.checkout("deploy")  # Return to deploy

                    try:
                        # Delete the branch in the local git tree, we'll create it again if the
                        # command is run again. This way, we keep things a little more clean in
                        # the local git tree
                        git.branch('-D', branch)
                    except GitError:
                        # It's OK if the branch doesn't get deleted, so long as we switch back to
                        # deploy, which we do in the finally block...
                        pass

                    # Error capture/checking for any "invalid" GH reply without an 'html_url' item,
                    # which will throw a KeyError.
                    if "bad credentials" in str(response.json()['message']).lower():
                        # Capture the case when GH credentials are bad or invalid
                        return (False, "Something is wrong with the GH credentials, tell someone to check them.")
                    else:
                        # Capture any other invalid response cases.
                        return (False, "A bad or invalid reply was received from GH, the message was: %s" %
                                response.json()['message'])
        except Exception as err:
            with open('errorLogs.txt', 'a', encoding="utf-8") as f:
                f.write("{dt} {message}".format(dt=datetime.now().strftime('%Y-%m-%d %H:%M:%s'), message=str(err)))
            return (False, "Git functions failed for unspecified reasons, details may be in error log.")
        finally:
            # Always return to `deploy` branch when done with anything.
            git.checkout("deploy")
            cls.gitmanager_lock.release()

        if op == 'blacklist':
            return (True, "Blacklisted `{0}`".format(item))
        elif op == 'watch':
            return (True, "Added `{0}` to watchlist".format(item))

    @classmethod
    def remove_from_blacklist(cls, item, username, blacklist_type="", code_privileged=False, metasmoke_down=False):
        if not code_privileged:
            if metasmoke_down:
                return False, "MS is offline, and I can't determine if you are a code admin or not. " \
                              "If you are a code admin, then wait for MS to be back up before running this command."
            else:
                return False, "Ask a code admin to run that for you. Use `!!/whois code_admin` to find out who's here."

        try:
            cls.gitmanager_lock.acquire()
            git.checkout("master")

            if blacklist_type == "watch":
                blacklists = [Blacklist.WATCHED_KEYWORDS, Blacklist.WATCHED_NUMBERS]
                list_type = "watchlist"
            elif blacklist_type == "blacklist":
                blacklists = [Blacklist.KEYWORDS, Blacklist.WEBSITES, Blacklist.USERNAMES, Blacklist.NUMBERS]
                list_type = "blacklist"
            else:
                return False, "`blacklist_type` not set, blame a developer."

            for blacklist in blacklists:
                file_name = blacklist[0]
                manager = Blacklist(blacklist)

                exists, _line = manager.exists(item)
                if exists:
                    break

            if not exists:
                return False, 'No such item `{}` in {}.'.format(item, list_type)

            status, message = cls.prepare_git_for_operation(file_name)
            if not status:
                return False, message

            branch = 'auto-un{}-{}'.format(blacklist_type, time.time())
            git.checkout('-b', branch)
            git.reset('HEAD')

            manager.remove(item)

            git.add(file_name)
            git.commit("--author='SmokeDetector <smokey@erwaysoftware.com>'",
                       '-m', 'Auto un{} of `{}` by {} --autopull'.format(blacklist_type, item, username))

            git.checkout('master')
            git.merge(branch)
            git.push('origin', 'master')

            try:
                git.branch('-D', branch)
            except GitError:
                # It's OK if the branch doesn't get deleted, so long as we switch back to
                # deploy, which we do in the finally block...
                pass

        except Exception as e:
            log('error', '{}: {}'.format(type(e).__name__, e))
            return False, 'Git operations failed for unspecified reasons.'
        finally:
            git.checkout('deploy')
            cls.gitmanager_lock.release()

        # With no exception raised, list_type should be set
        return True, 'Removed `{}` from {}'.format(item, list_type)

    @staticmethod
    def prepare_git_for_operation(blacklist_file_name):
        git.checkout('master')

        try:
            git.pull()
        except GitError:
            pass

        git.remote.update()
        at_tip = git.rev_parse("refs/remotes/origin/master").strip() == git.rev_parse("master").strip() \
            if 'windows' in platform.platform().lower() else \
            git("rev-parse", "refs/remotes/origin/master").strip() == git("rev-parse", "master").strip()
        if not at_tip:
            return (False, "HEAD isn't at tip of origin's master branch")

        if blacklist_file_name in git.status():
            return (False, "{0} is modified locally. This is probably bad.".format(blacklist_file_name))

        return (True, None)

    @staticmethod
    def current_git_status():
        if 'windows' in platform.platform().lower():
            return git.status_stripped()
        else:
            return str(git.status())

    @staticmethod
    def current_branch():
        return str(git('rev-parse', '--abbrev-ref', 'HEAD')).strip()

    @staticmethod
    def merge_abort():
        if 'windows' in platform.platform().lower():
            return  # No we don't do Windows
        git.merge("--abort")

    @staticmethod
    def reset_head():
        if 'windows' in platform.platform().lower():
            return  # No we don't do Windows
        git.reset("--hard", "HEAD")
        git.clean("-f")

    @staticmethod
    def get_remote_diff():
        git.fetch()
        if 'windows' in platform.platform().lower():
            return git.diff_filenames("HEAD", "origin/deploy")
        else:
            return git.diff("--name-only", "HEAD", "origin/deploy")

    @staticmethod
    def get_local_diff():
        if 'windows' in platform.platform().lower():
            return git.diff_filenames("HEAD", "master")
        else:
            return git.diff("--name-only", "HEAD", "master")

    @staticmethod
    def pull_remote():
        git.pull()

    @staticmethod
    def pull_local():
        diff = GitManager.get_local_diff()
        if not only_blacklists_changed(diff):
            return
        try:
            git.merge("--ff-only", "master")
            git.push("origin", "deploy")
        except GitError:
            return
