from sh import git
from requests.auth import HTTPBasicAuth
from globalvars import GlobalVars
import requests
import time
import json


class GitManager:
    @classmethod
    def add_to_blacklist(self, items_to_blacklist, username, code_permissions):
        # Check if we're on master
        if git("rev-parse", "--abbrev-ref", "HEAD").strip() != "master":
            return (False, "Not currently on master.")

        # Check that we're up-to-date with origin (GitHub)
        git.remote.update()
        if git("rev-parse", "refs/remotes/origin/master").strip() != git("rev-parse", "master").strip():
            return (False, "HEAD isn't at tip of origin's master branch")

        # Check that blacklisted_websites.txt isn't modified locally. That could get ugly fast
        if "blacklisted_websites.txt" in git.status():  # Also ugly
            return (False, "blacklisted_websites.txt modified locally. This is probably bad.")

        # Store current commit hash
        current_commit = git("rev-parse", "HEAD").strip()

        # Add items to file
        with open("blacklisted_websites.txt", "a+") as blacklisted_websites:
            last_character = blacklisted_websites.read()[-1:]
            if last_character != "\n":
                blacklisted_websites.write("\n")
            blacklisted_websites.write("\n".join(items_to_blacklist) + "\n")

        # Checkout a new branch (mostly unnecessary, but may help if we create PRs in the future
        branch = "auto-blacklist-{0}".format(str(time.time()))
        git.checkout("-b", branch)

        # Clear HEAD just in case
        git.reset("HEAD")

        git.add("blacklisted_websites.txt")
        git.commit("-m", u"Auto blacklist of {0} by {1} --autopull".format(", ".join(items_to_blacklist), username))

        if code_permissions:
            git.checkout("master")
            git.merge(branch)
            git.push()
        else:
            git.push("origin", branch)
            git.checkout("master")

            if GlobalVars.github_username is None or GlobalVars.github_password is None:
                return (False, "tell someone to set a GH password")
            
            list_of_domains = ""
            
            for domain in range(len(items_to_blacklist)):
	        list_of_domains += "\n - {0} - [MS search](https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93&body_is_regex=1&body={0})".format(items_to_blacklist[domain])
            
            payload = {"title": "{0}: Blacklist {1}".format(username, ", ".join(items_to_blacklist)),
                       "body": "{0} requests blacklist of domains: \n{1}".format(username, list_of_domains),
                       "head": branch,
                       "base": "master"}
            response = requests.post("https://api.github.com/repos/Charcoal-SE/SmokeDetector/pulls", auth=HTTPBasicAuth(GlobalVars.github_username, GlobalVars.github_password), data=json.dumps(payload))
            print(response.json())
            return (True, "You don't have code privileges, but I've [created a pull request for you]({0}).".format(response.json()["html_url"]))

        git.checkout(current_commit)  # Return to old commit to await CI. This will make Smokey think it's in reverted mode if it restarts

        if not code_permissions:
            return (False, "Unable to perform action due to lack of code-level permissions. [Branch pushed](https://github.com/Charcoal-SE/SmokeDetector/tree/{0}), PR at your leisure.".format(branch))

        return (True, "Blacklisted {0} - the entry will be applied via autopull if CI succeeds.".format(", ".join(items_to_blacklist)))

    @classmethod
    def current_git_status(self):
        return git.status()
