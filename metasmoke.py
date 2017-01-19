import json
import requests
from globalvars import GlobalVars
import threading
# noinspection PyPackageRequirements
import websocket
from collections import Iterable
import sys
import traceback
import time
import os
import datahandling
import parsing
import apigetpost
import spamhandling


# noinspection PyClassHasNoInit,PyBroadException,PyUnresolvedReferences,PyProtectedMember
class Metasmoke:
    @staticmethod
    def init_websocket():
        has_succeded = False
        while True:
            try:
                GlobalVars.metasmoke_ws = websocket.create_connection(GlobalVars.metasmoke_ws_host,
                                                                      origin=GlobalVars.metasmoke_host)
                payload = json.dumps({"command": "subscribe",
                                      "identifier": "{\"channel\":\"SmokeDetectorChannel\","
                                      "\"key\":\"" + GlobalVars.metasmoke_key + "\"}"})
                GlobalVars.metasmoke_ws.send(payload)
                
                
                GlobalVars.metasmoke_ws.settimeout(10)

                has_succeded = True
                while True:
                    a = GlobalVars.metasmoke_ws.recv()
                    try:
                        data = json.loads(a)
                        Metasmoke.handle_websocket_data(data)
                    except Exception, e:
                        GlobalVars.metasmoke_ws = websocket.create_connection(GlobalVars.metasmoke_ws_host,
                                                                              origin=GlobalVars.metasmoke_host)
                        payload = json.dumps({"command": "subscribe",
                                              "identifier": "{\"channel\":\"SmokeDetectorChannel\"}"})
                        GlobalVars.metasmoke_ws.send(payload)
                        print e
                        try:
                            exc_info = sys.exc_info()
                            traceback.print_exception(*exc_info)
                        except:
                            print "meh"
            except:
                print "Couldn't bind to MS websocket"
                if not has_succeded:
                    break
                else:
                    time.sleep(10)


    @staticmethod
    def handle_websocket_data(data):
        last_recieved = time.gmtime()
        
        if "message" not in data:
            return

        message = data['message']
        if isinstance(message, Iterable):
            if "message" in message:
                GlobalVars.charcoal_hq.send_message(message['message'])
            elif "blacklist" in message:
                datahandling.add_blacklisted_user((message['blacklist']['uid'], message['blacklist']['site']),
                                                  "metasmoke", message['blacklist']['post'])
            elif "naa" in message:
                post_site_id = parsing.fetch_post_id_and_site_from_url(message["naa"]["post_link"])
                datahandling.add_ignored_post(post_site_id[0:2])
            elif "fp" in message:
                post_site_id = parsing.fetch_post_id_and_site_from_url(message["fp"]["post_link"])
                datahandling.add_false_positive(post_site_id[0:2])
            elif "report" in message:
                post_data = apigetpost.api_get_post(message["report"]["post_link"])
                if post_data is None or post_data is False:
                    return
                if datahandling.has_already_been_posted(post_data.site, post_data.post_id, post_data.title) \
                        and not datahandling.is_false_positive((post_data.post_id, post_data.site)):
                    return
                user = parsing.get_user_from_url(post_data.owner_url)
                if user is not None:
                    datahandling.add_blacklisted_user(user, "metasmoke", post_data.post_url)
                why = u"Post manually reported by user *{}* from metasmoke.\n".format(message["report"]["user"])
                spamhandling.handle_spam(title=post_data.title,
                                         body=post_data.body,
                                         poster=post_data.owner_name,
                                         site=post_data.site,
                                         post_url=post_data.post_url,
                                         poster_url=post_data.owner_url,
                                         post_id=post_data.post_id,
                                         reasons=["Manually reported " + post_data.post_type],
                                         is_answer=post_data.post_type == "answer",
                                         why=why,
                                         owner_rep=post_data.owner_rep,
                                         post_score=post_data.score,
                                         up_vote_count=post_data.up_vote_count,
                                         down_vote_count=post_data.down_vote_count,
                                         question_id=post_data.question_id)
            elif "commit_status" in message:
                c = message["commit_status"]
                sha = c["commit_sha"][:7]
                if c["commit_sha"] != os.popen('git log --pretty=format:"%H" -n 1').read():
                    if c["status"] == "success":
                        if "autopull" in c["commit_message"]:
                            s = "[CI]({ci_link}) on {commit_sha} succeeded. Message contains 'autopull', pulling..." \
                                .format(ci_link=c["ci_url"], commit_sha=sha)
                            GlobalVars.charcoal_hq.send_message(s)
                            time.sleep(2)
                            os._exit(3)
                        else:
                            s = "[CI]({ci_link}) on {commit_sha} succeeded.".format(ci_link=c["ci_url"], commit_sha=sha)
                    elif c["status"] == "failure":
                        s = "[CI]({ci_link}) on {commit_sha} failed.".format(ci_link=c["ci_url"], commit_sha=sha)

                    # noinspection PyUnboundLocalVariable
                    GlobalVars.charcoal_hq.send_message(s)


    @staticmethod
    def send_stats_on_post(title, link, reasons, body, username, user_link, why, owner_rep,
                           post_score, up_vote_count, down_vote_count):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined, not reporting"
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            if len(why) > 1024:
                why = why[:512] + '...' + why[-512:]

            post = {'title': title, 'link': link, 'reasons': reasons,
                    'body': body, 'username': username, 'user_link': user_link,
                    'why': why, 'user_reputation': owner_rep, 'score': post_score,
                    'upvote_count': up_vote_count, 'downvote_count': down_vote_count}

            # Remove None values (if they somehow manage to get through)
            post = dict((k, v) for k, v in post.iteritems() if v)

            payload = {'post': post, 'key': metasmoke_key}
            headers = {'Content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/posts.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e

    @staticmethod
    def send_feedback_for_post(post_link, feedback_type, user_name, user_id, chat_host):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined; not reporting"
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
            requests.post(GlobalVars.metasmoke_host + "/feedbacks.json", data=json.dumps(payload), headers=headers)

        except Exception as e:
            print e

    @staticmethod
    def send_deletion_stats_for_post(post_link, is_deleted):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined; not reporting deletion stats"
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
            requests.post(GlobalVars.metasmoke_host + "/deletion_logs.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e

    @staticmethod
    def send_status_ping():
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined; not sending status ping"
            return

        threading.Timer(60, Metasmoke.send_status_ping).start()
        metasmoke_key = GlobalVars.metasmoke_key

        try:
            payload = {
                'location': GlobalVars.location,
                'key': metasmoke_key
            }

            headers = {'content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/status-update.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e

    @staticmethod
    def update_code_privileged_users_list():
        payload = {'key': GlobalVars.metasmoke_key}
        headers = {'Content-type': 'application/json'}
        response = requests.get(GlobalVars.metasmoke_host + "/api/users/code_privileged",
                                data=json.dumps(payload), headers=headers).json()['items']

        GlobalVars.code_privileged_users = {
            GlobalVars.charcoal_room_id: response["stackexchange_chat_ids"],
            GlobalVars.meta_tavern_room_id: response["meta_stackexchange_chat_ids"],
            GlobalVars.socvr_room_id: response["stackoverflow_chat_ids"]
        }

    @staticmethod
    def determine_if_autoflagged(post_url):
        """
        Given the URL for a post, determine whether or not it has been autoflagged.
        """
        payload = {'key': GlobalVars.metasmoke_key,
                   'urls': post_url}
        headers = {'Content-type': 'application/json'}
        autoflagged = requests.get(GlobalVars.metasmoke_host + "/api/posts/urls",
                                   data=json.dumps(payload), headers=headers).json()['items'][0]['autoflagged']
        is_autoflagged = autoflagged['flagged']
        names = autoflagged['names']

        return is_autoflagged, names

    @staticmethod
    def stop_autoflagging():
        payload = {'key': GlobalVars.metasmoke_key}
        headers = {'Content-type': 'application/json'}

        requests.post(GlobalVars.metasmoke_host + "/flagging/smokey_disable",
                      data=json.dumps(payload), headers=headers)

    @staticmethod
    def send_statistics(should_repeat=True):
        GlobalVars.posts_scan_stats_lock.acquire()
        if GlobalVars.post_scan_time != 0:
            posts_per_second = GlobalVars.num_posts_scanned / GlobalVars.post_scan_time
            payload = {'key': GlobalVars.metasmoke_key,
                       'statistic': {'posts_scanned': GlobalVars.num_posts_scanned, 'api_quota': GlobalVars.apiquota,
                                     'post_scan_rate': posts_per_second}}
        else:
            payload = {'key': GlobalVars.metasmoke_key,
                       'statistic': {'posts_scanned': GlobalVars.num_posts_scanned, 'api_quota': GlobalVars.apiquota}}

        GlobalVars.post_scan_time = 0
        GlobalVars.num_posts_scanned = 0
        GlobalVars.posts_scan_stats_lock.release()

        headers = {'Content-type': 'application/json'}

        requests.post(GlobalVars.metasmoke_host + "/statistics.json",
                      data=json.dumps(payload), headers=headers)

        if should_repeat:
            threading.Timer(600, Metasmoke.send_statistics).start()
