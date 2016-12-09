from sh import git
from requests.auth import HTTPBasicAuth
from globalvars import GlobalVars
import requests
import time
import json


class GitManager:
    @classmethod
    def add_to_blacklist(self, **kwargs):
        blacklist = kwargs.get("blacklist", "website")
        items_to_blacklist = kwargs.get("items_to_blacklist", [])
        username = kwargs.get("username", "")
        chat_profile_link = kwargs.get("chat_profile_link", "http://chat.stackexchange.com/users")
        code_permissions = kwargs.get("code_permissions", False)

        if blacklist == "website":
            blacklist_file_name = "blacklisted_websites.txt"
        elif blacklist == "keyword":
            blacklist_file_name = "bad_keywords.txt"
        elif blacklist == "username":
            blacklist_file_name = "blacklisted_usernames.txt"

        # Check if we're on master
        if git("rev-parse", "--abbrev-ref", "HEAD").strip() != "master":
            return (False, "Not currently on master.")

        # Check that we're up-to-date with origin (GitHub)
        git.remote.update()
        if git("rev-parse", "refs/remotes/origin/master").strip() != git("rev-parse", "master").strip():
            return (False, "HEAD isn't at tip of origin's master branch")

        # Check that blacklisted_websites.txt isn't modified locally. That could get ugly fast
        if blacklist_file_name in git.status():  # Also ugly
            return (False, "{0} modified locally. This is probably bad.".format(blacklist_file_name))

        # Store current commit hash
        current_commit = git("rev-parse", "HEAD").strip()

        # Add items to file
        with open(blacklist_file_name, "a+") as blacklist_file:
            last_character = blacklist_file.read()[-1:]
            if last_character != "\n":
                blacklist_file.write("\n")
            blacklist_file.write("\n".join(items_to_blacklist) + "\n")

        # Checkout a new branch (for PRs for non-code-privileged people)
        branch = "auto-blacklist-{0}".format(str(time.time()))
        git.checkout("-b", branch)

        # Clear HEAD just in case
        git.reset("HEAD")

        git.add(blacklist_file_name)
        git.commit("-m", u"Auto blacklist of {0} by {1} --autopull".format(", ".join(items_to_blacklist), username))

        if code_permissions:
            git.checkout("master")
            git.merge(branch)
            git.push()
        else:
            git.push("origin", branch)
            git.checkout("master")

            if GlobalVars.github_username is None or GlobalVars.github_password is None:
                return (False, "Tell someone to set a GH password")

            list_of_domains = ""

            for domain in range(len(items_to_blacklist)):
                list_of_domains += "\n - {0} - [MS search](https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93&body_is_regex=1&body={0})".format(items_to_blacklist[domain])

            payload = {"title": "{0}: Blacklist {1}".format(username, ", ".join(items_to_blacklist)),
                       "body": "[{0}]({1}) requests the blacklist of the following {2}(s): \n{3}\n<!-- METASMOKE-BLACKLIST {4} -->".format(username, chat_profile_link, blacklist, list_of_domains, "|".join(items_to_blacklist)),
                       "head": branch,
                       "base": "master"}
            response = requests.post("https://api.github.com/repos/Charcoal-SE/SmokeDetector/pulls", auth=HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password), data=json.dumps(payload))
            print(response.json())
            try:
                return (True, "You don't have code privileges, but I've [created a pull request for you]({0}).".format(response.json()["html_url"]))
            except KeyError:
                # Error capture/checking for any "invalid" GH reply without an 'html_url' item, which will throw a KeyError.
                if "Bad credentials" in str(response.json()['message']):
                    # Capture the case when GH credentials are bad or invalid
                    return (False, "Something is wrong with the GH credentials, tell someone to check the GH credentials.")
                else:
                    # Capture any other invalid response cases.
                    return (False, "A bad or invalid reply was received from GH, the message was: %s" % response.json()['message'])

        git.checkout(current_commit)  # Return to old commit to await CI. This will make Smokey think it's in reverted mode if it restarts

        return (True, "Blacklisted {0} - the entry will be applied via autopull if CI succeeds.".format(", ".join(items_to_blacklist)))

    @classmethod
    def current_git_status(self):
        return git.status()
