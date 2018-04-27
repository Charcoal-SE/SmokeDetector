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
from blacklists import *


# noinspection PyRedundantParentheses,PyClassHasNoInit,PyBroadException
class GitManager:
    gitmanager_lock = Lock()

    @classmethod
    def add_to_blacklist(cls, blacklist='', item_to_blacklist='', username='', chat_profile_link='',
                         code_permissions=False):
        if git.config("--get", "user.name", _ok_code=[0, 1]) == "":
            return (False, 'Tell someone to run `git config user.name "SmokeDetector"`')

        if git.config("--get", "user.email", _ok_code=[0, 1]) == "":
            return (False, 'Tell someone to run `git config user.email "smokey@erwaysoftware.com"`')

        if blacklist == "":
            return (False, 'GitManager: blacklist is not defined. Blame a developer.')

        if item_to_blacklist == "":
            return (False, 'GitManager: item_to_blacklist is not defined. Blame a developer.')

        item_to_blacklist = item_to_blacklist.replace("\s", " ")

        if blacklist == "website":
            blacklist_type = Blacklist.WEBSITES
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "keyword":
            blacklist_type = Blacklist.KEYWORDS
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "username":
            blacklist_type = Blacklist.USERNAMES
            ms_search_option = "&username_is_regex=1&username="
        elif blacklist == "watch_keyword":
            blacklist_type = Blacklist.WATCHED_KEYWORDS
            ms_search_option = "&body_is_regex=1&body="
        else:
            return (False, 'GitManager: blacklist is not recognized. Blame a developer.')

        blacklister = Blacklist(blacklist_type)
        blacklist_file_name = blacklist_type[0]

        try:
            cls.gitmanager_lock.acquire()
            status, message = cls.prepare_git_for_operation(blacklist_file_name)
            if not status:
                return (False, message)

            if blacklist_type in [Blacklist.WATCHED_KEYWORDS]:
                op = 'watch'
                now = datetime.now().strftime('%s')
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

            branch = "auto-blacklist-{0}".format(str(time.time()))
            git.checkout("-b", branch)

            git.reset("HEAD")

            git.add(blacklist_file_name)
            if watch_removed:
                git.add('watched_keywords.txt')

            git.commit("--author='SmokeDetector <smokey@erwaysoftware.com>'",
                       "-m", u"Auto {0} of {1} by {2} --autopull".format(op, item, username))

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

                payload = {"title": u"{0}: {1} {2}".format(username, op.title(), item),
                           "body": u"[{0}]({1}) requests the {2} of the {3} `{4}`. See the Metasmoke search [here]"
                                   "(https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93{5}{6}) and the "
                                   "Stack Exchange search [here](https://stackexchange.com/search?q=%22{7}%22).\n"
                                   u"<!-- METASMOKE-BLACKLIST-{8} {4} -->".format(
                                       username, chat_profile_link, op, blacklist,
                                       item, ms_search_option,
                                       quote_plus(item.replace("\\W", "[- ]")),
                                       quote_plus(item.replace("\\W", " ").replace("\\.", ".")),
                                       blacklist.upper()),
                           "head": branch,
                           "base": "master"}
                response = requests.post("https://api.github.com/repos/Charcoal-SE/SmokeDetector/pulls",
                                         auth=HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password),
                                         data=json.dumps(payload))
                log('debug', response.json())
                try:
                    git.checkout("deploy")  # Return to deploy, pending the accept of the PR in Master.
                    git.branch('-D', branch)  # Delete the branch in the local git tree since we're done with it.
                    url = response.json()["html_url"]
                    return (True,
                            "You don't have code privileges, but I've [created PR#{1} for you]({0}).".format(
                                url, url.split('/')[-1]))
                except KeyError:
                    git.checkout("deploy")  # Return to deploy

                    # Delete the branch in the local git tree, we'll create it again if the
                    # command is run again. This way, we keep things a little more clean in
                    # the local git tree
                    git.branch('-D', branch)

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

    @classmethod
    def unwatch(cls, item, username, code_privileged=False):
        if not code_privileged:
            return (False, 'Ask a code admin to run that for you. Use `!!/whois code_admin` to find out who\'s here.')

        try:
            cls.gitmanager_lock.acquire()

            watchlist = Blacklist.WATCHED_KEYWORDS
            file_name = watchlist[0]
            manager = Blacklist(watchlist)

            status, message = cls.prepare_git_for_operation(file_name)
            if not status:
                return (False, message)

            branch = 'auto-unwatch-{}'.format(str(time.time()))
            git.checkout('-b', branch)
            git.reset('HEAD')

            manager.remove(item)

            git.add(file_name)
            git.commit("--author='SmokeDetector <smokey@erwaysoftware.com>'",
                       '-m', 'Auto unwatch of {} by {} --autopull'.format(item, username))

            git.checkout('master')
            git.merge(branch)
            git.push('origin', 'master')
            git.branch('-D', branch)
        except Exception as e:
            log('error', '{}: {}'.format(type(e).__name__, str(e)))
            return (False, 'Git operations failed for unspecified reasons.')
        finally:
            git.checkout('deploy')
            cls.gitmanager_lock.release()

        return (True, 'Removed {} from watchlist'.format(item))

    @staticmethod
    def prepare_git_for_operation(blacklist_file_name):
        git.checkout('master')

        try:
            git.pull()
        except:
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
