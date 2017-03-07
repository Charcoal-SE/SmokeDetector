import json
import requests
import time
# noinspection PyPackageRequirements
import websocket
# noinspection PyPackageRequirements
from bs4 import BeautifulSoup
from threading import Thread
from urlparse import urlparse
import metasmoke
from globalvars import GlobalVars
import datahandling


# noinspection PyClassHasNoInit,PyBroadException,PyMethodParameters
class DeletionWatcher:
    @classmethod
    def update_site_id_list(self):
        soup = BeautifulSoup(requests.get("https://meta.stackexchange.com/topbar/site-switcher/site-list").text,
                             "html.parser")
        site_id_dict = {}
        for site in soup.findAll("a", attrs={"data-id": True}):
            site_name = urlparse(site["href"]).netloc
            site_id = site["data-id"]
            site_id_dict[site_name] = site_id
        GlobalVars.site_id_dict = site_id_dict

    @classmethod
    def check_websocket_for_deletion(self, post_site_id, post_url, timeout):
        print("Deletion websocket started")
        time_to_check = time.time() + timeout
        post_id = post_site_id[0]
        post_type = post_site_id[2]
        if post_type == "answer":
            question_id = str(datahandling.get_post_site_id_link(post_site_id))
            if question_id is None:
                print("Couldn't find question ID")
                return
        else:
            question_id = post_id
        post_site = post_site_id[1]
        if post_site not in GlobalVars.site_id_dict:
            print("Post site not recognized")
            return
        site_id = GlobalVars.site_id_dict[post_site]

        ws = websocket.create_connection("wss://qa.sockets.stackexchange.com/")
        ws.send(site_id + "-question-" + question_id)

        print("Attempted websocket connection")

        while time.time() < time_to_check:
            ws.settimeout(time_to_check - time.time())
            try:
                a = ws.recv()
                print("Received from deletion websocket: " + a)
            except websocket.WebSocketTimeoutException:
                t_metasmoke = Thread(name="metasmoke send deletion stats",
                                     target=metasmoke.Metasmoke.send_deletion_stats_for_post, args=(post_url, False))
                t_metasmoke.start()
                print("websocket.WebSocketTimeoutException:")
                return False
            if a is not None and a != "":
                try:
                    action = json.loads(a)["action"]
                    print("Parsed action: " + str(action))
                    if action == "hb":
                        ws.send("hb")
                        continue
                    else:
                        d = json.loads(json.loads(a)["data"])
                except:
                    print("Caught exception in deletion WS parsing")
                    continue
                if d["a"] == "post-deleted" and str(d["qId"]) == question_id \
                        and ((post_type == "answer" and "aId" in d and str(d["aId"]) == post_id) or
                             post_type == "question"):

                    print("Caught websocket deletion signal")

                    t_metasmoke = Thread(name="metasmoke send deletion stats",
                                         target=metasmoke.Metasmoke.send_deletion_stats_for_post, args=(post_url, True))
                    t_metasmoke.start()
                    return True

        t_metasmoke = Thread(name="metasmoke send deletion stats",
                             target=metasmoke.Metasmoke.send_deletion_stats_for_post, args=(post_url, False))
        t_metasmoke.start()
        return False

    @classmethod
    def check_if_report_was_deleted(self, post_site_id, post_url, message):
        was_report_deleted = self.check_websocket_for_deletion(post_site_id, post_url, 1200)
        if was_report_deleted:
            try:
                message.delete()
            except:
                pass

    @classmethod
    def post_message_if_not_deleted(self, post_site_id, post_url, message_text, room):
        was_report_deleted = self.check_websocket_for_deletion(post_site_id, post_url, 300)
        if not was_report_deleted and not datahandling.is_false_positive(post_site_id[0:2]) and not \
                datahandling.is_ignored_post(post_site_id[0:2]):
            room.send_message(message_text)
