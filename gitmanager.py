# coding=utf-8

import sys
import platform
import time
import json
from datetime import datetime
from threading import Lock

import regex
import requests
from requests.auth import HTTPBasicAuth

from urllib.parse import quote_plus
from urllib.parse import quote
from globalvars import GlobalVars
if GlobalVars.on_windows:
    # noinspection PyPep8Naming
    from _Git_Windows import git, GitError
else:
    from sh.contrib import git
    from sh import ErrorReturnCode as GitError

from helpers import log, log_current_exception, only_blacklists_changed
from blacklists import *


def _anchor(str_to_anchor, blacklist_type):
    """ Anchor a string according to the operation. """
    if blacklist_type in {Blacklist.WATCHED_KEYWORDS, Blacklist.KEYWORDS}:
        return r"(?s:\b" + str_to_anchor + r"\b)"
    else:
        return str_to_anchor


class GitHubManager:
    still_using_usernames = GlobalVars.github_access_token is None

    if still_using_usernames:
        still_using_usernames_nudge = " By the way, tell my owner to [set up personal access tokens]" \
                                      "(//chat.stackexchange.com/transcript/message/55007870#55007870)" \
                                      " when they have time :)"
        auth_args = {"auth": HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password)}
    else:
        still_using_usernames_nudge = ""
        auth_args = {"headers": {'Authorization': 'token {}'.format(GlobalVars.github_access_token)}}

    @classmethod
    def call_api(cls, method, route, payload):
        """ Perform API calls. """
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        response = requests.request(method, route, data=payload, **cls.auth_args)
        return response

    @classmethod
    def create_pull_request(cls, payload):
        """
        Creates a pull request on GitHub, returns the json'd response
        """
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        response = requests.post("https://api.github.com/repos/{}/pulls".format(GlobalVars.bot_repo_slug),
                                 data=payload, **cls.auth_args)
        return response.json()

    @classmethod
    def comment_on_thread(cls, thread_id, body):
        url = "https://api.github.com/repos/{}/issues/{}/comments".format(GlobalVars.bot_repo_slug, thread_id)
        payload = json.dumps({'body': body})
        response = requests.post(url, data=payload, **cls.auth_args)
        return response.json()

    @classmethod
    def get_pull_request(cls, pr_id, payload):
        """ Get pull requests info. """
        url = "https://api.github.com/repos/{}/pulls/{}".format(GlobalVars.bot_repo_slug, pr_id)
        return cls.call_api("GET", url, payload)

    @classmethod
    def update_pull_request(cls, pr_id, payload):
        """ Update pull requests' status (open/closed). """
        url = "https://api.github.com/repos/{}/pulls/{}".format(GlobalVars.bot_repo_slug, pr_id)
        return cls.call_api("PATCH", url, payload)

# noinspection PyRedundantParentheses,PyClassHasNoInit,PyBroadException


