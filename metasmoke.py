import json
import requests
from globalvars import GlobalVars


class Metasmoke:
    @classmethod
    def send_stats_on_post(self, title, link, reasons, body):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined, not reporting"
            return

        try:
            payload = {'post': {'title': title, 'link': link, 'reasons': reasons, 'body': body}}

            headers = {'Content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/posts.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e

    @classmethod
    def send_feedback_for_post(self, post_link, feedback_type, user_name):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined; not reporting"
            return

        try:
            payload = {'feedback': {'user_name': user_name, 'feedback_type': feedback_type, 'post_link': post_link}}

            headers = {'Content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/feedbacks.json", data=json.dumps(payload), headers=headers)

        except Exception as e:
            print e
