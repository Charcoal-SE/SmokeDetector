# coding=utf-8
import json
import time
import threading
import copy
from itertools import chain
from operator import itemgetter
from datetime import datetime

import requests
import psutil

from globalvars import GlobalVars
from spamhandling import handle_spam, check_if_spam
from datahandling import (add_or_update_api_data, clear_api_data, schedule_store_bodyfetcher_queue,
                          schedule_store_bodyfetcher_max_ids, add_queue_timing_data)
from chatcommunicate import tell_rooms_with
from classes import Post, PostParseError
from helpers import (log, log_current_thread, append_to_current_thread_name,
                     convert_new_scan_to_spam_result_if_new_reasons, add_to_global_bodyfetcher_queue_in_new_thread,
                     get_se_api_default_params_questions_answers_posts_add_site, get_se_api_url_for_route)
import recently_scanned_posts as rsp
from tasks import Tasks


# noinspection PyClassHasNoInit,PyBroadException
class BodyFetcher:
    queue_lock = threading.Lock()
    queue = {}

    max_ids_lock = threading.Lock()
    previous_max_ids = {}

    posts_in_process_lock = threading.Lock()
    posts_in_process = {}

    SMOKEDETECTOR_MAX_QUOTA = 80000
    QUOTA_ROLLOVER_DETECTION_THRESHOLD = SMOKEDETECTOR_MAX_QUOTA - 20
    QUOTA_ROLLOVER_DETECTION_MINIMUM_DIFFERENCE = 5000

    cpu_count = psutil.cpu_count()
    MAX_SCAN_THREADS_DIFFERENCE_TO_CPU_COUNT = 1
    max_scan_thread_count = cpu_count + MAX_SCAN_THREADS_DIFFERENCE_TO_CPU_COUNT
    scan_thread_count_semaphore = threading.BoundedSemaphore(value=max_scan_thread_count)
    THREAD_STARVATION_POST_IN_CHAT_AFTER_ELAPSED_TIME = 3 * 60
    MIN_THREADS_NOT_CONSUMED_BY_SAME_SITE = 1 if max_scan_thread_count > 2 else 0
    MAX_THREADS_PER_SITE = max_scan_thread_count - MIN_THREADS_NOT_CONSUMED_BY_SAME_SITE

    IGNORED_IGNORED_SPAM_CHECKS_IF_WORSE_SPAM = [
        "post has already been reported",
    ]
    LAUNCH_PROCESSING_THREAD_MAXIMUM_CPU_USE_THRESHOLD = 98
    DEFAULT_PER_SITE_PROCESSING_THREAD_LIMIT = MAX_THREADS_PER_SITE
    POST_SCAN_PERFORMANCE_LOW_VALUE_DISPLAY_THRESHOLD = 0.015
    per_site_processing_thread_limits = {
        'stackoverflow.com': MAX_THREADS_PER_SITE,
    }

    per_site_processing_thread_locks_lock = threading.Lock()
    per_site_processing_thread_locks = {}
    per_site_processing_thread_locks_delayed_warnings = {}

    PER_SITE_THREAD_STARVATION_POST_IN_CHAT_AFTER_ELAPSED_TIME = 3 * 60

    CPU_STARVATION_POST_IN_CHAT_AFTER_ELAPSED_TIME = 3 * 60
    SITES_NOT_TO_REREQUEST_POST_DUE_TO_POST_SCAN_CONFLICT = [
        'stackoverflow.com',
    ]

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
        # "stackoverflow.com": 2,                   # _  6,816            3          360            4,365
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
    last_activity_date_lock = threading.Lock()
    ACTIVITY_DATE_EXTRA_EARLIER_MS_TO_FETCH = 6 * 60 * 1000  # 6 minutes in milliseconds; is beyond edit grace period

    api_data_lock = threading.Lock()

    check_queue_lock = threading.Lock()
    # CPU starvation updates are under the check_queue_lock
    cpu_starvation_last_thread_not_launched_timestamp = None
    cpu_starvation_posted_in_chat_timestamp = None

    thread_starvation_delayed_warnings_lock = threading.RLock()
    thread_starvation_delayed_warnings = None

    def add_to_queue(self, hostname, question_id, should_check_site=False, source=None):
        # For the Sandbox questions on MSE, we choose to ignore the entire question and all answers.
        ignored_mse_questions = [
            3122,    # Formatting Sandbox
            51812,   # The API sandbox
            296077,  # Sandbox archive
        ]
        if question_id in ignored_mse_questions and hostname == "meta.stackexchange.com":
            return  # don't check meta sandbox, it's full of weird posts

        thread_stats = {
            'thread_count': 1,
            'source_EditWatcher': 1 if 'EditWatcher' in source else 0,
            'source_155-questions-active': 1 if '155-questions-active' in source else 0,
            'source_BF_re-reqest': 1 if 'BodyFetcher re-reqest' in source else 0,
            'all_errors': 0,
            'high_CPU': 0,
            'thread_limit': 0,
            'threads_limited_non_SO': 0,
            'threads_limited_SO': 0,
            'api_calls': 0,
        }

        try:
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

                # This line only works if we are using a dict in the self.queue[hostname] object, which we
                # should be with the previous conversion code.
                self.queue[hostname][str(question_id)] = datetime.utcnow()
                flovis_dict = None
                if GlobalVars.flovis is not None:
                    flovis_dict = {sk: list(sq.keys()) for sk, sq in self.queue.items()}

            if flovis_dict is not None:
                GlobalVars.flovis.stage('bodyfetcher/enqueued', hostname, question_id, flovis_dict)

            have_scan_thread_count_lock = False
            try:
                have_scan_thread_count_lock = self.scan_thread_count_semaphore.acquire(blocking=False)
                if not have_scan_thread_count_lock:
                    # There are already too many scan threads.
                    if not self.send_thread_starvation_warning_if_appropriate():
                        log_current_thread('info', "Already at maximum scan threads"
                                                   + " ({}).".format(self.max_scan_thread_count)
                                                   + " Not starting an additional scan thread.")
                    thread_stats['thread_limit'] += 1
                    return
                if should_check_site:
                    # The call to add_to_queue indicated that the site should be immediately processed.
                    if self.acquire_site_processing_lock(hostname, thread_stats):
                        try:
                            with self.queue_lock:
                                new_posts = self.queue.pop(hostname, None)
                            if new_posts:
                                schedule_store_bodyfetcher_queue()
                                self.make_api_call_for_site_and_restore_thread_name(hostname, new_posts, thread_stats)
                        except Exception:
                            raise
                        finally:
                            # We're done processing the site, so release the processing lock.
                            self.release_site_processing_lock(hostname)

                site_and_posts = True
                while site_and_posts:
                    try:
                        site_and_posts = self.get_first_queue_item_to_process(thread_stats)
                        if site_and_posts:
                            schedule_store_bodyfetcher_queue()
                            self.make_api_call_for_site_and_restore_thread_name(*site_and_posts, thread_stats)
                    except Exception:
                        raise
                    finally:
                        # We're done processing the site, so release the processing lock.
                        if site_and_posts and site_and_posts is not True:
                            self.release_site_processing_lock(site_and_posts[0])
            except Exception:
                raise
            finally:
                if have_scan_thread_count_lock:
                    self.scan_thread_count_semaphore.release()
        except Exception:
            thread_stats['all_errors'] += 1
            raise
        finally:
            GlobalVars.PostScanStat.add(thread_stats)

    def make_api_call_for_site_and_restore_thread_name(self, site, new_posts, thread_stats):
        self.thread_starvation_warning_thread_launched()
        current_thread = threading.current_thread()
        append_to_current_thread_name(('\n --> processing site:'
                                       ' {}:: posts: {}').format(site, [key for key in new_posts.keys()]))
        thread_name_to_restore = current_thread.name
        self.make_api_call_for_site(site, new_posts, thread_stats)
        current_thread.name = thread_name_to_restore

    def get_site_thread_limit(self, site):
        return self.per_site_processing_thread_limits.get(site, None) or self.DEFAULT_PER_SITE_PROCESSING_THREAD_LIMIT

    def acquire_site_processing_lock(self, site, thread_stats):
        have_acquired_lock = False
        try:
            with self.per_site_processing_thread_locks_lock:
                site_semaphore = self.per_site_processing_thread_locks.get(site, None)
                if site_semaphore is None:
                    semaphore_count = self.get_site_thread_limit(site)
                    site_semaphore = threading.BoundedSemaphore(value=semaphore_count)
                    self.per_site_processing_thread_locks[site] = site_semaphore
                have_acquired_lock = site_semaphore.acquire(blocking=False)
                if have_acquired_lock:
                    self.site_thread_starvation_warning_thread_launched(site)
                else:
                    if site == 'stackoverflow.com':
                        thread_stats['threads_limited_SO'] += 1
                    else:
                        thread_stats['threads_limited_non_SO'] += 1
                    if not self.send_site_thread_starvation_warning_if_appropriate(site):
                        log_current_thread('info', 'Unable to obtain site processing lock for: {}'.format(site))
                return have_acquired_lock
        except Exception:
            if have_acquired_lock:
                site_semaphore.release()
            raise

    def release_site_processing_lock(self, site):
        with self.per_site_processing_thread_locks_lock:
            self.per_site_processing_thread_locks[site].release()

    def send_thread_starvation_warning_if_appropriate(self):
        now = time.time()
        min_time = now - self.THREAD_STARVATION_POST_IN_CHAT_AFTER_ELAPSED_TIME
        with self.thread_starvation_delayed_warnings_lock:
            record = self.thread_starvation_delayed_warnings
            if record is None:
                self.thread_starvation_delayed_warnings = {
                    'launched_timestamp': now,
                    'chat_timestamp': now,
                }
                return False
            launched_timestamp, chat_timestamp = (record[key] for key in ['launched_timestamp', 'chat_timestamp'])
            if (launched_timestamp < min_time and chat_timestamp < min_time):
                record['chat_timestamp'] = now
                message = ("Unable to launch scan thread due to exhausted general thread limit"
                           " of {} for {} seconds.").format(self.max_scan_thread_count,
                                                            round(now - launched_timestamp, 2))
                Tasks.do(tell_rooms_with, "debug", message)
                log('error', message)
                return True
            return False

    def thread_starvation_warning_thread_launched(self):
        with self.thread_starvation_delayed_warnings_lock:
            self.thread_starvation_delayed_warnings = None

    def send_site_thread_starvation_warning_if_appropriate(self, site):
        # The thread lock for this is the per_site_processing_thread_locks_lock
        now = time.time()
        min_time = now - self.PER_SITE_THREAD_STARVATION_POST_IN_CHAT_AFTER_ELAPSED_TIME
        record = self.per_site_processing_thread_locks_delayed_warnings.get(site, None)
        if record is None:
            self.per_site_processing_thread_locks_delayed_warnings[site] = {
                'launched_timestamp': now,
                'chat_timestamp': now,
            }
            return False
        launched_timestamp, chat_timestamp = (record[key] for key in ['launched_timestamp', 'chat_timestamp'])
        if (launched_timestamp < min_time and chat_timestamp < min_time):
            record[site]['chat_timestamp'] = now
            message = ("Unable to launch scan thread for {} due to exhausted thread limit"
                       " of {} for {} seconds.").format(site, self.get_site_thread_limit(site),
                                                        round(now - launched_timestamp, 2))
            Tasks.do(tell_rooms_with, "debug", message)
            log('error', message)
            return True
        return False

    def site_thread_starvation_warning_thread_launched(self, site):
        # The thread lock for this is the per_site_processing_thread_locks_lock
        self.per_site_processing_thread_locks_delayed_warnings.pop(site, None)

    def send_cpu_starvation_warning_if_appropriate(self):
        # The thread lock for this is the check_queue_lock
        now = time.time()
        min_time = now - self.CPU_STARVATION_POST_IN_CHAT_AFTER_ELAPSED_TIME
        not_launched_timestamp = self.cpu_starvation_last_thread_not_launched_timestamp
        if not_launched_timestamp is None:
            self.cpu_starvation_last_thread_not_launched_timestamp = now
            self.cpu_starvation_posted_in_chat_timestamp = now
            return False
        chat_timestamp = self.cpu_starvation_posted_in_chat_timestamp
        if (not_launched_timestamp < min_time and chat_timestamp < min_time):
            self.cpu_starvation_posted_in_chat_timestamp = now
            message = ("High CPU use has prevented launching additional scan threads for"
                       " {} seconds.").format(round(now - not_launched_timestamp, 2))
            Tasks.do(tell_rooms_with, "debug", message)
            log('error', message)
            return True
        return False

    def cpu_starvation_warning_thread_launched(self):
        # The thread lock for this is the check_queue_lock
        self.cpu_starvation_last_thread_not_launched_timestamp = None

    def get_first_queue_item_to_process(self, thread_stats):
        # We use a copy of the queue keys (sites) and lengths in order to allow
        # the queue to be changed in other threads.
        # Overall this results in a FIFO for sites which have reached their threshold, because
        # dicts are guaranteed to be iterated in insertion order in Python >= 3.6.
        # We use self.check_queue_lock here to fully dispatch one queued site at a time and allow
        # consolidation of multiple WebSocket events for the same real-world event.
        with self.check_queue_lock:
            site_to_handle = None
            try:
                # Getting the CPU activity also provides time for multiple potential WebSocket events to queue
                # the same post along with some time for the SE API to update and have information on the new post.
                cpu_use = psutil.cpu_percent(interval=1)
                if cpu_use > self.LAUNCH_PROCESSING_THREAD_MAXIMUM_CPU_USE_THRESHOLD:
                    # We are already maxing out the CPU.
                    # Having additional threads processing posts is counterproductive.
                    if not self.send_cpu_starvation_warning_if_appropriate():
                        log_current_thread('warning', 'CPU use is {}'.format(cpu_use)
                                                      + ', which is too high to launch an additional scan thread.')
                    thread_stats['high_CPU'] += 1
                    return None
                self.cpu_starvation_warning_thread_launched()
                special_sites = []
                is_time_sensitive_time = datetime.utcnow().hour in range(4, 12)
                with self.queue_lock:
                    sites_in_queue = {site: len(values) for site, values in self.queue.items()}
                # Get sites listed in special cases and as time_sensitive
                for site, length in sites_in_queue.items():
                    if site in self.special_cases:
                        special_sites.append(site)
                        if length >= self.special_cases[site]:
                            if self.acquire_site_processing_lock(site, thread_stats):
                                site_to_handle = site
                                break
                    if is_time_sensitive_time and site in self.time_sensitive:
                        special_sites.append(site)
                        if length >= 1:
                            if self.acquire_site_processing_lock(site, thread_stats):
                                site_to_handle = site
                                break
                else:
                    # We didn't find a special site which met the applicable threshold.
                    # Remove the sites which we've already considered from our copy of the queue's keys.
                    for site in special_sites:
                        sites_in_queue.pop(site, None)

                    # If we don't have any special sites with their queue filled, take the first
                    # one without a special case
                    for site, length in sites_in_queue.items():
                        if length >= self.threshold:
                            if self.acquire_site_processing_lock(site, thread_stats):
                                site_to_handle = site
                                break

                if site_to_handle is not None:
                    # We already have a site processing lock, so if we have new_posts, then we're good to go.
                    with self.queue_lock:
                        new_posts = self.queue.pop(site_to_handle, None)
                    if new_posts:
                        # We've identified a site and have a list of new posts to fetch.
                        return (site, new_posts)
                    else:
                        # We don't actually have any posts to process, so need to give up the site processing lock
                        # we alreadying obtained.
                        self.release_site_processing_lock(site_to_handle)
                        site_to_handle = None
                # There's no site in the queue which has met the applicable threshold.
                return None
            # We don't have a finally here, as we're only releasing upon an exception.
            except Exception:
                if site_to_handle:
                    self.release_site_processing_lock(site_to_handle)

    def print_queue(self):
        with self.queue_lock:
            if self.queue:
                return '\n'.join(["{0}: {1}".format(key, str(len(values))) for (key, values) in self.queue.items()])
            else:
                return 'The BodyFetcher queue is empty.'

    def claim_post_in_process_or_request_rescan(self, ident, site, post_id):
        with self.posts_in_process_lock:
            site_dict = self.posts_in_process.get(site, None)
            if site_dict is None:
                site_dict = {}
                self.posts_in_process[site] = site_dict
            post_dict = site_dict.get(post_id, None)
            if post_dict is None:
                post_dict = {
                    'owner': ident,
                    'first_timestamp': time.time(),
                }
                site_dict[post_id] = post_dict
                return True
            post_lock_owner = post_dict.get('owner', None)
            if post_lock_owner == ident:
                post_dict['recent_timestamp'] = time.time(),
                return True
            log('info', 'Processing prevented in thread ',
                        '{} for Post {}/{}: being processed by {}'.format(ident, site, post_id, post_lock_owner))
            if site not in self.SITES_NOT_TO_REREQUEST_POST_DUE_TO_POST_SCAN_CONFLICT:
                # For sites where we're getting all recently active questions every time, and where they have
                # substantial activity (i.e. effectively guaranteed to be within the additional time-window
                # fetched before our last_active), a rescan of the post, if it's changed, is effectively
                # guaranteed, so we don't need to specifically request that the post be rescanned.
                post_dict['rescan_requested'] = True
                post_dict['rescan_requested_by'] = ident
            return False

    def release_post_in_process_and_recan_if_requested(self, ident, site, post_id, question_id):
        with self.posts_in_process_lock:
            site_dict = self.posts_in_process.get(site, None)
            if site_dict is None:
                log('error', 'posts_in_process: no site_dict found for {} in process: {}'.format(site_dict, ident))
                return False
            post_dict = site_dict.get(post_id, None)
            if post_dict is None:
                log('error', 'posts_in_process: no post_dict found for {} in process: {}'.format(post_dict, ident))
                return False
            if post_dict.get('owner', None) == ident:
                if post_dict.get('rescan_requested', None) is True:
                    add_to_global_bodyfetcher_queue_in_new_thread(site, question_id, False,
                                                                  source="BodyFetcher re-request")
                site_dict.pop(post_id, None)
                return True
            # There's really nothing for us to do here. We could raise an error, but it's
            # unclear that would help this thread.
            return False

    def make_api_call_for_site(self, site, new_posts, thread_stats):
        new_post_ids = [int(k) for k in new_posts.keys()]
        Tasks.do(GlobalVars.edit_watcher.subscribe, hostname=site, question_id=new_post_ids)

        if GlobalVars.flovis is not None:
            for post_id in new_post_ids:
                GlobalVars.flovis.stage('bodyfetcher/api_request', site, post_id,
                                        {'site': site, 'posts': list(new_posts.keys())})

        # Add queue timing data
        pop_time = datetime.utcnow()
        post_add_times = [(pop_time - v).total_seconds() for k, v in new_posts.items()]
        Tasks.do(add_queue_timing_data, site, post_add_times)

        store_max_ids = False
        with self.max_ids_lock:
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

            new_post_ids_max = max(new_post_ids)
            if new_post_ids_max > self.previous_max_ids.get(site, 0):
                self.previous_max_ids[site] = new_post_ids_max
                store_max_ids = True

        if store_max_ids:
            schedule_store_bodyfetcher_max_ids()

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
            with self.last_activity_date_lock:
                if self.last_activity_date != 0:
                    pagesize = "100"
                else:
                    pagesize = "50"

                pagesize_modifier = {
                    'pagesize': pagesize,
                    'min': str(max(self.last_activity_date - self.ACTIVITY_DATE_EXTRA_EARLIER_MS_TO_FETCH, 0))
                }
        else:
            question_modifier = "/{0}".format(";".join([str(post) for post in posts]))

        url = get_se_api_url_for_route("questions{}".format(question_modifier))
        params = get_se_api_default_params_questions_answers_posts_add_site(site)
        params.update(pagesize_modifier)

        # wait to make sure API has/updates post data
        time.sleep(3)

        with GlobalVars.api_request_lock:
            thread_stats['api_calls'] += 1
            # Respect backoff, if we were given one
            if GlobalVars.api_backoff_time > time.time():
                time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
            try:
                time_request_made = datetime.utcnow().strftime('%H:%M:%S')
                response = requests.get(url, params=params, timeout=20).json()
                response_timestamp = time.time()
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
                    if (quota_remaining - GlobalVars.apiquota >= self.QUOTA_ROLLOVER_DETECTION_MINIMUM_DIFFERENCE
                            and GlobalVars.apiquota >= 0
                            and quota_remaining > self.QUOTA_ROLLOVER_DETECTION_THRESHOLD):
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
                message_hq += " Previous URL: `{}?site={}`".format(url, site)

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
                with self.last_activity_date_lock:
                    self.last_activity_date = items[0]["last_activity_date"]

        self.scan_api_results(site, response, response_timestamp)

    def scan_api_results(self, site, response, response_timestamp):
        current_thread = threading.current_thread()
        current_thread_ident = current_thread.ident
        base_thread_name = current_thread.name
        full_start_time = time.time()
        section_start_time = full_start_time
        posts_processed_text = ''
        post_processing_text = ''
        scan_stats_text = ''
        scan_stats = {}
        post_stats = {}
        post_type = None
        processing_post_id = None
        started_post_stat_ident = None
        post_processing_text_prefixes = {
            'answer': '\n⠀⠀\t⠀⠀\tA{}:',
            'question': '\n⠀⠀\tQ{}:',
        }

        def build_scan_stats():
            nonlocal current_thread
            nonlocal scan_stats_text
            now = time.time()
            scan_stats_text = ('elapsed time: {}; scanned: {}, Q({}), A({});'
                               ' unchanged: Q({}), A({}); no post lock: {}; post errors: {}')
            scan_stats_text = scan_stats_text.format(
                round(now - full_start_time, 2),
                scan_stats.get('posts_scanned', 0),
                scan_stats.get('questions_scanned', 0),
                scan_stats.get('answers_scanned', 0),
                scan_stats.get('unchanged_questions', 0),
                scan_stats.get('unchanged_answers', 0),
                scan_stats.get('no_post_lock', 0),
                scan_stats.get('post_errors', 0))

        def set_thread_name():
            current_thread.name = (base_thread_name + '\n' + scan_stats_text + posts_processed_text
                                   + post_processing_text)

        def start_post(type_of_post, post_id):
            nonlocal post_stats
            nonlocal post_type
            nonlocal processing_post_id
            post_stats = {}
            end_post()
            post_type = type_of_post
            processing_post_id = post_id
            reset_section_timer()
            build_post_thread_name_text()
            set_thread_name()

        def end_post():
            nonlocal post_processing_text
            nonlocal posts_processed_text
            nonlocal post_stats
            nonlocal scan_stats
            nonlocal started_post_stat_ident
            posts_processed_text += post_processing_text
            post_processing_text = ''
            for stat_name, post_stat_dict in post_stats.items():
                if not post_stat_dict['dont_include_in_scan_stats']:
                    post_value = post_stat_dict.get('value', None)
                    if type(post_value) in [int, float]:
                        scan_stats[stat_name] = scan_stats.get(stat_name, 0) + post_stat_dict['value']
                    else:
                        log('warning', "BodyFetcher post stats: stat {} is {} with value: {}".format(stat_name,
                                                                                                     type(post_value),
                                                                                                     post_value))
            started_post_stat_ident = None
            post_stats = {}
            build_scan_stats()
            set_thread_name()

        def increment_scan_stat(stat_name, increment=1):
            nonlocal scan_stats
            old_value = scan_stats.get(stat_name, 0)
            scan_stats[stat_name] = old_value + increment

        def reset_section_timer():
            nonlocal section_start_time
            section_start_time = time.time()

        def start_post_stat_time(ident, short_text, no_low_output=True, dont_include_in_scan_stats=False):
            nonlocal post_stats
            nonlocal started_post_stat_ident
            post_stats[ident] = {
                'start_time': time.time(),
                'short_text': short_text,
                'no_low_output': no_low_output,
                'dont_include_in_scan_stats': dont_include_in_scan_stats,
            }
            started_post_stat_ident = ident
            build_post_thread_name_text()
            set_thread_name()

        def end_post_stat_time_and_start_new(new_ident=None, short_text=None, no_low_output=True,
                                             dont_include_in_scan_stats=False, ident=None):
            nonlocal post_stats
            nonlocal started_post_stat_ident
            now = time.time()
            if ident is None:
                ident = started_post_stat_ident
            elapsed = now - post_stats[ident]['start_time']
            post_stats[ident]['value'] = elapsed
            started_post_stat_ident = None
            if new_ident is not None:
                start_post_stat_time(new_ident, short_text, no_low_output, dont_include_in_scan_stats)
            else:
                started_post_stat_ident = None
            build_post_thread_name_text()
            set_thread_name()
            return elapsed

        def add_post_stat_time(ident, short_text, value=None, no_low_output=True, dont_include_in_scan_stats=False):
            nonlocal section_start_time
            nonlocal post_stats
            now = time.time()
            elapsed = now - section_start_time
            section_start_time = now
            if value is not None:
                elapsed = value
            post_stats[ident] = {
                'value': elapsed,
                'short_text': short_text,
                'no_low_output': no_low_output,
                'dont_include_in_scan_stats': dont_include_in_scan_stats,
            }
            build_post_thread_name_text()
            set_thread_name()
            return elapsed

        def build_post_thread_name_text():
            nonlocal post_processing_text
            build_post_thread_name_post_id()
            shorts_values = [[entry['short_text'], entry.get('value', '')] for entry in post_stats.values()
                             if not entry['no_low_output'] or entry.get('value', None) is None
                             or entry.get('value', 0) > self.POST_SCAN_PERFORMANCE_LOW_VALUE_DISPLAY_THRESHOLD]

            shorts_values = [[short_text, round(value, 2) if type(value) is float else value]
                             for short_text, value in shorts_values]
            texts = ['{}({})'.format(short_text, value) for short_text, value in shorts_values]
            post_processing_text += ';'.join(texts)

        def build_post_thread_name_post_id():
            nonlocal post_processing_text
            post_processing_text = post_processing_text_prefixes.get(post_type, '{}:').format(processing_post_id)

        def no_post_lock():
            nonlocal post_processing_text
            if started_post_stat_ident is not None:
                end_post_stat_time_and_start_new()
            increment_scan_stat('no_post_lock')
            build_post_thread_name_text()
            post_processing_text += '; no post lock'
            end_post()

        def post_is_unchanged():
            nonlocal post_processing_text
            if started_post_stat_ident is not None:
                end_post_stat_time_and_start_new()
            increment_scan_stat('unchanged_{}s'.format(post_type))
            # We don't show a record of the unchanged ones in the thread name.
            post_processing_text = ''
            end_post()

        def post_is_grace_period_edit():
            increment_scan_stat('grace_period_edits')

        def post_was_scanned():
            nonlocal scan_stats
            increment_scan_stat('posts_scanned')
            increment_scan_stat('{}s_scanned'.format(post_type))
            if started_post_stat_ident is not None:
                end_post_stat_time_and_start_new()
            post_scan_time_dict = post_stats.get('scan_{}'.format(post_type), None)
            if post_scan_time_dict is not None:
                post_scan_time = post_scan_time_dict.get('value', None)
                if type(post_scan_time) is float:
                    max_scan_time = scan_stats.get('max_scan_time', 0)
                    if post_scan_time > max_scan_time:
                        scan_stats['max_scan_time'] = post_scan_time
                        scan_stats['max_scan_time_post'] = '{}/{}'.format(site, processing_post_id)
            build_post_thread_name_text()
            end_post()

        def post_had_error():
            nonlocal post_processing_text
            increment_scan_stat('post_errors')
            build_post_thread_name_text()
            post_processing_text += '; ERROR'
            end_post()

        for post in response["items"]:
            if GlobalVars.flovis is not None:
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
            post['response_timestamp'] = response_timestamp
            try:
                post['edited'] = (post['creation_date'] != post['last_edit_date'])
            except KeyError:
                post['edited'] = False  # last_edit_date not present = not edited

            question_id = post.get('question_id', None)
            start_post('question', question_id)
            if question_id is not None:
                Tasks.do(GlobalVars.edit_watcher.subscribe, hostname=site, question_id=question_id)
            try:
                start_post_stat_time('post_processing_lock', '<Qplk')
                have_question_processing_lock = self.claim_post_in_process_or_request_rescan(current_thread_ident,
                                                                                             site, question_id)
                if have_question_processing_lock:
                    end_post_stat_time_and_start_new('check_unchanged', '<Qchkun')
                    compare_info = rsp.atomic_compare_update_and_get_spam_data(post)
                    question_doesnt_need_scan = compare_info['is_older_or_unchanged']
                    if question_doesnt_need_scan:
                        post_is_unchanged()
                    if compare_info.get('is_grace_edit', False):
                        post_is_grace_period_edit()
                else:
                    question_doesnt_need_scan = True
                    no_post_lock()

                if question_doesnt_need_scan and "answers" not in post:
                    continue
                do_flovis = GlobalVars.flovis is not None and question_id is not None
                try:
                    post_ = Post(api_response=post)
                except PostParseError as err:
                    log('error', 'Error {0} when parsing post: {1!r}'.format(err, post_))
                    if do_flovis:
                        GlobalVars.flovis.stage('bodyfetcher/api_response/error', site, question_id, pnb)
                    continue

                if not question_doesnt_need_scan:
                    end_post_stat_time_and_start_new('scan_question', ' scan', no_low_output=False)
                    is_spam, reason, why = convert_new_scan_to_spam_result_if_new_reasons(
                        check_if_spam(post_),
                        compare_info,
                        match_ignore=self.IGNORED_IGNORED_SPAM_CHECKS_IF_WORSE_SPAM
                    )
                    scan_time = end_post_stat_time_and_start_new()
                    rsp.add_post(post, is_spam=is_spam, reasons=reason, why=why, scan_time=scan_time)

                    if is_spam:
                        try:
                            if do_flovis:
                                GlobalVars.flovis.stage('bodyfetcher/api_response/spam', site, question_id,
                                                        {'post': pnb, 'check_if_spam': [is_spam, reason, why]})
                            handle_spam(post=post_,
                                        reasons=reason,
                                        why=why)
                        except Exception as e:
                            log('error', "Exception in handle_spam:", e)
                    elif do_flovis:
                        GlobalVars.flovis.stage('bodyfetcher/api_response/not_spam', site, question_id,
                                                {'post': pnb, 'check_if_spam': [is_spam, reason, why]})
                    post_was_scanned()
            except Exception:
                post_had_error()
                raise
            finally:
                if have_question_processing_lock:
                    have_question_processing_lock = False
                    self.release_post_in_process_and_recan_if_requested(current_thread_ident, site, question_id,
                                                                        question_id)

            try:
                if "answers" not in post:
                    pass
                else:
                    for answer in post["answers"]:
                        if GlobalVars.flovis is not None:
                            anb = copy.deepcopy(answer)
                            if 'body' in anb:
                                anb['body'] = 'Present, but truncated'

                        answer['response_timestamp'] = response_timestamp
                        answer["IsAnswer"] = True  # Necesssary for Post object
                        answer["title"] = ""  # Necessary for proper Post object creation
                        answer["site"] = site  # Necessary for proper Post object creation
                        try:
                            answer['edited'] = (answer['creation_date'] != answer['last_edit_date'])
                        except KeyError:
                            answer['edited'] = False  # last_edit_date not present = not edited
                        answer_id = answer.get('answer_id', None)
                        start_post('answer', answer_id)
                        try:
                            start_post_stat_time('post_processing_lock', '<Aplk')
                            answer_processing_lock = self.claim_post_in_process_or_request_rescan(current_thread_ident,
                                                                                                  site, answer_id)
                            if answer_processing_lock:
                                end_post_stat_time_and_start_new('check_unchanged', '<Achkun')
                                compare_info = rsp.atomic_compare_update_and_get_spam_data(answer)
                                answer_doesnt_need_scan = compare_info['is_older_or_unchanged']
                                if compare_info.get('is_grace_edit', False):
                                    post_is_grace_period_edit()
                            else:
                                no_post_lock()
                                continue
                            if answer_doesnt_need_scan:
                                post_is_unchanged()
                                continue
                            answer_ = Post(api_response=answer, parent=post_)

                            end_post_stat_time_and_start_new('scan_answer', ' scan', no_low_output=False)
                            is_spam, reason, why = convert_new_scan_to_spam_result_if_new_reasons(
                                check_if_spam(answer_),
                                compare_info,
                                match_ignore=self.IGNORED_IGNORED_SPAM_CHECKS_IF_WORSE_SPAM
                            )
                            scan_time = end_post_stat_time_and_start_new()
                            rsp.add_post(answer, is_spam=is_spam, reasons=reason, why=why, scan_time=scan_time)

                            if is_spam:
                                do_flovis = GlobalVars.flovis is not None and answer_id is not None
                                try:
                                    if do_flovis:
                                        GlobalVars.flovis.stage('bodyfetcher/api_response/spam', site, answer_id,
                                                                {'post': anb, 'check_if_spam': [is_spam, reason, why]})
                                    handle_spam(answer_,
                                                reasons=reason,
                                                why=why)
                                except Exception as e:
                                    log('error', "Exception in handle_spam:", e)
                            elif do_flovis:
                                GlobalVars.flovis.stage('bodyfetcher/api_response/not_spam', site, answer_id,
                                                        {'post': anb, 'check_if_spam': [is_spam, reason, why]})
                            post_was_scanned()
                        except Exception:
                            raise
                        finally:
                            if answer_processing_lock:
                                answer_processing_lock = False
                                self.release_post_in_process_and_recan_if_requested(current_thread_ident, site,
                                                                                    answer_id, question_id)

            except Exception as e:
                post_had_error()
                log('error', "Exception handling answers:", e)

        end_time = time.time()
        scan_stats['scan_time'] = end_time - full_start_time
        GlobalVars.PostScanStat.add(scan_stats)
        log('debug', current_thread.name)
        return
