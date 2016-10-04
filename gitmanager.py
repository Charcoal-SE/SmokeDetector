from sh import git
import time


class GitManager:
    @classmethod
    def add_to_blacklist(self, items_to_blacklist, username):
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

        # Add items to file

        with open("blacklisted_websites.txt", "a") as blacklisted_websites:
            blacklisted_websites.write("\n" + "\n".join(items_to_blacklist))

        # Checkout a new branch (mostly unnecessary, but may help if we create PRs in the future
        branch = "auto-blacklist-%s" % str(time.time())
        git.checkout("-b", branch)

        # Clear HEAD just in case
        git.reset("HEAD")

        git.add("blacklisted_websites.txt")
        git.commit("-m", "Auto blacklist of %s by %s --autopull" % (", ".join(items_to_blacklist), username))

        git.checkout("master")
        git.merge(branch)
        git.push()

        return (True, "Blacklisted {0} - the entry will be applied via autopull if CI succeeds.".format(", ".join(items_to_blacklist)))
