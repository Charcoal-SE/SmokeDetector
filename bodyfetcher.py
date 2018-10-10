# coding=utf-8
from spamhandling import handle_spam, check_if_spam
from datahandling import (add_or_update_api_data, clear_api_data, store_bodyfetcher_queue, store_bodyfetcher_max_ids,
                          store_queue_timings)
from chatcommunicate import tell_rooms_with
from globalvars import GlobalVars
from operator import itemgetter
from datetime import datetime
import json
import time
import threading
import requests
import copy
from classes import Post, PostParseError
from helpers import log
from itertools import chain


# noinspection PyClassHasNoInit,PyBroadException
class BodyFetcher:
    queue = {}
    previous_max_ids = {}
    queue_timings = {}

    special_cases = {
        "math.stackexchange.com": 1,
        "pt.stackoverflow.com": 10,
        "ru.stackoverflow.com": 10,
        "serverfault.com": 1,
        "blender.stackexchange.com": 5,
        "codegolf.stackexchange.com": 1,
        "codereview.stackexchange.com": 5,
        "es.stackoverflow.com": 5,
        "physics.stackexchange.com": 1,
        "stackoverflow.com": 3,
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
        "medicalsciences.stackexchange.com": 1,
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
        "writing.stackexchange.com": 1,
        "android.stackexchange.com": 1,
        "anime.stackexchange.com": 1,
        "apple.stackexchange.com": 1,
        "arduino.stackexchange.com": 1,
        "bitcoin.stackexchange.com": 1,
        "bricks.stackexchange.com": 1,
        "communitybuilding.stackexchange.com": 1,
        "english.stackexchange.com": 1,
        "fitness.stackexchange.com": 1,
        "freelancing.stackexchange.com": 1,
        "gaming.stackexchange.com": 1,
        "graphicdesign.stackexchange.com": 1,
        "homebrew.stackexchange.com": 1,
        "islam.stackexchange.com": 1,
        "lifehacks.stackexchange.com": 1,
        "martialarts.stackexchange.com": 1,
        "mythology.stackexchange.com": 1,
        "pm.stackexchange.com": 1,
        "poker.stackexchange.com": 1,
        "security.stackexchange.com": 1,
        "skeptics.stackexchange.com": 1,
        "sports.stackexchange.com": 1,
        "superuser.com": 1,
        "windowsphone.stackexchange.com": 1,
        "workplace.stackexchange.com": 1,
        "interpersonal.stackexchange.com": 1,
        "askubuntu.com": 1,
        "hinduism.stackexchange.com": 1,
        "buddhism.stackexchange.com": 1,
        "judaism.stackexchange.com": 1,
        "crafts.stackexchange.com": 1
    }

    time_sensitive = ["security.stackexchange.com", "movies.stackexchange.com",
                      "mathoverflow.net", "gaming.stackexchange.com", "webmasters.stackexchange.com",
                      "arduino.stackexchange.com", "workplace.stackexchange.com"]

    threshold = 2

    last_activity_date = 0

    api_data_lock = threading.Lock()
    queue_modify_lock = threading.Lock()
    max_ids_modify_lock = threading.Lock()
    queue_timing_modify_lock = threading.Lock()

    def add_to_queue(self, post, should_check_site=False):
        try:
            d = json.loads(json.loads(post)["data"])
        except ValueError:
            # post didn't contain a valid JSON object in its ["data"] member
            # indicative of a server-side socket reset
            return

        site_base = d["siteBaseHostAddress"]
        post_id = d["id"]
        if (post_id == 3122 or post_id == 51812) and site_base == "meta.stackexchange.com":
            return  # don't check meta sandbox, it's full of weird posts
        self.queue_modify_lock.acquire()
        if site_base not in self.queue:
            self.queue[site_base] = {}

        # Something about how the queue is being filled is storing Post IDs in a list.
        # So, if we get here we need to make sure that the correct types are paseed.
        #
        # If the item in self.queue[site_base] is a dict, do nothing.
        # If the item in self.queue[site_base] is not a dict but is a list or a tuple, then convert to dict and
        # then replace the list or tuple with the dict.
        # If the item in self.queue[site_base] is neither a dict or a list, then explode.
        if type(self.queue[site_base]) is dict:
            pass
        elif type(self.queue[site_base]) is not dict and type(self.queue[site_base]) in [list, tuple]:
            post_list_dict = {}
            for post_list_id in self.queue[site_base]:
                post_list_dict[post_list_id] = None
            self.queue[site_base] = post_list_dict
        else:
            raise TypeError("A non-iterable is in the queue item for a given site, this will cause errors!")

        # This line only works if we are using a dict in the self.queue[site_base] object, which we should be with
        # the previous conversion code.
        self.queue[site_base][str(post_id)] = datetime.utcnow()
        self.queue_modify_lock.release()

        if GlobalVars.flovis is not None:
            GlobalVars.flovis.stage('bodyfetcher/enqueued', site_base, post_id,
                                    {sk: list(sq.keys()) for sk, sq in self.queue.items()})

        if should_check_site:
            self.make_api_call_for_site(site_base)
        else:
            self.check_queue()
        return

    def check_queue(self):
        for site, values in self.queue.items():
            if site in self.special_cases:
                if len(values) >= self.special_cases[site]:
                    self.make_api_call_for_site(site)
                    return
            if site in self.time_sensitive:
                if len(values) >= 1 and datetime.utcnow().hour in range(4, 12):
                    self.make_api_call_for_site(site)
                    return

        # if we don't have any sites with their queue filled, take the first one without a special case
        for site, values in self.queue.items():
            if site not in self.special_cases and len(values) >= self.threshold:
                self.make_api_call_for_site(site)
                return

        # We're not making an API request, so explicitly store the queue
        self.queue_modify_lock.acquire()
        store_bodyfetcher_queue()
        self.queue_modify_lock.release()

    def print_queue(self):
        return '\n'.join(["{0}: {1}".format(key, str(len(values))) for (key, values) in self.queue.items()])

    def make_api_call_for_site(self, site):
        if site not in self.queue:
            return

        self.queue_modify_lock.acquire()
        new_posts = self.queue.pop(site)
        store_bodyfetcher_queue()
        self.queue_modify_lock.release()

        new_post_ids = [int(k) for k in new_posts.keys()]

        if GlobalVars.flovis is not None:
            for post_id in new_post_ids:
                GlobalVars.flovis.stage('bodyfetcher/api_request', site, post_id,
                                        {'site': site, 'posts': list(new_posts.keys())})

        self.queue_timing_modify_lock.acquire()
        post_add_times = [v for k, v in new_posts.items()]
        pop_time = datetime.utcnow()

        for add_time in post_add_times:
            try:
                seconds_in_queue = (pop_time - add_time).total_seconds()
                if site in self.queue_timings:
                    self.queue_timings[site].append(seconds_in_queue)
                else:
                    self.queue_timings[site] = [seconds_in_queue]
            except KeyError:  # XXX: Any other possible exception?
                continue  # Skip to next item if we've got invalid data or missing values.

        store_queue_timings()

        self.queue_timing_modify_lock.release()
        self.max_ids_modify_lock.acquire()

        if site in self.previous_max_ids and max(new_post_ids) > self.previous_max_ids[site]:
            previous_max_id = self.previous_max_ids[site]
            intermediate_posts = range(previous_max_id + 1, max(new_post_ids))

            # We don't want to go over the 100-post API cutoff, so take the last
            # (100-len(new_post_ids)) from intermediate_posts

            intermediate_posts = intermediate_posts[(100 - len(new_post_ids)):]

            # new_post_ids could contain edited posts, so merge it back in
            combined = chain(intermediate_posts, new_post_ids)

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

        log('debug', "New IDs / Hybrid Intermediate IDs for {}:".format(site))
        if len(new_post_ids) > 30:
            log('debug', "{} +{} more".format(sorted(new_post_ids)[:30], len(new_post_ids) - 30))
        else:
            log('debug', sorted(new_post_ids))
        if len(new_post_ids) == len(posts):
            log('debug', "[ *Identical* ]")
        elif len(posts) > 30:
            log('debug', "{} +{} more".format(sorted(posts)[:30], len(posts) - 30))
        else:
            log('debug', sorted(posts))

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
            question_modifier = "/{0}".format(";".join([str(post) for post in posts]))

        url = "https://api.stackexchange.com/2.2/questions{q_modifier}?site={site}" \
              "&filter=!*xq08dCDNr)PlxxXfaN8ntivx(BPlY_8XASyXLX-J7F-)VK*Q3KTJVkvp*&key=IAkbitmze4B8KpacUfLqkw((" \
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
                self.queue[site].update(new_posts)
            else:
                self.queue[site] = new_posts
            self.queue_modify_lock.release()
            GlobalVars.api_request_lock.release()
            return

        self.api_data_lock.acquire()
        add_or_update_api_data(site)
        self.api_data_lock.release()

        message_hq = ""
        if "quota_remaining" in response:
            if response["quota_remaining"] - GlobalVars.apiquota >= 5000 and GlobalVars.apiquota >= 0:
                tell_rooms_with("debug", "API quota rolled over with {0} requests remaining. "
                                         "Current quota: {1}.".format(GlobalVars.apiquota,
                                                                      response["quota_remaining"]))

                sorted_calls_per_site = sorted(GlobalVars.api_calls_per_site.items(), key=itemgetter(1), reverse=True)
                api_quota_used_per_site = ""
                for site_name, quota_used in sorted_calls_per_site:
                    sanatized_site_name = site_name.replace('.com', '').replace('.stackexchange', '')
                    api_quota_used_per_site += sanatized_site_name + ": {0}\n".format(str(quota_used))
                api_quota_used_per_site = api_quota_used_per_site.strip()

                tell_rooms_with("debug", api_quota_used_per_site)
                clear_api_data()
            if response["quota_remaining"] == 0:
                tell_rooms_with("debug", "API reports no quota left!  May be a glitch.")
                tell_rooms_with("debug", str(response))  # No code format for now?
            if GlobalVars.apiquota == -1:
                tell_rooms_with("debug", "Restart: API quota is {quota}."
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
            message_hq += " Previous URL: `{}`".format(url)

        if "backoff" in response:
            if GlobalVars.api_backoff_time < time.time() + response["backoff"]:
                GlobalVars.api_backoff_time = time.time() + response["backoff"]

        GlobalVars.api_request_lock.release()

        if len(message_hq) > 0:
            tell_rooms_with("debug", message_hq.strip())

        if "items" not in response:
            return

        if site == "stackoverflow.com":
            items = response["items"]
            if len(items) > 0 and "last_activity_date" in items[0]:
                self.last_activity_date = items[0]["last_activity_date"]

        num_scanned = 0
        start_time = time.time()

        for post in response["items"]:
            pnb = copy.deepcopy(post)
            if 'body' in pnb:
                pnb['body'] = 'Present, but truncated'
            if 'answers' in pnb:
                del pnb['answers']

            if "title" not in post or "body" not in post:
                if GlobalVars.flovis is not None and 'question_id' in post:
                    GlobalVars.flovis.stage('bodyfetcher/api_response/no_content', site, post['question_id'], pnb)
                continue

            post['site'] = site
            try:
                post['edited'] = (post['creation_date'] != post['last_edit_date'])
            except KeyError:
                post['edited'] = False  # last_edit_date not present = not edited

            try:
                post_ = Post(api_response=post)
            except PostParseError as err:
                log('error', 'Error {0} when parsing post: {1!r}'.format(err, post_))
                if GlobalVars.flovis is not None and 'question_id' in post:
                    GlobalVars.flovis.stage('bodyfetcher/api_response/error', site, post['question_id'], pnb)
                continue

            num_scanned += 1

            is_spam, reason, why = check_if_spam(post_)

            if is_spam:
                try:
                    if GlobalVars.flovis is not None and 'question_id' in post:
                        GlobalVars.flovis.stage('bodyfetcher/api_response/spam', site, post['question_id'],
                                                {'post': pnb, 'check_if_spam': [is_spam, reason, why]})
                    handle_spam(post=post_,
                                reasons=reason,
                                why=why)
                except Exception as e:
                    log('error', "Exception in handle_spam:", e)
            elif GlobalVars.flovis is not None and 'question_id' in post:
                GlobalVars.flovis.stage('bodyfetcher/api_response/not_spam', site, post['question_id'],
                                        {'post': pnb, 'check_if_spam': [is_spam, reason, why]})

            try:
                if "answers" not in post:
                    pass
                else:
                    for answer in post["answers"]:
                        anb = copy.deepcopy(answer)
                        if 'body' in anb:
                            anb['body'] = 'Present, but truncated'

                        num_scanned += 1
                        answer["IsAnswer"] = True  # Necesssary for Post object
                        answer["title"] = ""  # Necessary for proper Post object creation
                        answer["site"] = site  # Necessary for proper Post object creation
                        try:
                            answer['edited'] = (answer['creation_date'] != answer['last_edit_date'])
                        except KeyError:
                            answer['edited'] = False  # last_edit_date not present = not edited
                        answer_ = Post(api_response=answer, parent=post_)

                        is_spam, reason, why = check_if_spam(answer_)
                        if is_spam:
                            try:
                                if GlobalVars.flovis is not None and 'answer_id' in answer:
                                    GlobalVars.flovis.stage('bodyfetcher/api_response/spam', site, answer['answer_id'],
                                                            {'post': anb, 'check_if_spam': [is_spam, reason, why]})
                                handle_spam(answer_,
                                            reasons=reason,
                                            why=why)
                            except Exception as e:
                                log('error', "Exception in handle_spam:", e)
                        elif GlobalVars.flovis is not None and 'answer_id' in answer:
                            GlobalVars.flovis.stage('bodyfetcher/api_response/not_spam', site, answer['answer_id'],
                                                    {'post': anb, 'check_if_spam': [is_spam, reason, why]})

            except Exception as e:
                log('error', "Exception handling answers:", e)

        end_time = time.time()
        GlobalVars.posts_scan_stats_lock.acquire()
        GlobalVars.num_posts_scanned += num_scanned
        GlobalVars.post_scan_time += end_time - start_time
        GlobalVars.posts_scan_stats_lock.release()
        return
