import json
import requests
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
            payload = {'feedback': {'user_name': user_name, 'chat_user_id': user_id, 'feedback_type': feedback_type, 'post_link': post_link}, 'key': metasmoke_key}

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
            payload = {'deletion_log': {'is_deleted': is_deleted, 'post_link': post_link}, 'key': metasmoke_key}

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
            payload = {'location': GlobalVars.location, 'key': metasmoke_key}

            headers = {'Content-type': 'application/json'}
            response = requests.post(GlobalVars.metasmoke_host + "/status-update.json", data=json.dumps(payload), headers=headers)

            if response.status_code == 201:  # 200 = successful status creation; 201 = new commit status
                json = response.json()
                if json["status"] == "success":
                    GlobalVars.charcoal_hq.send_message("CI on commit " + json["commit_sha"] + " (*" + json["commit_message"] + "*) succeeded!")

        except Exception as e:
            print e
