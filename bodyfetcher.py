# coding=utf-8
from spamhandling import handle_spam, check_if_spam
from datahandling import (add_or_update_api_data, clear_api_data, store_bodyfetcher_queue, store_bodyfetcher_max_ids,
                          add_queue_timing_data)
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
from tasks import Tasks


# noinspection PyClassHasNoInit,PyBroadException
class BodyFetcher:
    queue = {}
    previous_max_ids = {}

    # special_cases are the minimum number of posts, for each of the specified sites, which
    # need to be in the queue prior to feching posts.
    # The number of questions we fetch each day per site is the total of
    #   new questions + new answers + edits.
    # Stack Overflow is handled specially. It's know that some SO edits/new posts don't
    #   appear on the WebSocket.
    # Queue depths were last comprehensively adjusted on 2015-12-30.
    special_cases = {
        # 2020-11-02:
        # Request numbers pre 2020-11-02 are very low due to a now fixed bug.
        #
        #                                                                pre                   sum of requests
        #                                               questions    2020-11-02   2020-02-19    2020-10-28 to
        #                                                per day       setting     requests      2020-11-02
        # "stackoverflow.com": 3,                   # _  6,816            3          360            4,365
        # "math.stackexchange.com": 2,              # _    596            1          473            6,346
        # "ru.stackoverflow.com": 2,                # _    230           10           13              145
        # "askubuntu.com": ,                        # _    140            1           88            1,199
        # "es.stackoverflow.com": 2,                # _    138            5           25              225
        # "superuser.com": ,                        # _    122            1           87            1,038
        # "physics.stackexchange.com": ,            # _     90            1           76            1,161
        # "stats.stackexchange.com": 2,             # _     82            5           16              151
        # "pt.stackoverflow.com": 2,                # _     73           10            7               75
        # "unix.stackexchange.com": ,               # _     72            1           76              772
        # "electronics.stackexchange.com": ,        # _     69            1           46              723
        # "serverfault.com": ,                      # _     62            1           43              582
        # "tex.stackexchange.com": 2,               # _     60            5            8               98
        # "blender.stackexchange.com": 2,           # _     59            5            8               85
        # "salesforce.stackexchange.com": ,         # _     49            1           47              472
        # "gis.stackexchange.com": 2,               # _     46            3           15              166
        # "mathoverflow.net" (time_sensitive)       # _     37            -           33              511
        # "english.stackexchange.com": ,            # _     36            1           34              382
        # "magento.stackexchange.com": 2,           # _     34            3            5               93
        # "ell.stackexchange.com": ,                # _     33            1           24              365
        # "wordpress.stackexchange.com": ,          # _     29            1           30              283
        # "apple.stackexchange.com": ,              # _     29            1           46              294
        # "diy.stackexchange.com": ,                # _     26            1           24              306
        # "mathematica.stackexchange.com": ,        # _     25            1           21              384
        # "dba.stackexchange.com": ,                # _     23            1           31              343
        # "datascience.stackexchange.com": ,        # _     21            1           17              220
        # "chemistry.stackexchange.com": ,          # _     20            1           20              140
        # "security.stackexchange.com": ,           # _     18            1           15              238
        # "codereview.stackexchange.com": ,         # _     18            5            2               39
        #  The only reason this is the cut-off is that it was the last in the existing list
        #    as of 2020-11-01.
    }

    time_sensitive = ["security.stackexchange.com", "movies.stackexchange.com",
                      "mathoverflow.net", "gaming.stackexchange.com", "webmasters.stackexchange.com",
                      "arduino.stackexchange.com", "workplace.stackexchange.com"]

    threshold = 1

    last_activity_date = 0

    api_data_lock = threading.Lock()
    queue_lock = threading.Lock()
    max_ids_modify_lock = threading.Lock()
    queue_timing_modify_lock = threading.Lock()

    def add_to_queue(self, hostname, question_id, should_check_site=False):
        # For the Sandbox questions on MSE, we choose to ignore the entire question and all answers.
        ignored_mse_questions = [
            3122,    # Formatting Sandbox
            51812,   # The API sandbox
            296077,  # Sandbox archive
        ]
        if question_id in ignored_mse_questions and hostname == "meta.stackexchange.com":
            return  # don't check meta sandbox, it's full of weird posts

        with self.queue_lock:
            if hostname not in self.queue:
                self.queue[hostname] = {}

            # Something about how the queue is being filled is storing Post IDs in a list.
            # So, if we get here we need to make sure that the correct types are paseed.
            #
            # If the item in self.queue[hostname] is a dict, do nothing.
            # If the item in self.queue[hostname] is not a dict but is a list or a tuple, then convert to dict and
            # then replace the list or tuple with the dict.
            # If the item in self.queue[hostname] is neither a dict or a list, then explode.
            if type(self.queue[hostname]) is dict:
                pass
            elif type(self.queue[hostname]) in [list, tuple]:
                post_list_dict = {}
                for post_list_id in self.queue[hostname]:
                    post_list_dict[str(post_list_id)] = None
                self.queue[hostname] = post_list_dict
            else:
                raise TypeError("A non-iterable is in the queue item for a given site, this will cause errors!")

            # This line only works if we are using a dict in the self.queue[hostname] object, which we should be with
            # the previous conversion code.
            self.queue[hostname][str(question_id)] = datetime.utcnow()
            flovis_dict = None
            if GlobalVars.flovis is not None:
                flovis_dict = {sk: list(sq.keys()) for sk, sq in self.queue.items()}

        if flovis_dict is not None:
            GlobalVars.flovis.stage('bodyfetcher/enqueued', hostname, question_id, flovis_dict)

        if should_check_site:
            self.make_api_call_for_site(hostname)
        else:
            self.check_queue()
        return

    def check_queue(self):
        # This should be called once in a new Thread every time we add an entry to the queue. Thus, we
        # should only need to process a single queue entry in order to keep the queue from containing
        # entries which are qualified for processing, but which haven't been processed. However, that
        # doesn't account for the possibility of things going wrong and/or implementing some other
        # way to qualify other than the depth of the queue for a particular site (e.g. time in queue).

        # We use a copy of the queue in order to allow the queue to be changed in other threads.
        # This is OK, because self.make_api_call_for_site(site) verifies that the site
        # is still in the queue.
        with self.queue_lock:
            queue_copy = self.queue
        handled_sites = []
        # Handle sites listed in special cases and as time_sensitive
        for site, values in queue_copy.items():
            if site in self.special_cases:
                if len(values) >= self.special_cases[site]:
                    handled_sites.append(site)
                    self.make_api_call_for_site(site)
                    continue
            if site in self.time_sensitive:
                if len(values) >= 1 and datetime.utcnow().hour in range(4, 12):
                    handled_sites.append(site)
                    self.make_api_call_for_site(site)

        # Remove the sites which we've handled from our copy of the queue.
        for site in handled_sites:
            queue_copy.pop(site, None)

        # if we don't have any sites with their queue filled, take the first one without a special case
        for site, values in queue_copy.items():
            if site not in self.special_cases and len(values) >= self.threshold:
                handled_sites.append(site)
                self.make_api_call_for_site(site)

        if not handled_sites:
            # We're not making an API request, so explicitly store the queue.
            Tasks.do(store_bodyfetcher_queue)

    def print_queue(self):
        return '\n'.join(["{0}: {1}".format(key, str(len(values))) for (key, values) in self.queue.items()])

    def make_api_call_for_site(self, site):
        with self.queue_lock:
            new_posts = self.queue.pop(site, None)
        if new_posts is None:
            # site was not in the queue
            return
        Tasks.do(store_bodyfetcher_queue)

        new_post_ids = [int(k) for k in new_posts.keys()]

        if GlobalVars.flovis is not None:
            for post_id in new_post_ids:
                GlobalVars.flovis.stage('bodyfetcher/api_request', site, post_id,
                                        {'site': site, 'posts': list(new_posts.keys())})

        # Add queue timing data
        with self.queue_timing_modify_lock:
            post_add_times = [v for k, v in new_posts.items()]
            pop_time = datetime.utcnow()
            for add_time in post_add_times:
                seconds_in_queue = (pop_time - add_time).total_seconds()
                add_queue_timing_data(site, seconds_in_queue)

        with self.max_ids_modify_lock:
            if site in self.previous_max_ids and max(new_post_ids) > self.previous_max_ids[site]:
                previous_max_id = self.previous_max_ids[site]
                intermediate_posts = range(previous_max_id + 1, max(new_post_ids))

                # We don't want to go over the 100-post API cutoff, so take the last
                # (100-len(new_post_ids)) from intermediate_posts

                intermediate_posts = intermediate_posts[-(100 - len(new_post_ids)):]

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
        pagesize_modifier = {}

        if site == "stackoverflow.com":
            # Not all SO questions are shown in the realtime feed. We now
            # fetch all recently modified SO questions to work around that.
            if self.last_activity_date != 0:
                pagesize = "50"
            else:
                pagesize = "25"

            pagesize_modifier = {
                'pagesize': pagesize,
                'min': str(self.last_activity_date)
            }
        else:
            question_modifier = "/{0}".format(";".join([str(post) for post in posts]))

        url = "https://api.stackexchange.com/2.2/questions{}".format(question_modifier)
        params = {
            'filter': '!1rs)sUKylwB)8isvCRk.xNu71LnaxjnPS12*pX*CEOKbPFwVFdHNxiMa7GIVgzDAwMa',
            'key': 'IAkbitmze4B8KpacUfLqkw((',
            'site': site
        }
        params.update(pagesize_modifier)

        # wait to make sure API has/updates post data
        time.sleep(3)

        with GlobalVars.api_request_lock:
            # Respect backoff, if we were given one
            if GlobalVars.api_backoff_time > time.time():
                time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
            try:
                time_request_made = datetime.utcnow().strftime('%H:%M:%S')
                response = requests.get(url, params=params, timeout=20).json()
            except (requests.exceptions.Timeout, requests.ConnectionError, Exception):
                # Any failure in the request being made (timeout or otherwise) should be added back to
                # the queue.
                with self.queue_lock:
                    if site in self.queue:
                        self.queue[site].update(new_posts)
                    else:
                        self.queue[site] = new_posts
                return

            with self.api_data_lock:
                add_or_update_api_data(site)

            message_hq = ""
            with GlobalVars.apiquota_rw_lock:
                if "quota_remaining" in response:
                    quota_remaining = response["quota_remaining"]
                    if quota_remaining - GlobalVars.apiquota >= 5000 and GlobalVars.apiquota >= 0 \
                            and quota_remaining > 39980:
                        tell_rooms_with("debug", "API quota rolled over with {0} requests remaining. "
                                                 "Current quota: {1}.".format(GlobalVars.apiquota,
                                                                              quota_remaining))

                        sorted_calls_per_site = sorted(GlobalVars.api_calls_per_site.items(), key=itemgetter(1),
                                                       reverse=True)
                        api_quota_used_per_site = ""
                        for site_name, quota_used in sorted_calls_per_site:
                            sanatized_site_name = site_name.replace('.com', '').replace('.stackexchange', '')
                            api_quota_used_per_site += sanatized_site_name + ": {0}\n".format(str(quota_used))
                        api_quota_used_per_site = api_quota_used_per_site.strip()

                        tell_rooms_with("debug", api_quota_used_per_site)
                        clear_api_data()
                    if quota_remaining == 0:
                        tell_rooms_with("debug", "API reports no quota left!  May be a glitch.")
                        tell_rooms_with("debug", str(response))  # No code format for now?
                    if GlobalVars.apiquota == -1:
                        tell_rooms_with("debug", "Restart: API quota is {quota}."
                                                 .format(quota=quota_remaining))
                    GlobalVars.apiquota = quota_remaining
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

        if len(message_hq) > 0 and "site is required" not in message_hq:
            message_hq = message_hq.strip()
            if len(message_hq) > 500:
                message_hq = "\n" + message_hq
            tell_rooms_with("debug", message_hq)

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
        scan_time = end_time - start_time
        GlobalVars.PostScanStat.add_stat(num_scanned, scan_time)
        return
