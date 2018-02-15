# coding=utf-8
import json
import os.path
import pickle
import requests
import time
import threading
# noinspection PyPackageRequirements
import websocket
# noinspection PyPackageRequirements
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import chatcommunicate
import metasmoke
from globalvars import GlobalVars
import datahandling
from parsing import fetch_post_id_and_site_from_url
from tasks import Tasks


# noinspection PyClassHasNoInit,PyBroadException,PyMethodParameters
class DeletionWatcher:
    def __init__(self):
        DeletionWatcher.update_site_id_list()

        self.socket = websocket.create_connection("wss://qa.sockets.stackexchange.com/")
        self.posts = {}

        if os.path.exists("deletionIDs.p"):
            with open("deletionIDs.p", "rb") as fh:
                for post in DeletionWatcher._check_batch(pickle.load(fh)):
                    self.subscribe(post, pickle=False)

                self._save()

        threading.Thread(name="deletion watcher", target=self._start, daemon=True)

    def _start(self):
        while True:
            msg = self.socket.recv()

            if msg:
                msg = json.loads(msg)
                action = msg["action"]

                if action == "hb":
                    ws.send("hb")
                else:
                    data = json.loads(msg)["data"]

                    if data["a"] == "post-deleted":
                        try:
                            post_id, _, post_type, post_url, callback, max_time = self.posts[action["action"]]

                            if not post_type == "answer" or ("aId" in d and str(d["aId"]) == post_id)):
                                self.socket.send("-" + action)
                                Tasks.do(metasmoke.Metasmoke.send_deletion_stats_for_post, post_url, True)

                                if callback and (not max_time or time.time() < max_time):
                                    callback()
                        except KeyError:
                            pass

    def subscribe(post_url, callback=None, pickle=True, timeout=300):
        post_id, post_site, post_type = fetch_post_id_and_site_from_url(post_url)

        if post_site not in GlobalVars.site_id_dict:
            return

        if post_type == "answer":
            question_id = str(datahandling.get_post_site_id_link(post_site_id))

            if question_id is None:
                return
        else:
            question_id = post_id

        site_id = GlobalVars.site_id_dict[post_site]
        action = "{}-question-{}".format(site_id, question_id)
        max_time = time.time() + timeout

        self.posts[action] = (post_id, post_site, post_type, post_url, callback, max_time)
        self.socket.send(action)

        if pickle:
            Tasks.do(self._save)

    def _save():
        pickle_output = {}

        for post_id, post_site, _, _, _, _ in self.posts.values():
            if post_site not in pickle_output:
                pickle_output[post_site] = [post_id]
            else:
                pickle_output[post_site].append(post_id)

        with open("deletionIDs.p", "wb") as pickle_file:
                pickle.dump(pickle_output, pickle_file)

    @staticmethod
    def _check_batch(saved):
        for site, posts in saved:
            ids = ";".join([post_id for post_id in posts])
            uri = "https://api.stackexchange.com/2.2/posts/{}?site={}&key=IAkbitmze4B8KpacUfLqkw((".format(ids, site)

            for post in requests.get(uri).json()["items"]:
                yield post["link"]

    @staticmethod
    def update_site_id_list():
        soup = BeautifulSoup(requests.get("https://meta.stackexchange.com/topbar/site-switcher/site-list").text,
                             "html.parser")
        site_id_dict = {}
        for site in soup.findAll("a", attrs={"data-id": True}):
            site_name = urlparse(site["href"]).netloc
            site_id = site["data-id"]
            site_id_dict[site_name] = site_id
        GlobalVars.site_id_dict = site_id_dict
