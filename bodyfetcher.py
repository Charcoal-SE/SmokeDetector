from spamhandling import handle_spam, check_if_spam
from datahandling import add_or_update_api_data, clear_api_data, store_bodyfetcher_queue, store_bodyfetcher_max_ids
from globalvars import GlobalVars
from operator import itemgetter
from datetime import datetime
import json
import time
import threading
import requests
from classes import Post


# noinspection PyClassHasNoInit,PyBroadException
class BodyFetcher:
    queue = {}
    previous_max_ids = {}

    special_cases = {
        "math.stackexchange.com": 15,
        "pt.stackoverflow.com": 10,
        "ru.stackoverflow.com": 10,
        "serverfault.com": 10,
        "blender.stackexchange.com": 5,
        "codegolf.stackexchange.com": 5,
        "codereview.stackexchange.com": 5,
        "es.stackoverflow.com": 5,
        "physics.stackexchange.com": 5,
        "stackoverflow.com": 5,
        "stats.stackexchange.com": 5,
        "tex.stackexchange.com": 5,
        "magento.stackexchange.com": 3,
        "gis.stackexchange.com": 3,
        "3dprinting.stackexchange.com": 1,
        "academia.stackexchange.com": 1,
        "alcohol.stackexchange.com": 1,
        "civicrm.stackexchange.com": 1,
        "drupal.stackexchange.com": 1,
        "engineering.stackexchange.com": 1,
        "expatriates.stackexchange.com": 1,
        "genealogy.stackexchange.com": 1,
        "ham.stackexchange.com": 1,
        "health.stackexchange.com": 1,
        "history.stackexchange.com": 1,
        "meta.stackexchange.com": 1,
        "money.stackexchange.com": 1,
        "outdoors.stackexchange.com": 1,
        "parenting.stackexchange.com": 1,
        "patents.stackexchange.com": 1,
        "pets.stackexchange.com": 1,
        "startups.stackexchange.com": 1,
        "travel.stackexchange.com": 1,
        "webapps.stackexchange.com": 1,
        "woodworking.stackexchange.com": 1,
        "writers.stackexchange.com": 1
    }

    time_sensitive = ["askubuntu.com", "superuser.com", "security.stackexchange.com", "movies.stackexchange.com",
                      "mathoverflow.net", "gaming.stackexchange.com", "webmasters.stackexchange.com",
                      "arduino.stackexchange.com", "workplace.stackexchange.com"]

    threshold = 2

    last_activity_date = 0

    api_data_lock = threading.Lock()
    queue_modify_lock = threading.Lock()
    max_ids_modify_lock = threading.Lock()

    def add_to_queue(self, post, should_check_site=False):
        mse_sandbox_id = 3122

        try:
            d = json.loads(json.loads(post)["data"])
        except ValueError:
            # post didn't contain a valid JSON object in its ["data"] member
            # indicative of a server-side socket reset
            return

        site_base = d["siteBaseHostAddress"]
        post_id = d["id"]
        if post_id == mse_sandbox_id and site_base == "meta.stackexchange.com":
            return  # don't check meta sandbox, it's full of weird posts
        self.queue_modify_lock.acquire()
        if site_base in self.queue:
            self.queue[site_base].append(post_id)
        else:
            self.queue[site_base] = [post_id]
        self.queue_modify_lock.release()

        if should_check_site:
            self.make_api_call_for_site(site_base)
        else:
            self.check_queue()
        return

    def check_queue(self):
        for site, values in self.queue.iteritems():
            if site in self.special_cases:
                if len(values) >= self.special_cases[site]:
                    self.make_api_call_for_site(site)
                    return
            if site in self.time_sensitive:
                if len(values) >= 1 and datetime.utcnow().hour in range(4, 12):
                    self.make_api_call_for_site(site)
                    return

        # if we don't have any sites with their queue filled, take the first one without a special case
        for site, values in self.queue.iteritems():
            if site not in self.special_cases and len(values) >= self.threshold:
                self.make_api_call_for_site(site)
                return

        # We're not making an API request, so explicitly store the queue
        self.queue_modify_lock.acquire()
        store_bodyfetcher_queue()
        self.queue_modify_lock.release()

    def print_queue(self):
        return '\n'.join("{0}: {1}".format(key, str(len(values))) for (key, values) in self.queue.iteritems())

    def make_api_call_for_site(self, site):
        if site not in self.queue:
            return

        self.queue_modify_lock.acquire()
        new_post_ids = self.queue.pop(site)
        store_bodyfetcher_queue()
        self.queue_modify_lock.release()

        self.max_ids_modify_lock.acquire()

        if site in self.previous_max_ids and max(new_post_ids) > self.previous_max_ids[site]:
            previous_max_id = self.previous_max_ids[site]
            intermediate_posts = range(previous_max_id + 1, max(new_post_ids))

            # We don't want to go over the 100-post API cutoff, so take the last
            # (100-len(new_post_ids)) from intermediate_posts

            intermediate_posts = intermediate_posts[(len(new_post_ids) - 100):]

            # new_post_ids could contain edited posts, so merge it back in
            combined = intermediate_posts + new_post_ids

            # Could be duplicates, so uniquify
            posts = list(set(combined))
        else:
            posts = new_post_ids

        try:
            if max(new_post_ids) > self.previous_max_ids[site]:
                self.previous_max_ids[site] = max(new_post_ids)
                store_bodyfetcher_max_ids()
        except KeyError:
            self.previous_max_ids[site] = max(new_post_ids)
            store_bodyfetcher_max_ids()

        self.max_ids_modify_lock.release()

        print("New IDs / Hybrid Intermediate IDs for {0}:".format(site))
        print(sorted(new_post_ids))
        print(sorted(posts))

        question_modifier = ""
        pagesize_modifier = ""

        if site == "stackoverflow.com":
            # Not all SO questions are shown in the realtime feed. We now
            # fetch all recently modified SO questions to work around that.
            if self.last_activity_date != 0:
                pagesize = "50"
            else:
                pagesize = "25"

            pagesize_modifier = "&pagesize={pagesize}" \
                                "&min={time_length}".format(pagesize=pagesize, time_length=str(self.last_activity_date))
        else:
            question_modifier = "/{0}".format(";".join(str(post) for post in posts))

        url = "https://api.stackexchange.com/2.2/questions{q_modifier}?site={site}" \
              "&filter=!)E0g*ODaEZ(SgULQhYvCYbu09*ss(bKFdnTrGmGUxnqPptuHP&key=IAkbitmze4B8KpacUfLqkw((" \
              "{optional_min_query_param}".format(q_modifier=question_modifier, site=site,
                                                  optional_min_query_param=pagesize_modifier)

        # wait to make sure API has/updates post data
        time.sleep(3)

        GlobalVars.api_request_lock.acquire()
        # Respect backoff, if we were given one
        if GlobalVars.api_backoff_time > time.time():
            time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
        try:
            time_request_made = datetime.now().strftime('%H:%M:%S')
            response = requests.get(url, timeout=20).json()
        except (requests.exceptions.Timeout, requests.ConnectionError, Exception):
            # Any failure in the request being made (timeout or otherwise) should be added back to
            # the queue.
            self.queue_modify_lock.acquire()
            if site in self.queue:
                self.queue[site].extend(posts)
            else:
                self.queue[site] = posts
            self.queue_modify_lock.release()
            GlobalVars.api_request_lock.release()
            return

        self.api_data_lock.acquire()
        add_or_update_api_data(site)
        self.api_data_lock.release()

        message_hq = ""
        if "quota_remaining" in response:
            if response["quota_remaining"] - GlobalVars.apiquota >= 5000 and GlobalVars.apiquota >= 0:
                GlobalVars.charcoal_hq.send_message("API quota rolled over with {0} requests remaining. "
                                                    "Current quota: {1}.".format(GlobalVars.apiquota,
                                                                                 response["quota_remaining"]))
                sorted_calls_per_site = sorted(GlobalVars.api_calls_per_site.items(), key=itemgetter(1), reverse=True)
                api_quota_used_per_site = ""
                for site_name, quota_used in sorted_calls_per_site:
                    sanatized_site_name = site_name.replace('.com', '').replace('.stackexchange', '')
                    api_quota_used_per_site += sanatized_site_name + ": {0}\n".format(str(quota_used))
                api_quota_used_per_site = api_quota_used_per_site.strip()
                GlobalVars.charcoal_hq.send_message(api_quota_used_per_site, False)
                clear_api_data()
            if response["quota_remaining"] == 0:
                GlobalVars.charcoal_hq.send_message("API reports no quota left!  May be a glitch.")
                GlobalVars.charcoal_hq.send_message(str(response))  # No code format for now?
            if GlobalVars.apiquota == -1:
                GlobalVars.charcoal_hq.send_message("Restart: API quota is {quota}."
                                                    .format(quota=response["quota_remaining"]))
            GlobalVars.apiquota = response["quota_remaining"]
        else:
            message_hq = "The quota_remaining property was not in the API response."

        if "error_message" in response:
            message_hq += " Error: {} at {} UTC.".format(response["error_message"], time_request_made)
            if "error_id" in response and response["error_id"] == 502:
                if GlobalVars.api_backoff_time < time.time() + 12:  # Add a backoff of 10 + 2 seconds as a default
                    GlobalVars.api_backoff_time = time.time() + 12
            message_hq += " Backing off on requests for the next 12 seconds."

        if "backoff" in response:
            if GlobalVars.api_backoff_time < time.time() + response["backoff"]:
                GlobalVars.api_backoff_time = time.time() + response["backoff"]

        GlobalVars.api_request_lock.release()

        if len(message_hq) > 0:
            GlobalVars.charcoal_hq.send_message(message_hq.strip())

        if "items" not in response:
            return

        if site == "stackoverflow.com":
            items = response["items"]
            if len(items) > 0 and "last_activity_date" in items[0]:
                self.last_activity_date = items[0]["last_activity_date"]

        num_scanned = 0
        start_time = time.time()

        for post in response["items"]:
            if "title" not in post or "body" not in post:
                continue

            post['site'] = site
            post_ = Post(api_response=post)

            num_scanned += 1

            is_spam, reason, why = check_if_spam(post_)

            if is_spam:
                try:
                    handle_spam(post=post_,
                                reasons=reason,
                                why=why)
                except:
                    pass

            try:
                for answer in post["answers"]:
                    num_scanned += 1
                    answer["IsAnswer"] = True  # Necesssary for Post object
                    answer["title"] = ""  # Necessary for proper Post object creation
                    answer["site"] = site  # Necessary for proper Post object creation
                    answer_ = Post(api_response=answer)

                    is_spam, reason, why = check_if_spam(post_)
                    if is_spam:
                        try:
                            handle_spam(answer_,
                                        reasons=reason,
                                        why=why)
                        except:
                            pass
            except:
                pass

        end_time = time.time()
        GlobalVars.posts_scan_stats_lock.acquire()
        GlobalVars.num_posts_scanned += num_scanned
        GlobalVars.post_scan_time += end_time - start_time
        GlobalVars.posts_scan_stats_lock.release()
        return
