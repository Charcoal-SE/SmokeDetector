from spamhandling import handle_spam, check_if_spam
from datahandling import add_or_update_api_data, clear_api_data
from globalvars import GlobalVars
from operator import itemgetter
import json
import time
import requests


class BodyFetcher:
    queue = {}

    specialCases = {"stackoverflow.com": 5,
                    "serverfault.com": 5,
                    "math.stackexchange.com": 10,
                    "drupal.stackexchange.com": 1,
                    "meta.stackexchange.com": 1}

    threshold = 2

    last_activity_date = 0

    def add_to_queue(self, post):
        d = json.loads(json.loads(post)["data"])
        sitebase = d["siteBaseHostAddress"]
        postid = d["id"]
        if postid == 3122 and sitebase == "meta.stackexchange.com":
            return  # don't check meta sandbox, it's full of weird posts
        if sitebase in self.queue:
            self.queue[sitebase].append(postid)
        else:
            self.queue[sitebase] = [postid]

        print self.queue
        self.check_queue()
        return

    def check_queue(self):
        for site, values in self.queue.iteritems():
            if site in self.specialCases:
                if len(self.queue[site]) >= self.specialCases[site]:
                    print "site " + site + " met special case quota, fetching..."
                    self.make_api_call_for_site(site)
                    return

        # if we don't have any sites with their queue filled, take the first one without a special case
        for site, values in self.queue.iteritems():
            if site not in self.specialCases and len(values) >= self.threshold:
                self.make_api_call_for_site(site)
                return

    def print_queue(self):
        string = ""
        for site, values in self.queue.iteritems():
            string = string + "\n" + site + ": " + str(len(values))

        return string

    def make_api_call_for_site(self, site):
        posts = self.queue.pop(site)
        if site == "stackoverflow.com":
            # Not all SO questions are shown in the realtime feed. We now
            # fetch all recently modified SO questions to work around that.
            min_query = ""
            if self.last_activity_date != 0:
                min_query = "&min=" + str(self.last_activity_date)
                pagesize = "50"
            else:
                pagesize = "25"
            url = "http://api.stackexchange.com/2.2/questions?site=stackoverflow&filter=!4y_-sca-)pfAwlmP_1FxC6e5yzutRIcQvonAiP&key=IAkbitmze4B8KpacUfLqkw((&pagesize=" + pagesize + min_query
        else:
            url = "http://api.stackexchange.com/2.2/questions/" + ";".join(str(x) for x in posts) + "?site=" + site + "&filter=!4y_-sca-)pfAwlmP_1FxC6e5yzutRIcQvonAiP&key=IAkbitmze4B8KpacUfLqkw(("
        # wait to make sure API has/updates post data
        time.sleep(60)
        try:
            response = requests.get(url, timeout=20).json()
        except requests.exceptions.Timeout:
            return  # could add some retrying logic here, but eh.

        add_or_update_api_data(site)

        if "quota_remaining" in response:
            if response["quota_remaining"] - GlobalVars.apiquota >= 1000 and GlobalVars.apiquota >= 0:
                GlobalVars.charcoal_hq.send_message("API quota rolled over with {} requests remaining.".format(GlobalVars.apiquota))
                sorted_calls_per_site = sorted(GlobalVars.api_calls_per_site.items(), key=itemgetter(1), reverse=True)
                api_quota_used_per_site = ""
                for site, quota_used in sorted_calls_per_site:
                    api_quota_used_per_site = api_quota_used_per_site + site + ": " + str(quota_used) + "\n"
                api_quota_used_per_site = api_quota_used_per_site.strip()
                GlobalVars.charcoal_hq.send_message(api_quota_used_per_site, False)
                clear_api_data()

            elif response["quota_remaining"] == 0:
                GlobalVars.charcoal_hq.send_message("API reports no quota left!  May be a glitch.")
            GlobalVars.apiquota = response["quota_remaining"]
        else:
            GlobalVars.charcoal_hq.send_message("The quota_remaining property was not in the API response.")

        if site == "stackoverflow.com":
            if len(response["items"]) > 0 and "last_activity_date" in response["items"][0]:
                self.last_activity_date = response["items"][0]["last_activity_date"]

        for post in response["items"]:
            if "title" not in post or "body" not in post:
                continue
            title = GlobalVars.parser.unescape(post["title"])
            body = GlobalVars.parser.unescape(post["body"])
            link = post["link"]
            try:
                owner_name = GlobalVars.parser.unescape(post["owner"]["display_name"])
                owner_link = post["owner"]["link"]
                owner_rep = post["owner"]["reputation"]
            except:
                owner_name = ""
                owner_link = ""
                owner_rep = 0
            q_id = str(post["question_id"])

            is_spam, reason, why = check_if_spam(title, body, owner_name, owner_link, site, q_id, False, False, owner_rep)
            if is_spam:
                try:
                    handle_spam(title, body, owner_name, site, link, owner_link, q_id, reason, False, why)
                except:
                    print "NOP"
            try:
                for answer in post["answers"]:
                    answer_title = ""
                    body = answer["body"]
                    print "got answer from owner with name " + owner_name
                    link = answer["link"]
                    a_id = str(answer["answer_id"])
                    try:
                        owner_name = GlobalVars.parser.unescape(answer["owner"]["display_name"])
                        owner_link = answer["owner"]["link"]
                        owner_rep = answer["owner"]["reputation"]
                    except:
                        owner_name = ""
                        owner_link = ""
                        owner_rep = 0

                    is_spam, reason, why = check_if_spam(answer_title, body, owner_name, owner_link, site, a_id, True, False, owner_rep)
                    if is_spam:
                        try:
                            handle_spam(title, body, owner_name, site, link, owner_link, a_id, reason, True, why)
                        except:
                            print "NOP"
            except:
                print "no answers"
        return
