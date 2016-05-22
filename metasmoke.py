import json
import requests
import os
import time
from globalvars import GlobalVars
import threading


class Metasmoke:
    @classmethod
    def send_stats_on_post(self, title, link, reasons, body, username, user_link, why, owner_rep, post_score, up_vote_count, down_vote_count):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined, not reporting"
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            post = {'title': title, 'link': link, 'reasons': reasons, 'body': body, 'username': username, 'user_link': user_link, 'why': why, 'user_reputation': owner_rep, 'score': post_score, 'upvote_count': up_vote_count, 'downvote_count': down_vote_count}

            post = dict((k, v) for k, v in post.iteritems() if v)  # Remove None values (if they somehow manage to get through)

            payload = {'post': post, 'key': metasmoke_key}

            headers = {'Content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/posts.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e

    @classmethod
    def send_feedback_for_post(self, post_link, feedback_type, user_name, user_id):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined; not reporting"
            return

        metasmoke_key = GlobalVars.metasmoke_key

        try:
            payload = {
                'feedback': {
                    'user_name': user_name,
                    'chat_user_id': user_id,
                    'feedback_type': feedback_type,
                    'post_link': post_link
                },
                'key': metasmoke_key
            }

            headers = {'Content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/feedbacks.json", data=json.dumps(payload), headers=headers)

        except Exception as e:
            print e

    @classmethod
    def send_deletion_stats_for_post(self, post_link, is_deleted):
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

    @classmethod
    def send_status_ping(self):
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

            headers = {'Content-type': 'application/json'}
            response = requests.post(GlobalVars.metasmoke_host + "/status-update.json", data=json.dumps(payload), headers=headers)

            if response.status_code == 201:  # 200 = successful status creation; 201 = new commit status
                json_response = response.json()
                commit_response = json_response["commit_status"]
                if commit_response["status"] == "success":
                    autopull_message = "Message contains 'autopull', pulling..."
                    GlobalVars.charcoal_hq.send_message(
                        "[Continuous integration]({status}) on commit [{commit}](//github.com/Charcoal-SE/SmokeDetector/commit/{sha}) ".format(status=commit_response["ci_url"], commit=commit_response["commit_sha"][:7], sha=commit_response["commit_sha"]) +
                        "(*{commit}*) succeeded!{optional_autopull_message}".format(commit=commit_response["commit_message"].split("\n")[0], optional_autopull_message=autopull_message if "autopull" in commit_response["commit_message"] else "")
                    )
                    if "autopull" in commit_response["commit_message"]:
                        time.sleep(2)
                        os._exit(3)

        except Exception as e:
            print e
