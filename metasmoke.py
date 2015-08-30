import json
import requests
from globalvars import GlobalVars


class Metasmoke:
    @classmethod
    def send_stats_on_post(self, title, link, reasons):
        if GlobalVars.metasmoke_host is None:
            print "Metasmoke location not defined, not reporting"
            return

        try:
            payload = {'post': {'title': title, 'link': link, 'reasons': reasons}}

            headers = {'Content-type': 'application/json'}
            requests.post(GlobalVars.metasmoke_host + "/posts.json", data=json.dumps(payload), headers=headers)
        except Exception as e:
            print e
