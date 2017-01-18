from sh import git
from requests.auth import HTTPBasicAuth
from globalvars import GlobalVars
import requests
import time
import json


# noinspection PyRedundantParentheses,PyClassHasNoInit,PyBroadException
class GitManager:
    @staticmethod
    def add_to_blacklist(**kwargs):
        blacklist = kwargs.get("blacklist", "")
        item_to_blacklist = kwargs.get("item_to_blacklist", "")
        username = kwargs.get("username", "")
        chat_profile_link = kwargs.get("chat_profile_link", "http://chat.stackexchange.com/users")
        code_permissions = kwargs.get("code_permissions", False)

        # Make sure git credentials are set up
        if git.config("--global", "--get", "user.name") == "":
            return (False, "Tell someone to run `git config --global user.name \"SmokeDetector\"`")

        if git.config("--global", "--get", "user.name") == "":
            return (False, "Tell someone to run `git config --global user.email \"smokey@erwaysoftware.com\"`")

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
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "keyword":
            blacklist_file_name = "bad_keywords.txt"
            ms_search_option = "&body_is_regex=1&body="
        elif blacklist == "username":
            blacklist_file_name = "blacklisted_usernames.txt"
            ms_search_option = "&username_is_regex=1&username="
        else:
            # Just checking all bases, but blacklist_file_name *might* have empty value
            # if we don't address it here.
            return (False, "Invalid blacklist type specified, something has broken badly!")

        git.checkout("master")
        try:
            git.pull()
        except:
            pass

        # Check that we're up-to-date with origin (GitHub)
        git.remote.update()
        if git("rev-parse", "refs/remotes/origin/master").strip() != git("rev-parse", "master").strip():
            return (False, "HEAD isn't at tip of origin's master branch")

        # Check that blacklisted_websites.txt isn't modified locally. That could get ugly fast
        if blacklist_file_name in git.status():  # Also ugly
            return (False, "{0} is modified locally. This is probably bad.".format(blacklist_file_name))

        # Add item to file
        with open(blacklist_file_name, "a+") as blacklist_file:
            last_character = blacklist_file.read()[-1:]
            if last_character != "\n":
                blacklist_file.write("\n")
            blacklist_file.write(item_to_blacklist + "\n")

        # Checkout a new branch (for PRs for non-code-privileged people)
        branch = "auto-blacklist-{0}".format(str(time.time()))
        git.checkout("-b", branch)

        # Clear HEAD just in case
        git.reset("HEAD")

        git.add(blacklist_file_name)
        git.commit("-m", u"Auto blacklist of {0} by {1} --autopull".format(item_to_blacklist, username))

        if code_permissions:
            git.checkout("master")
            git.merge(branch)
            git.push()
        else:
            git.push("origin", branch)
            git.checkout("master")

            if GlobalVars.github_username is None or GlobalVars.github_password is None:
                return (False, "Tell someone to set a GH password")

            payload = {"title": "{0}: Blacklist {1}".format(username, item_to_blacklist),
                       "body": "[{0}]({1}) requests the blacklist of the {2} {3}. See the Metasmoke search [here]"
                               "(https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93{4}{5})\n"
                               "<!-- METASMOKE-BLACKLIST-{6} {3} -->".format(username, chat_profile_link, blacklist,
                                                                         item_to_blacklist, ms_search_option,
                                                                         item_to_blacklist.replace(" ", "+"),
                                                                         blacklist.upper()),
                       "head": branch,
                       "base": "master"}
            response = requests.post("https://api.github.com/repos/Charcoal-SE/SmokeDetector/pulls",
                                     auth=HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password),
                                     data=json.dumps(payload))
            print(response.json())
            try:
                git.checkout("deploy")  # Return to deploy, pending the accept of the PR in Master.
                return (True, "You don't have code privileges, but I've [created a pull request for you]({0}).".format(
                    response.json()["html_url"]))
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

        git.checkout("deploy")  # Return to deploy to await CI.

        return (True, "Blacklisted {0}".format(item_to_blacklist))

    @staticmethod
    def current_git_status():
        return git.status()
