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
    only_modules_changed, blacklist_integrity_check, reload_modules
from gitmanager import GitManager
import findspam
from socketscience import SocketScience
import metasmoke_cache


MAX_MS_WEBSOCKET_RETRIES = 5
MAX_FAILURES = 10  # Preservative, 10 errors = MS down
NO_ACTIVITY_PINGS_TO_STANDBY = 8
NO_ACTIVITY_PINGS_TO_REPORT = 4


# noinspection PyClassHasNoInit,PyBroadException,PyUnresolvedReferences,PyProtectedMember
class Metasmoke:
    status_pings_since_scan_activity = 0
    last_ping_scan_time = 0
    last_ping_posts_scanned = 0

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
                        GlobalVars.metasmoke_last_ping_time = datetime.utcnow()
                        Metasmoke.handle_websocket_data(data)
                        Metasmoke.reset_failure_count()
                    except ConnectionError:
                        raise
                    except Exception as e:
                        Metasmoke.connect_websocket()
                        GlobalVars.metasmoke_failures += 1
                        log('error', e, f=True)
                        traceback.print_exc()
            except Exception:
                GlobalVars.metasmoke_failures += 1
                log('error', "Couldn't bind to MS websocket")
                if not has_succeeded:
                    failed_connection_attempts += 1
                    if failed_connection_attempts > MAX_MS_WEBSOCKET_RETRIES:
                        chatcommunicate.tell_rooms_with("debug", "Cannot initiate MS websocket." +
                                                        "  Manual `!!/reboot` is required once MS is up")
                        log('warning', "Cannot initiate MS websocket." +
                            " init_websocket() in metasmoke.py is terminating.")
                        break
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
            chatcommunicate.tell_rooms_with("metasmoke", message['message'])
        elif "autoflag_fp" in message:
            event = message["autoflag_fp"]

            chatcommunicate.tell_rooms(event["message"], ("debug", "site-" + event["site"]),
                                       ("no-site-" + event["site"],), notify_site="/autoflag_fp")
        elif "exit" in message:
            os._exit(message["exit"])
        elif "blacklist" in message:
            ids = (message['blacklist']['uid'], message['blacklist']['site'])

            datahandling.add_blacklisted_user(ids, "metasmoke", message['blacklist']['post'])
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
                        if not GlobalVars.on_branch:
                            # Restart if HEAD detached
                            log('warning', "Pulling remote with HEAD detached, checkout deploy", f=True)
                            exit_mode("checkout_deploy")
                        GlobalVars.reload()
                        findspam.FindSpam.reload_blacklists()
                        chatcommunicate.tell_rooms_with('debug', GlobalVars.s_norestart_blacklists)
                    elif only_modules_changed(remote_diff):
                        GitManager.pull_remote()
                        if not GlobalVars.on_branch:
                            # Restart if HEAD detached
                            log('warning', "Pulling remote with HEAD detached, checkout deploy", f=True)
                            exit_mode("checkout_deploy")
                        GlobalVars.reload()
                        reload_modules()
                        chatcommunicate.tell_rooms_with('debug', GlobalVars.s_norestart_findspam)
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
    def send_stats_on_post(title, link, reasons, body, username, user_link, why, owner_rep,
                           post_score, up_vote_count, down_vote_count):
        if GlobalVars.metasmoke_host is None:
            log('info', 'Attempted to send stats but metasmoke_host is undefined. Ignoring.')
            return
        elif GlobalVars.metasmoke_down:
            log('warning', "Metasmoke down, not sending stats.")
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            if len(why) > 4096:
                why = why[:2048] + ' ... ' + why[-2043:]  # Basic maths

            post = {'title': title, 'link': link, 'reasons': reasons,
                    'body': body, 'username': username, 'user_link': user_link,
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
    def send_feedback_for_post(post_link, feedback_type, user_name, user_id, chat_host):
        if GlobalVars.metasmoke_host is None:
            log('info', 'Received chat feedback but metasmoke_host is undefined. Ignoring.')
            return
        elif GlobalVars.metasmoke_down:
            log('warning', "Metasmoke is down, not sending feedback")
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
    def send_deletion_stats_for_post(post_link, is_deleted):
        if GlobalVars.metasmoke_host is None:
            log('info', 'Attempted to send deletion data but metasmoke_host is undefined. Ignoring.')
            return
        elif GlobalVars.metasmoke_down:
            log('warning', "Metasmoke is down, not sending deletion stats")
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
        elif GlobalVars.metasmoke_down:
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
                GlobalVars.metasmoke_last_ping_time = datetime.utcnow()  # Otherwise the ping watcher will exit(10)

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
        if GlobalVars.metasmoke_down:
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
        if GlobalVars.metasmoke_down:
            log('warning', "Metasmoke is down, not sending statistics")
            return
        # Get current apiquota from globalvars
        GlobalVars.apiquota_rw_lock.acquire()
        current_apiquota = GlobalVars.apiquota
        GlobalVars.apiquota_rw_lock.release()

        GlobalVars.posts_scan_stats_lock.acquire()
        if GlobalVars.post_scan_time != 0:
            posts_per_second = GlobalVars.num_posts_scanned / GlobalVars.post_scan_time
            payload = {'key': GlobalVars.metasmoke_key,
                       'statistic': {'posts_scanned': GlobalVars.num_posts_scanned, 'api_quota': current_apiquota,
                                     'post_scan_rate': posts_per_second}}
        else:
            payload = {'key': GlobalVars.metasmoke_key,
                       'statistic': {'posts_scanned': GlobalVars.num_posts_scanned, 'api_quota': current_apiquota}}

        GlobalVars.post_scan_time = 0
        GlobalVars.num_posts_scanned = 0
        GlobalVars.posts_scan_stats_lock.release()

        headers = {'Content-type': 'application/json'}

        if GlobalVars.metasmoke_host is not None:
            log('info', 'Sent statistics to metasmoke: ', payload['statistic'])
            Metasmoke.post("/statistics.json",
                           data=json.dumps(payload), headers=headers)

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
        if not GlobalVars.metasmoke_key:
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
        def func(url, *args, ignore_down=False, **kwargs):
            if not GlobalVars.metasmoke_host or (GlobalVars.metasmoke_down and not ignore_down):
                return None

            if 'timeout' not in kwargs:
                kwargs['timeout'] = 10.000  # Don't throttle by MS

            response = None  # Should return None upon failure, if any
            try:
                response = method(GlobalVars.metasmoke_host + url, *args, **kwargs)
            except Exception:
                GlobalVars.metasmoke_failures += 1
                if GlobalVars.metasmoke_failures >= MAX_FAILURES and not GlobalVars.metasmoke_down:
                    GlobalVars.metasmoke_down = True
                    chatcommunicate.tell_rooms_with(
                        'debug', '**Warning**: {}: {} latest connections to '
                        'metasmoke have failed. Disabling metasmoke'.format(
                            GlobalVars.location, GlobalVars.metasmoke_failures))
                # No need to log here because it's re-raised
                raise  # Maintain minimal difference to the original get/post methods
            else:
                GlobalVars.metasmoke_failures -= 1
                if GlobalVars.metasmoke_failures < 0:
                    GlobalVars.metasmoke_failures = 0

            return response
        return func

    get = request_sender.__func__(requests.get)
    post = request_sender.__func__(requests.post)

    @staticmethod
    def reset_failure_count():  # For use in other places
        GlobalVars.metasmoke_failures -= 1
        if GlobalVars.metasmoke_failures < 0:
            GlobalVars.metasmoke_failures = 0

    @staticmethod
    def send_status_ping_and_verify_scanning_if_active():
        in_standby_mode = GlobalVars.standby_mode or GlobalVars.no_se_activity_scan
        if not in_standby_mode:
            # This is the active instance, so should be scanning. If it's not scanning, then report or go to standby.

            # We're not changing the scan stats, so shouldn't need a lock.
            current_scan_time = GlobalVars.post_scan_time
            current_posts_scanned = GlobalVars.num_posts_scanned
            if current_scan_time == Metasmoke.last_ping_scan_time \
                    and current_posts_scanned == Metasmoke.last_ping_posts_scanned:
                # There's been no actvity since the last ping.
                Metasmoke.status_pings_since_scan_activity += 1
                if Metasmoke.status_pings_since_scan_activity >= NO_ACTIVITY_PINGS_TO_STANDBY:
                    # Assume something is very wrong. Report to debug rooms and go into standby mode.
                    error_message = "There's been no scan activity for {} status pings. Going into standby." \
                                    .format(Metasmoke.status_pings_since_scan_activity)
                    log('error', error_message)
                    chatcommunicate.tell_rooms_with("debug", error_message)
                    GlobalVars.standby_mode = True
                    # Let MS know immediately, to lessen potential wait time (e.g. if we fail to reboot).
                    Metasmoke.send_status_ping()
                    time.sleep(8)
                    exit_mode("standby")
                elif Metasmoke.status_pings_since_scan_activity >= NO_ACTIVITY_PINGS_TO_REPORT:
                    # Something might be wrong. Let people in debug rooms know.
                    status_message = "There's been no scan activity for {} status pings. There may be a problem." \
                                     .format(Metasmoke.status_pings_since_scan_activity)
                    log('warning', status_message)
                    chatcommunicate.tell_rooms_with("debug", status_message)
            else:
                Metasmoke.status_pings_since_scan_activity = 0
        Metasmoke.send_status_ping()
