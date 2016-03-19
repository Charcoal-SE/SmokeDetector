import json
import requests
import time
import websocket
from bs4 import BeautifulSoup
from globalvars import GlobalVars
from datahandling import get_post_site_id_link, get_special_room_report


class DeletionWatcher:
    @classmethod
    def update_site_id_list(self):
        soup = BeautifulSoup(requests.get("http://meta.stackexchange.com/topbar/site-switcher/site-list").text)
        site_id_dict = {}
        for site in soup.findAll("a", attrs={"data-id": True}):
            site_name = site["href"][2:]
            site_id = site["data-id"]
            site_id_dict[site_name] = site_id
        GlobalVars.site_id_dict = site_id_dict

    @classmethod
    def check_websocket_for_deletion(self, post_site_id, message):
        time_to_check = time.time() + 120
        post_id = post_site_id[0]
        post_type = post_site_id[2]
        if post_type == "answer":
            question_id = str(get_post_site_id_link(post_site_id))
            if question_id is None:
                return
        else:
            question_id = post_id
        post_site = post_site_id[1]
        if post_site not in GlobalVars.site_id_dict:
            return
        site_id = GlobalVars.site_id_dict[post_site]

        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send(site_id + "-question-" + question_id)

        while time.time() < time_to_check:
            a = ws.recv()
            if a is not None and a != "":
                try:
                    d = json.loads(json.loads(a)["data"])
                except:
                    continue
                if d["a"] == "post-deleted" and str(d["qId"]) == question_id and ((post_type == "answer" and "aId" in d and str(d["aId"]) == post_id) or post_type == "question"):
                    try:
                        message.delete()
                        special_room_report = get_special_room_report(post_site_id)
                        if special_room_report is not None:
                            special_room_report.delete()
                    except:
                        pass
                    return
