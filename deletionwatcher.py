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
from helpers import log
from parsing import fetch_post_id_and_site_from_url, to_protocol_relative
from tasks import Tasks


# noinspection PyClassHasNoInit,PyBroadException,PyMethodParameters
class DeletionWatcher:
    next_request_time = time.time() - 1

    def __init__(self):
        DeletionWatcher.update_site_id_list()
        self.posts = {}

        try:
            self.socket = websocket.create_connection("wss://qa.sockets.stackexchange.com/")
        except websocket.WebSocketException:
            log('error', 'DeletionWatcher failed to create a websocket connection')
            return

        if os.path.exists("deletionIDs.p"):
            with open("deletionIDs.p", "rb") as fh:
                for post in DeletionWatcher._check_batch(pickle.load(fh)):
                    self.subscribe(post, pickle=False)

                self._save()

        threading.Thread(name="deletion watcher", target=self._start, daemon=True).start()

    def _start(self):
        while True:
            msg = self.socket.recv()

            if msg:
                msg = json.loads(msg)
                action = msg["action"]

                if action == "hb":
                    self.socket.send("hb")
                else:
                    data = json.loads(msg["data"])

                    if data["a"] == "post-deleted":
                        try:
                            post_id, _, post_type, post_url, callbacks = self.posts[action]
                            del self.posts[action]

                            if not post_type == "answer" or ("aId" in data and str(data["aId"]) == post_id):
                                self.socket.send("-" + action)
                                Tasks.do(metasmoke.Metasmoke.send_deletion_stats_for_post, post_url, True)

                                for callback, max_time in callbacks:
                                    if not max_time or time.time() < max_time:
                                        callback()
                        except KeyError:
                            pass

    def subscribe(self, post_url, callback=None, pickle=True, timeout=None):
        post_id, post_site, post_type = fetch_post_id_and_site_from_url(post_url)

        if post_site not in GlobalVars.site_id_dict:
            log("warning", "unknown site {} when subscribing to {}".format(post_site, post_url))
            return

        if post_type == "answer":
            question_id = datahandling.get_post_site_id_link((post_id, post_site, post_type))

            if question_id is None:
                return
        else:
            question_id = post_id

        site_id = GlobalVars.site_id_dict[post_site]
        action = "{}-question-{}".format(site_id, question_id)
        max_time = (time.time() + timeout) if timeout else None

        if action not in self.posts:
            self.posts[action] = (post_id, post_site, post_type, post_url, [(callback, max_time)] if callback else [])
            try:
                self.socket.send(action)
            except websocket.WebSocketException:
                log('error', 'DeletionWatcher failed on sending {}'.format(action))
        elif callback:
            _, _, _, _, callbacks = self.posts[action]
            callbacks.append((callback, max_time))
        else:
            return

        if pickle:
            Tasks.do(self._save)

    def _save(self):
        pickle_output = {}

        for post_id, post_site, _, _, _ in self.posts.values():
            if post_site not in pickle_output:
                pickle_output[post_site] = [post_id]
            else:
                pickle_output[post_site].append(post_id)

        with open("deletionIDs.p", "wb") as pickle_file:
                pickle.dump(pickle_output, pickle_file)

    @staticmethod
    def _check_batch(saved):
        if time.time() < DeletionWatcher.next_request_time:
            time.sleep(DeletionWatcher.next_request_time - time.time())

        for site, posts in saved.items():
            ids = ";".join(post_id for post_id in posts if not DeletionWatcher._ignore((post_id, site)))
            uri = "https://api.stackexchange.com/2.2/posts/{}?site={}&key=IAkbitmze4B8KpacUfLqkw((".format(ids, site)
            res = requests.get(uri)
            json = res.json()

            if "items" not in json:
                log('warning',
                    'DeletionWatcher API request received no items in response (code {})'.format(res.status_code))
                log('warning', res.text)
                return

            if 'backoff' in json:
                DeletionWatcher.next_request_time = time.time() + json['backoff']

            for post in json['items']:
                if time.time() - post["creation_date"] < 7200:
                    yield to_protocol_relative(post["link"]).replace("/q/", "/questions/")

    @staticmethod
    def _ignore(post_site_id):
        return datahandling.is_false_positive(post_site_id) or datahandling.is_ignored_post(post_site_id) or \
            datahandling.is_auto_ignored_post(post_site_id)

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
