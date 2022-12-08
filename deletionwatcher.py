# coding=utf-8
import json
import os.path
import time
import threading
from urllib.parse import urlparse

import requests
# noinspection PyPackageRequirements
import websocket

from globalvars import GlobalVars
import metasmoke
import datahandling
from helpers import log, get_se_api_default_params_questions_answers_posts_add_site
from parsing import fetch_post_id_and_site_from_url, to_protocol_relative
from tasks import Tasks


PICKLE_FILENAME = "deletionIDs.p"


# noinspection PyClassHasNoInit,PyBroadException,PyMethodParameters
class DeletionWatcher:
    next_request_time = time.time() - 1

    def __init__(self):
        if GlobalVars.no_deletion_watcher:
            return
        self.posts = {}
        self.posts_lock = threading.Lock()
        self.save_handle = None
        self.save_handle_lock = threading.Lock()

        try:
            self.socket = websocket.create_connection("wss://qa.sockets.stackexchange.com/")
        except websocket.WebSocketException:
            self.socket = None
            log('error', 'DeletionWatcher failed to create a websocket connection')
            return

        if datahandling.has_pickle(PICKLE_FILENAME):
            pickle_data = datahandling.load_pickle(PICKLE_FILENAME)
            for post in DeletionWatcher._check_batch(pickle_data):
                self.subscribe(post, pickle=False)
            self._schedule_save()

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
                            with self.posts_lock:
                                post_id, _, _, post_url, callbacks = self.posts[action]

                            if post_id == str(data["aId"] if "aId" in data else data["qId"]):
                                with self.posts_lock:
                                    del self.posts[action]
                                Tasks.do(self._unsubscribe, action)
                                Tasks.do(metasmoke.Metasmoke.send_deletion_stats_for_post, post_url, True)

                                for callback, max_time in callbacks:
                                    if not max_time or time.time() < max_time:
                                        callback()
                        except KeyError:
                            pass

    def subscribe(self, post_url, callback=None, pickle=True, timeout=None):
        if GlobalVars.no_deletion_watcher:
            return
        post_id, post_site, post_type = fetch_post_id_and_site_from_url(post_url)

        with GlobalVars.site_id_dict_lock:
            site_id = GlobalVars.site_id_dict.get(post_site, None)
        if not site_id:
            log("warning", "unknown site {} when subscribing to {}".format(post_site, post_url))
            return

        if post_type == "answer":
            question_id = datahandling.get_post_site_id_link((post_id, post_site, post_type))

            if question_id is None:
                return
        else:
            question_id = post_id

        action = "{}-question-{}".format(site_id, question_id)
        max_time = (time.time() + timeout) if timeout else None

        with self.posts_lock:
            if action not in self.posts:
                self.posts[action] = (post_id, post_site, post_type, post_url,
                                      [(callback, max_time)] if callback else [])
                Tasks.do(self._subscribe, action)
            elif callback:
                _, _, _, _, callbacks = self.posts[action]
                callbacks.append((callback, max_time))
            else:
                return

        if pickle:
            self._schedule_save()

    def _subscribe(self, action):
        if self.socket:
            try:
                self.socket.send(action)
            except websocket.WebSocketException:
                log('error', 'DeletionWatcher failed to subscribe to {}'.format(action))
        else:
            log('warning', 'DeletionWatcher tried to subscribe to {}, but no WebSocket available.'.format(action))

    def _schedule_save(self):
        with self.save_handle_lock:
            if self.save_handle:
                self.save_handle.cancel()
            save_handle = Tasks.do(self._save)

    def _save(self):
        pickle_output = {}

        with self.posts_lock:
            for post_id, post_site, _, _, _ in self.posts.values():
                if post_site not in pickle_output:
                    pickle_output[post_site] = [post_id]
                else:
                    pickle_output[post_site].append(post_id)

        datahandling.dump_pickle(PICKLE_FILENAME, pickle_output)

    @staticmethod
    def _check_batch(saved):
        if time.time() < DeletionWatcher.next_request_time:
            time.sleep(DeletionWatcher.next_request_time - time.time())

        for site, posts in saved.items():
            ids = ";".join(post_id for post_id in posts if not DeletionWatcher._ignore((post_id, site)))
            uri = GlobalVars.se_api_url_base + "posts/{}".format(ids)
            params = get_se_api_default_params_questions_answers_posts_add_site(site)
            res = requests.get(uri, params=params)
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

    def _unsubscribe(self, action):
        if self.socket:
            try:
                self.socket.send("-" + action)
            except websocket.WebSocketException:
                log('error', 'DeletionWatcher failed to unsubscribe to {}'.format(action))
        else:
            log('warning', 'DeletionWatcher tried to unsubscribe to {}, but no WebSocket available.'.format(action))

    @staticmethod
    def _ignore(post_site_id):
        return datahandling.is_false_positive(post_site_id) or datahandling.is_ignored_post(post_site_id) or \
            datahandling.is_auto_ignored_post(post_site_id)