class GitManager:
    gitmanager_lock = Lock()

    @staticmethod
    def get_origin_or_auth():
        git_url = git.config("--get", "remote.origin.url").strip()
        if git_url[0:19] == "https://github.com/" and GlobalVars.github_username and GlobalVars.github_access_token:
            preformat_url = ('https://{}:{}@github.com/' + git_url[19:])
            return preformat_url.format(quote(GlobalVars.github_username), quote(GlobalVars.github_access_token))
        else:
            return "origin"

    @classmethod
    def add_to_blacklist(cls, blacklist='', item_to_blacklist='', username='', chat_profile_link='',
                         code_permissions=False, metasmoke_down=False, before_pattern='', after_pattern=''):
        if blacklist == "":
            return (False, 'GitManager: blacklist is not defined. Blame a developer.')

        if item_to_blacklist == "":
            return (False, 'GitManager: item_to_blacklist is not defined. Blame a developer.')

        # item_to_blacklist = item_to_blacklist.replace("\\s", " ")

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
            if blacklist_type not in {Blacklist.WATCHED_KEYWORDS, Blacklist.WATCHED_NUMBERS}:
                for watcher_type in {Blacklist.WATCHED_KEYWORDS, Blacklist.WATCHED_NUMBERS}:
                    watcher = Blacklist(watcher_type)
                    if watcher.exists(item_to_blacklist):
                        watch_removed = True
                        watcher.remove(item_to_blacklist)

            blacklister.add(item_to_blacklist)

            branch = "auto-blacklist-{0}".format(now)
            git.checkout("-b", branch)

            git.reset("HEAD")

            git.add(blacklist_file_name)
            if watch_removed:
                git.add('watched_keywords.txt', 'watched_numbers.txt')

            git("-c", "user.name=" + GlobalVars.git_name,
                "-c", "user.email=" + GlobalVars.git_email,
                "commit",
                "--author={} <{}>".format(GlobalVars.git_name, GlobalVars.git_email),
                "-m", "Auto {0} of{before_pattern} `{1}`{after_pattern} by {2}".format(op, item, username,
                                                                                       before_pattern=before_pattern,
                                                                                       after_pattern=after_pattern))

            origin_or_auth = cls.get_origin_or_auth()
            if code_permissions:
                git.checkout("master")
                git.merge(branch)
                git.push(origin_or_auth, "master")
                git.branch('-D', branch)  # Delete the branch in the local git tree since we're done with it.
            else:
                git.push(origin_or_auth, branch)
                git.checkout("master")

                if ((GlobalVars.github_username is None or GlobalVars.github_password is None)
                        and (GlobalVars.github_access_token is None)):
                    return (False, "Tell someone to set a GH token")

                payload = {"title": "{0}: {1} {2}".format(username, op.title(), item),
                           "body": "[{0}]({1}) requests the {2} of the {3} `{4}`. See the MS search [here]"
                                   "(https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93{5}{6}) and the "
                                   "Stack Exchange search [in text](https://stackexchange.com/search?q=%22{7}%22)"
                                   ", [in URLs](https://stackexchange.com/search?q=url%3A%22{7}%22)"
                                   ", and [in code](https://stackexchange.com/search?q=code%3A%22{7}%22)"
                                   ".\n"
                                   "<!-- METASMOKE-BLACKLIST-{8} {4} -->".format(
                                       username, chat_profile_link, op, blacklist,                # 0 1 2 3
                                       item, ms_search_option,                                    # 4 5
                                       quote_plus(_anchor(item, blacklist_type)),                 # 6
                                       quote_plus(item.replace("\\W", " ").replace("\\.", ".")),  # 7
                                       blacklist.upper()),                                        # 8
                           "head": branch,
                           "base": "master"}
                response = GitHubManager.create_pull_request(payload)
                log('debug', response)
                try:
                    git.checkout("deploy")  # Return to deploy, pending the accept of the PR in Master.
                    git.branch('-D', branch)  # Delete the branch in the local git tree since we're done with it.
                    url, pr_num = response["html_url"], response["number"]

                    if metasmoke_down:
                        return (True,
                                "MS is not reachable, so I can't see if you have blacklist manager privileges, but "
                                "I've [created PR#{1} for you]({0}).{2}".format(
                                    url, pr_num, GitHubManager.still_using_usernames_nudge))
                    else:
                        return (True,
                                "You don't have blacklist manager privileges, "
                                "but I've [created PR#{1} for you]({0}).{2}"
                                .format(url, pr_num, GitHubManager.still_using_usernames_nudge))

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
                    if "bad credentials" in str(response['message']).lower():
                        # Capture the case when GH credentials are bad or invalid
                        return (False, "Something is wrong with the GH credentials, tell someone to check them.")
                    else:
                        # Capture any other invalid response cases.
                        return (False, "A bad or invalid reply was received from GH, the message was: %s" %
                                response['message'])
        except Exception as err:
            log_current_exception()
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
                return False, "MS is offline, and I can't determine if you are a blacklist manager or not. " \
                              "If you are a blacklist manager, then wait for MS to be back up before running " \
                              "this command."
            else:
                return False, "Ask a blacklist manager to run that for you. Use `!!/whois blacklister` to find " \
                              "out who's here."

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
            git("-c", "user.name=" + GlobalVars.git_name,
                "-c", "user.email=" + GlobalVars.git_email,
                "commit",
                "--author={} <{}>".format(GlobalVars.git_name, GlobalVars.git_email),
                '-m', 'Auto un{} of `{}` by {}'.format(blacklist_type, item, username))

            git.checkout('master')
            git.merge(branch)
            origin_or_auth = cls.get_origin_or_auth()
            git.push(origin_or_auth, 'master')

            try:
                git.branch('-D', branch)
            except GitError:
                # It's OK if the branch doesn't get deleted, so long as we switch back to
                # deploy, which we do in the finally block...
                pass

        except Exception as e:
            log('error', '{}: {}'.format(type(e).__name__, e))
            log_current_exception()
            return False, 'Git operations failed for unspecified reasons.'
        finally:
            git.checkout('deploy')
            cls.gitmanager_lock.release()

        # With no exception raised, list_type should be set
        return True, 'Removed `{}` from {}'.format(item, list_type)

    @classmethod
    def merge_pull_request(cls, pr_id, comment=""):
        response = requests.get("https://api.github.com/repos/{}/pulls/{}".format(GlobalVars.bot_repo_slug, pr_id))
        if not response:
            raise ConnectionError("Cannot connect to GitHub API")
        pr_info = response.json()
        if pr_info["user"]["login"] != "SmokeDetector":
            raise ValueError("PR #{} is not created by me, so I can't approve it.".format(pr_id))
        if "<!-- METASMOKE-BLACKLIST" not in pr_info["body"]:
            raise ValueError("PR description is malformed. Blame a developer.")
        if pr_info["state"] != "open":
            raise ValueError("PR #{} is not currently open, so I won't merge it.".format(pr_id))
        ref = pr_info['head']['ref']

        if comment:  # yay we have comments now
            GitHubManager.comment_on_thread(pr_id, comment)

        try:
            # Remote checks passed, good to go here
            cls.gitmanager_lock.acquire()
            git.checkout('master')
            origin_or_auth = cls.get_origin_or_auth()
            git.fetch(origin_or_auth, '+refs/pull/{}/head'.format(pr_id))
            git("-c", "user.name=" + GlobalVars.git_name,
                "-c", "user.email=" + GlobalVars.git_email,
                "merge",
                'FETCH_HEAD', '--no-ff', '-m', 'Merge pull request #{} from {}/{}'.format(
                    pr_id, GlobalVars.bot_repo_slug.split("/")[0], ref))
            git.push(origin_or_auth, 'master')
            try:
                git.push('-d', origin_or_auth, ref)
            except GitError as e:
                # TODO: PR merged, but branch deletion has something wrong, generate some text
                pass
            return "Merged pull request [#{0}](https://github.com/{1}/pull/{0}).".format(
                pr_id, GlobalVars.bot_repo_slug)
        finally:
            git.checkout('deploy')
            cls.gitmanager_lock.release()

    @classmethod
    def reject_pull_request(cls, pr_id, comment=""):
        response = requests.get("https://api.github.com/repos/{}/pulls/{}".format(GlobalVars.bot_repo_slug, pr_id))
        if not response:
            raise ConnectionError("Cannot connect to GitHub API")
        pr_info = response.json()
        if pr_info["user"]["login"] != "SmokeDetector":
            raise ValueError("PR #{} is not created by me, so I can't reject it.".format(pr_id))
        if "<!-- METASMOKE-BLACKLIST" not in pr_info["body"]:
            raise ValueError("PR description is malformed. Blame a developer.")
        if pr_info["state"] != "open":
            raise ValueError("PR #{} is not currently open, so I won't reject it.".format(pr_id))
        ref = pr_info['head']['ref']

        if comment:  # yay we have comments now
            GitHubManager.comment_on_thread(pr_id, comment)

        with cls.gitmanager_lock:
            origin_or_auth = cls.get_origin_or_auth()
            git.fetch(origin_or_auth, '+refs/pull/{}/head'.format(pr_id))
            payload = {"state": "closed"}
            response = GitHubManager.update_pull_request(pr_id, payload)
            if response:
                if response.json()["state"] == "closed":
                    git.push('-d', origin_or_auth, ref)
                    return "Closed pull request [#{0}](https://github.com/{1}/pull/{0}).".format(
                        pr_id, GlobalVars.bot_repo_slug)

        raise RuntimeError("Closing pull request #{} failed. Manual operations required.".format(pr_id))

    @staticmethod
    def prepare_git_for_operation(blacklist_file_name):
        try:
            git.checkout('master')
            git.remote.update()
            git.reset('--hard', 'origin/master')
        except GitError as e:
            if GlobalVars.on_windows:
                return False, "Not doing this, we're on Windows."
            log_current_exception()
            return False, "`git pull` has failed. This shouldn't happen. Details have been logged."

        if GlobalVars.on_windows:
            remote_ref = git.rev_parse("refs/remotes/origin/master").strip()
            local_ref = git.rev_parse("master").strip()
        else:
            remote_ref = git("rev-parse", "refs/remotes/origin/master").strip()
            local_ref = git("rev-parse", "master").strip()
        if local_ref != remote_ref:
            local_log = git.log(r"--pretty=`[%h]` *%cn*: %s", "-1", str(local_ref)).strip()
            remote_log = git.log(r"--pretty=`[%h]` *%cn*: %s", "-1", str(remote_ref)).strip()
            return False, "HEAD isn't at tip of origin's master branch (local {}, remote {})".format(
                local_log, remote_log)

        return True, None

    @staticmethod
    def current_git_status():
        if GlobalVars.on_windows:
            return git.status_stripped()
        else:
            return str(git.status())

    @staticmethod
    def current_branch():
        return str(git('rev-parse', '--abbrev-ref', 'HEAD')).strip()

    @staticmethod
    def merge_abort():
        git.merge("--abort")

    @staticmethod
    def reset_head():
        git.reset("--hard", "HEAD")
        git.clean("-f")

    @staticmethod
    def get_remote_diff():
        git.fetch()
        if GlobalVars.on_windows:
            return git.diff_filenames("HEAD", "deploy@{u}")
        else:
            return git.diff("--name-only", "HEAD", "deploy@{u}")

    @staticmethod
    def get_local_diff():
        if GlobalVars.on_windows:
            return git.diff_filenames("HEAD", "master")
        else:
            return git.diff("--name-only", "HEAD", "master")

    @staticmethod
    def pull_remote():
        # We need to pull both the master and deploy branches here in order to be in sync with GitHub.
        git.checkout('deploy')
        git.pull()
        git.checkout('master')
        git.pull()
        git.checkout('deploy')

    @classmethod
    def pull_local(cls):
        diff = GitManager.get_local_diff()
        if not only_blacklists_changed(diff):
            return
        try:
            git.merge("--ff-only", "master")
            origin_or_auth = cls.get_origin_or_auth()
            git.push(origin_or_auth, "deploy")
        except GitError:
            return

    @staticmethod
    def sync_remote():
        try:
            git.fetch('--force')
            git.checkout('master', '--force')
            git.branch('--create-reflog', '-f', 'deploy', '-t', 'origin/deploy')
            git.checkout('deploy', '--force')
            git.branch('--create-reflog', '-f', 'master', '-t', 'origin/master')
            return True, "Synced to origin/master and origin/deploy. You'll probably want to !!/reboot now."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def sync_remote_hard():
        try:
            git.fetch('--force')
            git.checkout('master', '--force')
            git.reset('origin/master', '--hard')
            git.checkout('deploy', '--force')
            git.reset('origin/deploy', '--hard')
            git.checkout('master', '--force')
            git.checkout('deploy', '--force')
            return True, "Synced hard to origin/master and origin/deploy."
        except Exception as e:
            return False, str(e)
