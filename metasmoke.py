import json
import requests


class Metasmoke:
    @classmethod
    def send_stats_on_post(self, title, reasons):
        try:
            payload = {'post': {'title': title, 'reasons': reasons}}

            headers = {'Content-type': 'application/json'}
            requests.post("http://localhost:3000/posts.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e
