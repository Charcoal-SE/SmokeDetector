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
from helpers import (log, get_se_api_default_params_questions_answers_posts_add_site, get_se_api_url_for_route,
                     recover_websocket, chunk_list)
from parsing import fetch_post_id_and_site_from_url, to_protocol_relative
from tasks import Tasks


PICKLE_FILENAME = "deletionIDs.p"
DELETION_WATCH_MIN_SECONDS = 7200


# noinspection PyClassHasNoInit,PyBroadException,PyMethodParameters
class DeletionWatcher:
    next_request_time = time.time() - 1

    def __init__(self):
        if GlobalVars.no_deletion_watcher:
            return
        # posts is a dict with the WebSocket action as keys: {site_id}-question-{question_id}
        #   The value of each is a dict with post IDs as the key.
        #     The value of each of those is a tuple:
        #        (post_id, post_site, post_type, post_url, question_id, max_watch_time, [(callback, max_callback_time)])
        #   Actions are added when a post is subscribed. They are removed when a WebSocket message is received
        #   indicating the first post subscribed for that question is deleted.
        #   Upon reboot, questions are not resubscribed to if the last subscription was more than
        #   DELETION_WATCH_MIN_SECONDS ago (currently 7200).
        self.posts = {}
        self.posts_lock = threading.RLock()

        try:
            self.socket = websocket.create_connection(GlobalVars.se_websocket_url,
                                                      timeout=GlobalVars.se_websocket_timeout)
            self.connect_time = time.time()
            self.hb_time = None
        except websocket.WebSocketException:
            self.socket = None
            log('error', '{}: WebSocket: failed to create a websocket connection'.format(self.__class__.__name__))
            return

        if datahandling.has_pickle(PICKLE_FILENAME):
            pickle_info = datahandling.load_pickle(PICKLE_FILENAME)
            if 'version' not in pickle_info:
                # original pickle version
                for post_url in DeletionWatcher._check_batch(pickle_info):
                    self.subscribe(post_url)
            elif pickle_info['version'] == '2':
                with self.posts_lock:
                    self.posts = pickle_info['posts']
                self.expunge_expired_posts(False)
                self._subscribe_to_all_saved_posts()

        threading.Thread(name=self.__class__.__name__, target=self._start, daemon=True).start()

    def _start(self):
        while True:
            try:
                msg = self.socket.recv()

                if msg:
                    msg = json.loads(msg)
                    action = msg["action"]

                    if action == "hb":
                        self.hb_time = time.time()
                        self.socket.send("hb")
                    else:
                        data = json.loads(msg["data"])

                        if data["a"] == "post-deleted":
                            try:
                                post_id = str(data["aId"] if "aId" in data else data["qId"])
                                with self.posts_lock:
                                    _, _, _, post_url, _, _, callbacks = self.posts[action][post_id]
                                    del self.posts[action][post_id]
                                    if len(self.posts[action]) == 0:
                                        del self.posts[action]
                                        Tasks.do(self._unsubscribe, action)
                                Tasks.do(metasmoke.Metasmoke.send_deletion_stats_for_post, post_url, True)
                                now = time.time()
                                for callback, max_time in callbacks:
                                    if not max_time or now < max_time:
                                        callback()
                            except KeyError:
                                pass
            except websocket.WebSocketException as e:
                ws = self.socket
                self.socket = None
                self.socket = recover_websocket(self.__class__.__name__, ws, e, self.connect_time, self.hb_time)
                self._subscribe_to_all_saved_posts()
                self.connect_time = time.time()
                self.hb_time = None

    def expunge_expired_posts(self, unsubscribe=True):
        now = time.time()
        with self.posts_lock:
            actions = list(self.posts.keys())
            for action in actions:
                post_ids = list(self.posts[action].keys())
                for post_id in post_ids:
                    _, _, _, _, _, max_time, _ = self.posts[action][post_id]
                    if now > max_time:
                        del self.posts[action][post_id]
                if len(self.posts[action]) == 0:
                    del self.posts[action]
                    if unsubscribe:
                        Tasks.do(self._unsubscribe, action)

    def _subscribe_to_all_saved_posts(self):
        with self.posts_lock:
            for action in self.posts:
                self._subscribe(action)

    def subscribe(self, post_url, callback=None, timeout=None):
        if GlobalVars.no_deletion_watcher:
            return
        post_id, post_site, post_type = fetch_post_id_and_site_from_url(post_url)

        with GlobalVars.site_id_dict_lock:
            site_id = GlobalVars.site_id_dict.get(post_site, None)
        if not site_id:
            log("warning", "{}: unknown site {} when subscribing to {}".format(self.__class__.__name__, post_site,
                                                                               post_url))
            return

        if post_type == "answer":
            question_id = datahandling.get_post_site_id_link((post_id, post_site, post_type))

            if question_id is None:
                return
        else:
            question_id = post_id

        action = "{}-question-{}".format(site_id, question_id)
        now = time.time()
        max_time = (now + timeout) if timeout else None

        needs_subscribe = False
        post_id = str(post_id)
        with self.posts_lock:
            if action not in self.posts:
                self.posts[action] = {}
                needs_subscribe = True
            callbacks = []
            if post_id in self.posts[action]:
                _, _, _, _, _, _, callbacks = self.posts[action][post_id]
            if callback:
                callbacks.append((callback, max_time))
            # This is fully replaced in order to update the max_watch_time
            self.posts[action][post_id] = (post_id, post_site, post_type, post_url, question_id,
                                           now + DELETION_WATCH_MIN_SECONDS, callbacks)
        if needs_subscribe:
            Tasks.do(self._subscribe, action)

    def _subscribe(self, action):
        if self.socket:
            try:
                self.socket.send(action)
            except websocket.WebSocketException:
                log('error', '{}: failed to subscribe to {}'.format(self.__class__.__name__, action))
        else:
            log('warning', '{}: tried to subscribe to {}, but no WebSocket available.'.format(self.__class__.__name__,
                                                                                              action))

    def save(self):
        # We save a copy of the self.posts data, but with the calbacks removed.
        if GlobalVars.no_deletion_watcher:
            return
        pickle_data = {}

        with self.posts_lock:
            for action in self.posts:
                pickle_data[action] = {}
                for post in self.posts[action]:
                    (post_id, post_site, post_type, post_url, question_id, max_time, _) = self.posts[action][post]
                    pickle_data[action][post] = (post_id, post_site, post_type, post_url, question_id, max_time, [])
        pickle_output = {
            'version': '2',
            'posts': pickle_data,
        }
        datahandling.dump_pickle(PICKLE_FILENAME, pickle_output)

    @staticmethod
    def _check_batch(saved):
        # This was used with version 1 of the pickle. Version 2 of the pickle was in development on 2024-10-27.
        # Once some time has past (hours), this can be removed and handling of version one can change to ignoring
        # it, as the max watch time will have elapsed and nothing from it would be used anyway.
        if time.time() < DeletionWatcher.next_request_time:
            time.sleep(DeletionWatcher.next_request_time - time.time())

        for site, posts in saved.items():
            not_ignored_posts = [post_id for post_id in posts if not DeletionWatcher._ignore((post_id, site))]
            for chunk in chunk_list(not_ignored_posts, 100):
                ids = ";".join(chunk)
                uri = get_se_api_url_for_route("posts/{}".format(ids))
                params = get_se_api_default_params_questions_answers_posts_add_site(site)
                res = requests.get(uri, params=params, timeout=GlobalVars.default_requests_timeout)
                try:
                    response_data = res.json()
                except json.decoder.JSONDecodeError:
                    log('warning',
                        'DeletionWatcher SE API request: invalid JSON in response (code {})'.format(res.status_code))
                    log('warning', res.text)
                    continue

                if 'backoff' in response_data:
                    DeletionWatcher.next_request_time = time.time() + response_data['backoff']

                if "items" not in response_data:
                    log('warning',
                        'DeletionWatcher SE API request: no items in response (code {})'.format(res.status_code))
                    log('warning', res.text)
                    continue

                for post in response_data['items']:
                    compare_date = post["last_edit_date"] if "last_edit_date" in post else post["creation_date"]
                    if time.time() - compare_date < DELETION_WATCH_MIN_SECONDS:
                        yield to_protocol_relative(post["link"]).replace("/q/", "/questions/")

    def _unsubscribe(self, action):
        if self.socket:
            try:
                self.socket.send("-" + action)
            except websocket.WebSocketException:
                log('error', '{}: failed to unsubscribe to {}'.format(self.__class__.__name__, action))
        else:
            log('warn', '{}: tried to unsubscribe to {}, but no WebSocket available.'.format(self.__class__.__name__,
                                                                                             action))

    @staticmethod
    def _ignore(post_site_id):
        return datahandling.is_false_positive(post_site_id) or datahandling.is_ignored_post(post_site_id) or \
            datahandling.is_auto_ignored_post(post_site_id)
