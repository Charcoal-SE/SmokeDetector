# coding=utf-8
import json
import requests
import importlib  # for .reload()
from globalvars import GlobalVars
import threading
# noinspection PyPackageRequirements
import websocket
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable
from datetime import datetime, timedelta
from glob import glob
from regex import sub
import sys
import traceback
import time
import os
import subprocess as sp
import datahandling
import parsing
import apigetpost
import spamhandling
import classes
import chatcommunicate
from helpers import log, exit_mode, only_blacklists_changed, \
    only_modules_changed, blacklist_integrity_check, reload_modules, log_exception
from gitmanager import GitManager
import findspam
from socketscience import SocketScience
import metasmoke_cache


MS_WEBSOCKET_LONG_INTERVAL = 60
MAX_MS_WEBSOCKET_RETRIES_TO_LONG_INTERVAL = 5
MAX_FAILURES = 10  # Preservative, 10 errors = MS down
NO_ACTIVITY_PINGS_TO_REBOOT = 4
NO_ACTIVITY_PINGS_TO_STANDBY = 5  # This is effectively disabled
NO_ACTIVITY_PINGS_TO_REPORT = 3


# noinspection PyClassHasNoInit,PyBroadException,PyUnresolvedReferences,PyProtectedMember
class Metasmoke:
    MS_URLS_TO_NOT_QUEUE = [
        "/status-update.json",
        "/flagging/smokey_disable",
    ]
    status_pings_since_scan_activity = 0
    scan_stat_snapshot = None
    ms_ajax_queue_lock = threading.Lock()
    # The ms_ajax_queue is filled from the pickle in datahandling
    ms_ajax_queue = []

    class AutoSwitch:
        """ Automatically switch metasmoke status """
        MAX_FAILURES = 10  # More than 10 failures == ms down
        MAX_SUCCESSES = 1  # More than 1 success == ms up
        ping_failure_counter = 0  # Negative values indicate consecutive successes
        autoswitch_is_on = True
        rw_lock = threading.Lock()

        @staticmethod
        def ping_failed():
            """ Indicate a metasmoke status ping connection failure """
            with Metasmoke.AutoSwitch.rw_lock:
                if Metasmoke.AutoSwitch.ping_failure_counter < 0:
                    # Consecutive counter. Switch sign.
                    Metasmoke.AutoSwitch.ping_failure_counter = 0
                Metasmoke.AutoSwitch.ping_failure_counter += 1
                current_counter = Metasmoke.AutoSwitch.ping_failure_counter
                current_auto = Metasmoke.AutoSwitch.autoswitch_is_on
            # MAX_FAILURES is constant so no lock.
            if current_counter > Metasmoke.AutoSwitch.MAX_FAILURES and\
               GlobalVars.MSStatus.is_up() and current_auto:
                log("warning", "Last {} connection(s) to metasmoke failed".format(current_counter) +
                               " Setting metasmoke status to down.")
                chatcommunicate.tell_rooms_with("debug", "**Warning**: {}: ".format(GlobalVars.location) +
                                                         "Last {} connection(s) to metasmoke".format(current_counter) +
                                                         " failed. Setting metasmoke status to **down**.")
                Metasmoke.set_ms_down(tell=False)

        @staticmethod
        def ping_succeeded():
            """ Indicate a metasmoke status ping connection success """
            with Metasmoke.AutoSwitch.rw_lock:
                if Metasmoke.AutoSwitch.ping_failure_counter > 0:
                    # Consecutive counter. Switch sign.
                    Metasmoke.AutoSwitch.ping_failure_counter = 0
                Metasmoke.AutoSwitch.ping_failure_counter -= 1
                # Negative values for success
                current_counter = -Metasmoke.AutoSwitch.ping_failure_counter
                current_auto = Metasmoke.AutoSwitch.autoswitch_is_on
            # MAX_SUCCESSES is constant so no lock.
            if current_counter > Metasmoke.AutoSwitch.MAX_SUCCESSES and\
               GlobalVars.MSStatus.is_down() and current_auto:
                # Why use warning? Because some action may be needed if people don't think metasmoke is up.
                log("warning", "Last {} connection(s) to metasmoke succeeded".format(current_counter) +
                               " Setting metasmoke status to up.")
                chatcommunicate.tell_rooms_with("debug", "**Notice**: {}: ".format(GlobalVars.location) +
                                                         "Last {} connection(s) to metasmoke".format(current_counter) +
                                                         " succeeded. Setting metasmoke status to **up**.")
                Metasmoke.set_ms_up(tell=False)

        @staticmethod
        def enable_autoswitch(to_enable):
            """ Enable or disable auto status switch """
            switch_auto_msg = ""
            with Metasmoke.AutoSwitch.rw_lock:
                if Metasmoke.AutoSwitch.autoswitch_is_on is not to_enable:
                    # Log and post chat message only if there really is a change.
                    switch_auto_msg = "Metasmoke status autoswitch is now {}abled.".format("en" if to_enable else "dis")
                    Metasmoke.AutoSwitch.autoswitch_is_on = to_enable

            if switch_auto_msg:
                log("info", switch_auto_msg)
                chatcommunicate.tell_rooms_with("debug", switch_auto_msg)

        @staticmethod
        def get_ping_failure():
            """ Get ping failure count. Negative number is ping success count. """
            with Metasmoke.AutoSwitch.rw_lock:
                return Metasmoke.AutoSwitch.ping_failure_counter

        @staticmethod
        def reset_switch():
            """ Reset class Metasmoke.AutoSwitch to default values """
            with Metasmoke.AutoSwitch.rw_lock:
                Metasmoke.AutoSwitch.ping_failure_counter = 0
                Metasmoke.AutoSwitch.autoswitch_is_on = True

    @staticmethod
    def set_ms_up(tell=True):
        """ Switch metasmoke status to up """
        # We must first set metasmoke to up, then say that metasmoke is up, not the other way around.
        ms_msg = ""
        if GlobalVars.MSStatus.is_down():
            ms_msg = "Metasmoke status: set to up."
            GlobalVars.MSStatus.set_up()

        if ms_msg:
            log("info", ms_msg)
            if tell:
                chatcommunicate.tell_rooms_with("debug", "{}: {}".format(GlobalVars.location, ms_msg))

    @staticmethod
    def set_ms_down(tell=True):
        """ Switch metasmoke status to down """
        ms_msg = ""
        if GlobalVars.MSStatus.is_up():
            ms_msg = "Metasmoke status: set to down."
            GlobalVars.MSStatus.set_down()

        if ms_msg:
            log("info", ms_msg)
            if tell:
                chatcommunicate.tell_rooms_with("debug", "{}: {}".format(GlobalVars.location, ms_msg))

    @staticmethod
    def connect_websocket():
        GlobalVars.metasmoke_ws = websocket.create_connection(GlobalVars.metasmoke_ws_host,
                                                              origin=GlobalVars.metasmoke_host)
        payload = json.dumps({"command": "subscribe",
                              "identifier": "{\"channel\":\"SmokeDetectorChannel\","
                              "\"key\":\"" + GlobalVars.metasmoke_key + "\"}"})
        GlobalVars.metasmoke_ws.send(payload)
        GlobalVars.metasmoke_ws.settimeout(10)

    @staticmethod
    def init_websocket():
        has_succeeded = False
        failed_connection_attempts = 0
        while GlobalVars.metasmoke_key and GlobalVars.metasmoke_ws_host:
            try:
                Metasmoke.connect_websocket()
                has_succeeded = True
                while True:
                    a = GlobalVars.metasmoke_ws.recv()
                    try:
                        data = json.loads(a)
                        Metasmoke.handle_websocket_data(data)
                        GlobalVars.MSStatus.succeeded()
                        failed_connection_attempts = 0
                    except ConnectionError:
                        raise
                    except Exception as e:
                        log('error', '{}: {}'.format(type(e).__name__, e))
                        log_exception(*sys.exc_info())
                        GlobalVars.MSStatus.failed()
                        Metasmoke.connect_websocket()
            except Exception:
                GlobalVars.MSStatus.failed()
                log('error', "Couldn't bind to MS websocket")
                if not has_succeeded:
                    failed_connection_attempts += 1
                    if failed_connection_attempts == MAX_MS_WEBSOCKET_RETRIES_TO_LONG_INTERVAL:
                        chatcommunicate.tell_rooms_with("debug", "Cannot initiate MS websocket."
                                                                 " Continuing to retry at longer intervals.")
                        log('warning', "Cannot initiate MS websocket."
                                       " Continuing to retry at longer intervals.")
                    if failed_connection_attempts >= MAX_MS_WEBSOCKET_RETRIES_TO_LONG_INTERVAL:
                        time.sleep(MS_WEBSOCKET_LONG_INTERVAL)
                    else:
                        # Wait and hopefully network issues will be solved
                        time.sleep(10)
                else:
                    time.sleep(10)

    @staticmethod
    def handle_websocket_data(data):
        if "message" not in data:
            if "type" in data and data['type'] == "reject_subscription":
                log('error', "MS WebSocket subscription was rejected. Check your MS key.")
                raise ConnectionError("MS WebSocket connection rejected")
            return
        message = data['message']
        if not isinstance(message, Iterable):
            return

        if "message" in message:
            # Temporarily allow this to be handled by the MS relay instance
            return
            from_ms = message['message']
            if (from_ms.startswith("[ [charcoal-se.github.io](https://github.com/Charcoal-SE/charcoal-se.github.io) ]"
                                   " continuous-integration/travis-ci/push")):
                from_ms = from_ms.replace(": ",
                                          ", or the [SD wiki](//git.io/vyDZv)"
                                          " ([history](//github.com/Charcoal-SE/SmokeDetector/wiki/_history)): ", 1)
            # Use protocol-relative links
            from_ms = sub(r"\]\((?<!\\\]\()https?://", "](//", from_ms)
            chatcommunicate.tell_rooms_with("metasmoke", from_ms)
        elif "autoflag_fp" in message:
            event = message["autoflag_fp"]

            chatcommunicate.tell_rooms(event["message"], ("debug", "site-" + event["site"]),
                                       ("no-site-" + event["site"],), notify_site="/autoflag_fp")
        elif "exit" in message:
            exit_mode(code=message["exit"])
        elif "blacklist" in message:
            ids = (message['blacklist']['uid'], message['blacklist']['site'])

            datahandling.add_blacklisted_user(ids, "metasmoke", message['blacklist']['post'])
            with datahandling.last_feedbacked_lock:
                datahandling.last_feedbacked = (ids, time.time() + 60)
        elif "unblacklist" in message:
            ids = (message['unblacklist']['uid'], message['unblacklist']['site'])
            datahandling.remove_blacklisted_user(ids)
        elif "naa" in message:
            post_site_id = parsing.fetch_post_id_and_site_from_url(message["naa"]["post_link"])
            datahandling.add_ignored_post(post_site_id[0:2])
        elif "fp" in message:
            post_site_id = parsing.fetch_post_id_and_site_from_url(message["fp"]["post_link"])
            datahandling.add_false_positive(post_site_id[0:2])
        elif "report" in message:
            import chatcommands  # Do it here
            chatcommands.report_posts([message["report"]["post_link"]], message["report"]["user"],
                                      True, "the metasmoke API")
        elif "deploy_updated" in message:
            return  # Disabled
            sha = message["deploy_updated"]["head_commit"]["id"]
            if sha != os.popen('git log -1 --pretty="%H"').read():
                if "autopull" in message["deploy_updated"]["head_commit"]["message"]:
                    if only_blacklists_changed(GitManager.get_remote_diff()):
                        commit_md = "[`{0}`](https://github.com/{1}/commit/{0})" \
                                    .format(sha[:7], GlobalVars.bot_repo_slug)
                        integrity = blacklist_integrity_check()
                        if len(integrity) == 0:  # No issues
                            GitManager.pull_remote()
                            findspam.reload_blacklists()
                            chatcommunicate.tell_rooms_with("debug", "No code modified in {0}, only blacklists"
                                                            " reloaded.".format(commit_md))
                        else:
                            integrity.append("please fix before pulling.")
                            chatcommunicate.tell_rooms_with("debug", ", ".join(integrity))
        elif "commit_status" in message:
            c = message["commit_status"]
            sha = c["commit_sha"][:7]
            recent_commits = sp.check_output(["git", "log", "-50", "--pretty=%H"]).decode('utf-8').strip().split('\n')
            if c["commit_sha"] in recent_commits:
                return  # Same rev, or earlier rev (e.g. when watching things faster than CI completes), nothing to do

            if c["status"] == "success":
                if "autopull" in c["commit_message"] or c["commit_message"].startswith("!") or \
                        c["commit_message"].startswith("Auto "):
                    s = "[CI]({ci_link}) on [`{commit_sha}`](https://github.com/{repo}/" \
                        "commit/{commit_sha}) succeeded. Message contains 'autopull', pulling...".format(
                            ci_link=c["ci_url"], repo=GlobalVars.bot_repo_slug, commit_sha=sha)
                    remote_diff = GitManager.get_remote_diff()
                    if only_blacklists_changed(remote_diff):
                        GitManager.pull_remote()
                        with GlobalVars.globalvars_reload_lock:
                            on_branch = GlobalVars.on_branch
                        if not on_branch:
                            # Restart if HEAD detached
                            log('warning', "Pulling remote with HEAD detached, checkout deploy", f=True)
                            exit_mode("checkout_deploy")
                        GlobalVars.reload()
                        findspam.FindSpam.reload_blacklists()
                        with GlobalVars.globalvars_reload_lock:
                            globalvars_s_norestart_blacklists = GlobalVars.s_norestart_blacklists
                        chatcommunicate.tell_rooms_with('debug', globalvars_s_norestart_blacklists)
                    elif False and only_modules_changed(remote_diff):
                        # As of 2022-05-19, this causes at least intermittent failures and has been disabled.
                        GitManager.pull_remote()
                        with GlobalVars.globalvars_reload_lock:
                            on_branch = GlobalVars.on_branch
                        if not on_branch:
                            # Restart if HEAD detached
                            log('warning', "Pulling remote with HEAD detached, checkout deploy", f=True)
                            exit_mode("checkout_deploy")
                        GlobalVars.reload()
                        reload_modules()
                        with GlobalVars.globalvars_reload_lock:
                            globalvars_s_norestart_findspam = GlobalVars.s_norestart_findspam
                        chatcommunicate.tell_rooms_with('debug', globalvars_s_norestart_findspam)
                    else:
                        chatcommunicate.tell_rooms_with('debug', s, notify_site="/ci")
                        exit_mode("pull_update")
                else:
                    s = "[CI]({ci_link}) on [`{commit_sha}`](https://github.com/{repo}/commit/{commit_sha}) " \
                        "succeeded.".format(ci_link=c["ci_url"], repo=GlobalVars.bot_repo_slug, commit_sha=sha)

                    chatcommunicate.tell_rooms_with("debug", s, notify_site="/ci")
            elif c["status"] == "failure":
                s = "[CI]({ci_link}) on [`{commit_sha}`](https://github.com/{repo}/commit/{commit_sha}) " \
                    "failed.".format(ci_link=c["ci_url"], repo=GlobalVars.bot_repo_slug, commit_sha=sha)

                chatcommunicate.tell_rooms_with("debug", s, notify_site="/ci")
        elif "everything_is_broken" in message:
            if message["everything_is_broken"] is True:
                exit_mode("shutdown")
        elif "domain_whitelist" in message:
            if message["domain_whitelist"] == "refresh":
                metasmoke_cache.MetasmokeCache.delete('whitelisted-domains')

    @staticmethod
    def add_call_to_metasmoke_queue(method_name, ms_ajax_timestamp, data):
        if ms_ajax_timestamp == 0:
            ms_ajax_timestamp = time.time()
        new_entry = {"method_name": method_name, 'ms_ajax_timestamp': ms_ajax_timestamp, "data": data}
        with Metasmoke.ms_ajax_queue_lock:
            Metasmoke.ms_ajax_queue.append(new_entry)
            queue_length = len(Metasmoke.ms_ajax_queue)
        log('debug', 'Added a call to the delayed MS AJAX queue. Current length: {}'.format(queue_length))
        datahandling.store_ms_ajax_queue()

    @staticmethod
    def send_stats_on_post(title, link, reasons, body, markdown, username, user_link, why, owner_rep,
                           post_score, up_vote_count, down_vote_count, ms_ajax_timestamp=0):
        if GlobalVars.metasmoke_host is None:
            log('info', 'Would have reported post to metasmoke, but metasmoke_host is undefined. Ignoring.')
            return
        elif GlobalVars.MSStatus.is_down():
            Metasmoke.add_call_to_metasmoke_queue("send_stats_on_post", ms_ajax_timestamp, {
                "kwargs": {
                    "title": title,
                    "link": link,
                    "reasons": reasons,
                    "body": body,
                    "markdown": markdown,
                    "username": username,
                    "user_link": user_link,
                    "why": why,
                    "owner_rep": owner_rep,
                    "post_score": post_score,
                    "up_vote_count": up_vote_count,
                    "down_vote_count": down_vote_count,
                }
            })
            log('warning', "Metasmoke down, not sending stats now, but queued it for later.")
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            if len(why) > 4096:
                why = why[:2048] + ' ... ' + why[-2043:]  # Basic maths

            post = {'title': title, 'link': link, 'reasons': reasons, 'body': body, 'markdown': markdown,
                    'username': username, 'user_link': user_link,
                    'why': why, 'user_reputation': owner_rep, 'score': post_score,
                    'upvote_count': up_vote_count, 'downvote_count': down_vote_count}

            # Remove None values (if they somehow manage to get through)
            post = {k: v for k, v in post.items() if v}

            payload = {'post': post, 'key': metasmoke_key}
            headers = {'Content-type': 'application/json'}
            Metasmoke.post("/posts.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            log('error', e)

    @staticmethod
    def send_feedback_for_post(post_link, feedback_type, user_name, user_id, chat_host, ms_ajax_timestamp=0):
        if GlobalVars.metasmoke_host is None:
            log('info', 'Received chat feedback but metasmoke_host is undefined. Ignoring.')
            return
        elif GlobalVars.MSStatus.is_down():
            Metasmoke.add_call_to_metasmoke_queue("send_feedback_for_post", ms_ajax_timestamp, {
                "kwargs": {
                    "post_link": post_link,
                    "feedback_type": feedback_type,
                    "user_name": user_name,
                    "user_id": user_id,
                    "chat_host": chat_host,
                }
            })
            log('warning', "Metasmoke is down, not sending feedback now, but queued it for later.")
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            payload = {
                'feedback': {
                    'user_name': user_name,
                    'chat_user_id': user_id,
                    'chat_host': chat_host,
                    'feedback_type': feedback_type,
                    'post_link': post_link
                },
                'key': metasmoke_key
            }

            headers = {'Content-type': 'application/json'}
            Metasmoke.post("/feedbacks.json", data=json.dumps(payload), headers=headers)

        except Exception as e:
            log('error', e)

    @staticmethod
    def send_deletion_stats_for_post(post_link, is_deleted, ms_ajax_timestamp=0):
        if GlobalVars.metasmoke_host is None:
            log('info', 'Attempted to send deletion data but metasmoke_host is undefined. Ignoring.')
            return
        elif GlobalVars.MSStatus.is_down():
            Metasmoke.add_call_to_metasmoke_queue("send_deletion_stats_for_post", ms_ajax_timestamp, {
                "kwargs": {
                    "post_link": post_link,
                    "is_deleted": is_deleted,
                }
            })
            log('warning', "Metasmoke is down, not sending deletion stats now, but queued it for later.")
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            payload = {
                'deletion_log': {
                    'is_deleted': is_deleted,
                    'post_link': post_link
                },
                'key': metasmoke_key
            }

            headers = {'Content-type': 'application/json'}
            Metasmoke.post("/deletion_logs.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            log('error', e)

    @staticmethod
    def send_status_ping():
        if GlobalVars.metasmoke_host is None:
            log('info', 'Attempted to send status ping but metasmoke_host is undefined. Not sent.')
            return
        elif GlobalVars.MSStatus.is_down():
            payload = {
                "location": GlobalVars.location,
                "timestamp": time.time()
            }
            SocketScience.send(payload)

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            payload = {
                'location': GlobalVars.location,
                'key': metasmoke_key,
                'standby': GlobalVars.standby_mode or GlobalVars.no_se_activity_scan
            }

            headers = {'content-type': 'application/json'}
            response = Metasmoke.post("/status-update.json",
                                      data=json.dumps(payload), headers=headers, ignore_down=True)

            try:
                response = response.json()

                if response.get('pull_update', False):
                    log('info', "Received pull command from MS ping response")
                    exit_mode("pull_update")

                if ('failover' in response and GlobalVars.standby_mode and not GlobalVars.no_se_activity_scan):
                    # If we're not scanning, then we don't want to become officially active due to failover.
                    if response['failover']:
                        GlobalVars.standby_mode = False

                        chatcommunicate.tell_rooms_with("debug", GlobalVars.location + " received failover signal.",
                                                        notify_site="/failover")

                if response.get('standby', False):
                    chatcommunicate.tell_rooms_with("debug",
                                                    GlobalVars.location + " entering metasmoke-forced standby.")
                    time.sleep(2)
                    exit_mode("standby")

                if response.get('shutdown', False):
                    exit_mode("shutdown")

            except Exception:  # TODO: What could happen here?
                pass

        except Exception as e:
            log('error', e)

    @staticmethod
    def update_code_privileged_users_list():
        if GlobalVars.MSStatus.is_down():
            log('warning', "Metasmoke is down, can't update blacklist manager privilege list")
            return

        payload = {'key': GlobalVars.metasmoke_key}
        headers = {'Content-type': 'application/json'}
        try:
            response = Metasmoke.get("/api/users/code_privileged",
                                     data=json.dumps(payload), headers=headers).json()['items']
        except Exception as e:
            log('error', e)
            return

        GlobalVars.code_privileged_users = set()

        for id in response["stackexchange_chat_ids"]:
            GlobalVars.code_privileged_users.add(("stackexchange.com", id))

        for id in response["meta_stackexchange_chat_ids"]:
            GlobalVars.code_privileged_users.add(("meta.stackexchange.com", id))

        for id in response["stackoverflow_chat_ids"]:
            GlobalVars.code_privileged_users.add(("stackoverflow.com", id))

    @staticmethod
    def determine_if_autoflagged(post_url):
        """
        Given the URL for a post, determine whether or not it has been autoflagged.
        """
        payload = {
            'key': GlobalVars.metasmoke_key,
            'filter': 'GFGJGHFMHGOLMMJMJJJGHIGOMKFKKILF',  # id and autoflagged
            'urls': post_url
        }
        try:
            response = Metasmoke.get("/api/v2.0/posts/urls", params=payload).json()
        except Exception as e:
            log('error', e)
            return False, []

        # The first report of a URL is the only one that will be autoflagged. MS responses to the
        # /posts/urls endpoint have the oldest report last.
        if len(response["items"]) > 0 and response["items"][-1]["autoflagged"]:
            # get flagger names
            id = str(response["items"][-1]["id"])
            payload = {'key': GlobalVars.metasmoke_key}

            flags = Metasmoke.get("/api/v2.0/posts/" + id + "/flags", params=payload).json()

            if len(flags["items"]) > 0:
                return True, [user["username"] for user in flags["items"][0]["autoflagged"]["users"]]

        return False, []

    @staticmethod
    def stop_autoflagging():
        payload = {'key': GlobalVars.metasmoke_key}
        headers = {'Content-type': 'application/json'}

        Metasmoke.post("/flagging/smokey_disable",
                       data=json.dumps(payload), headers=headers)

    @staticmethod
    def send_statistics():
        if GlobalVars.MSStatus.is_down():
            log('warning', "Metasmoke is down, not sending statistics")
            return
        # Get current apiquota from globalvars
        with GlobalVars.apiquota_rw_lock:
            current_apiquota = GlobalVars.apiquota

        posts_scanned, scan_time, posts_per_second = GlobalVars.PostScanStat.get_stats_for_ms(reset=True)
        payload = {'key': GlobalVars.metasmoke_key,
                   'statistic': {'posts_scanned': posts_scanned,
                                 'api_quota': current_apiquota}}
        if posts_per_second:
            # Send scan rate as well, if applicable.
            payload['statistic']['post_scan_rate'] = posts_per_second

        headers = {'Content-type': 'application/json'}

        if GlobalVars.metasmoke_host is not None:
            log('info', 'Sent statistics to metasmoke: ', payload['statistic'])
            Metasmoke.post("/statistics.json",
                           data=json.dumps(payload), headers=headers)
        else:
            log('info', 'Would have sent statistics to metasmoke, but metasmoke_host is undefined.'
                        ' Ignoring. Stats would have been: ', payload['statistic'])

    @staticmethod
    def post_auto_comment(msg, user, url=None, ids=None):
        if not GlobalVars.metasmoke_key:
            return

        response = None

        if url is not None:
            params = {"key": GlobalVars.metasmoke_key, "urls": url, "filter": "GFGJGHFJNFGNHKNIKHGGOMILHKLJIFFN"}
            response = Metasmoke.get("/api/v2.0/posts/urls", params=params).json()
        elif ids is not None:
            post_id, site = ids
            site = parsing.api_parameter_from_link(site)
            params = {"key": GlobalVars.metasmoke_key, "filter": "GFGJGHFJNFGNHKNIKHGGOMILHKLJIFFN"}

            try:
                response = Metasmoke.get("/api/v2.0/posts/uid/{}/{}".format(site, post_id), params=params).json()
            except AttributeError:
                response = None

        if response and "items" in response and len(response["items"]) > 0:
            ms_id = response["items"][0]["id"]
            params = {"key": GlobalVars.metasmoke_key,
                      "text": msg[:1].upper() + msg[1:],  # Capitalise the first letter of the comment
                      "chat_user_id": user.id,
                      "chat_host": user._client.host}

            Metasmoke.post("/api/v2.0/comments/post/{}".format(ms_id), params=params)

    @staticmethod
    def get_post_bodies_from_ms(post_url):
        if not GlobalVars.metasmoke_key or not GlobalVars.metasmoke_host or GlobalVars.MSStatus.is_down():
            return None

        payload = {
            'key': GlobalVars.metasmoke_key,
            'filter': 'GHOOIJGNLKHIIOIKGILKIJGHFMNKKGFJ',  # posts.id, posts.body, posts.created_at
            'urls': parsing.to_protocol_relative(post_url)
        }
        try:
            response = Metasmoke.get('/api/v2.0/posts/urls', params=payload).json()
        except AttributeError:
            return None
        except Exception as e:
            log('error', '{}: {}'.format(type(e).__name__, e))
            log_exception(*sys.exc_info())
            exception_only = ''.join(traceback.format_exception_only(type(e), e)).strip()
            chatcommunicate.tell_rooms_with("debug", "{}: In getting MS post information, recovered from `{}`"
                                                     .format(GlobalVars.location, exception_only))
            return None

        return response['items']

    @staticmethod
    def get_reason_weights():
        if not GlobalVars.metasmoke_key:
            return None

        payload = {
            'key': GlobalVars.metasmoke_key,
            'per_page': 100,
            'page': 1,
        }
        items = []
        try:
            while True:
                response = Metasmoke.get('/api/v2.0/reasons', params=payload).json()
                items.extend(response['items'])
                if not response['has_more']:
                    break
                payload['page'] += 1
        except AttributeError:
            return None
        return items

    # Some sniffy stuff
    @staticmethod
    def request_sender(method):
        def func(url, *args, ignore_down=False, ms_ajax_timestamp=0, **kwargs):
            if not GlobalVars.metasmoke_host or (GlobalVars.MSStatus.is_down() and not ignore_down):
                return None

            if 'timeout' not in kwargs:
                kwargs['timeout'] = 10.000  # Don't throttle by MS

            response = None  # Should return None upon failure, if any
            try:
                response = method(GlobalVars.metasmoke_host + url, *args, **kwargs)
            except Exception:
                GlobalVars.MSStatus.failed()
                if ignore_down:
                    # Means that this is a status ping
                    Metasmoke.AutoSwitch.ping_failed()
                if method is requests.post and url not in Metasmoke.MS_URLS_TO_NOT_QUEUE:
                    # This is a POST. It's failed, and this is not a URL to which we care to send later.
                    kwargs['ignore_down'] = ignore_down
                    Metasmoke.add_call_to_metasmoke_queue("post", ms_ajax_timestamp,
                                                          {"args": tuple([url]) + args, "kwargs": kwargs})
                    log('warning', "A POST to metasmoke URL: {} failed. It has been queued for later.".format(url))
                # No need to log here because it's re-raised
                raise  # Maintain minimal difference to the original get/post methods
            else:
                GlobalVars.MSStatus.succeeded()
                if ignore_down:
                    # Means that this is a status ping
                    Metasmoke.AutoSwitch.ping_succeeded()

            return response
        return func

    get = request_sender.__func__(requests.get)
    post = request_sender.__func__(requests.post)

    @staticmethod
    def send_status_ping_and_verify_scanning_if_active():
        def reboot_or_standby(action):
            error_message = "There's been no scan activity for {} status pings. Going to {}." \
                            .format(Metasmoke.status_pings_since_scan_activity, action)
            log('error', error_message)
            chatcommunicate.tell_rooms_with("debug", error_message)
            if action == "standby":
                GlobalVars.standby_mode = True
            # Let MS know immediately, to lessen potential wait time (e.g. if we fail to reboot).
            Metasmoke.send_status_ping()
            time.sleep(8)
            exit_mode(action)

        in_standby_mode = GlobalVars.standby_mode or GlobalVars.no_se_activity_scan
        if not in_standby_mode:
            # This is the active instance, so should be scanning. If it's not scanning, then report or go to standby.
            current_ms_stats = GlobalVars.PostScanStat.get_stats_for_ms()
            if current_ms_stats == Metasmoke.scan_stat_snapshot:
                # There's been no actvity since the last ping.
                Metasmoke.status_pings_since_scan_activity += 1
                with GlobalVars.ignore_no_se_websocket_activity_lock:
                    ignore_no_se_websocket_activity = GlobalVars.ignore_no_se_websocket_activity
                if ignore_no_se_websocket_activity:
                    pass
                elif Metasmoke.status_pings_since_scan_activity >= NO_ACTIVITY_PINGS_TO_REBOOT:
                    # Assume something is very wrong. Report to debug rooms and go into standby mode.
                    reboot_or_standby("reboot")
                elif Metasmoke.status_pings_since_scan_activity >= NO_ACTIVITY_PINGS_TO_STANDBY:
                    # Assume something is very wrong. Report to debug rooms and go into standby mode.
                    reboot_or_standby("standby")
                elif Metasmoke.status_pings_since_scan_activity >= NO_ACTIVITY_PINGS_TO_REPORT:
                    # Something might be wrong. Let people in debug rooms know.
                    status_message = "There's been no scan activity for {} status pings. There may be a problem." \
                                     .format(Metasmoke.status_pings_since_scan_activity)
                    log('warning', status_message)
                    chatcommunicate.tell_rooms_with("debug", status_message)
            else:
                Metasmoke.status_pings_since_scan_activity = 0
                Metasmoke.scan_stat_snapshot = current_ms_stats
        Metasmoke.send_status_ping()
