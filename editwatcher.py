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
import chatcommunicate
import datahandling
from helpers import log, add_to_global_bodyfetcher_queue_in_new_thread, recover_websocket
from parsing import fetch_post_id_and_site_from_url
from tasks import Tasks

PICKLE_FILENAME = "editActions.p"
DEFAULT_TIMEOUT = 10 * 60  # 10 minutes


# noinspection PyClassHasNoInit,PyBroadException,PyMethodParameters
class EditWatcher:
    def __init__(self):
        if GlobalVars.no_edit_watcher:
            self.socket = None
            return
        # posts is a dict with the WebSocket action, {site_id}-question-{question_id}, as keys
        # with each value being: (site_id, hostname, question_id, max_time)
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
            pickle_data = datahandling.load_pickle(PICKLE_FILENAME)
            with self.posts_lock:
                self.posts = pickle_data
            self._subscribe_to_saved_posts()  # This expunges old entries, so we don't need to do that here.

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
                        now = time.time()
                        with self.posts_lock:
                            site_id, hostname, question_id, max_time = self.posts.get(action, (None, None, None, now))
                            if site_id and max_time <= now:
                                del self.posts[action]
                                Tasks.do(self._unsubscribe, action)
                        if max_time > now and data["a"] == "post-edit":
                            add_to_global_bodyfetcher_queue_in_new_thread(hostname, question_id, False,
                                                                          source=self.__class__.__name__)
                    Tasks.do(self._unsubscribe_to_expired_posts_and_expunge)
            except websocket.WebSocketException as e:
                ws = self.socket
                self.socket = None
                self.socket = recover_websocket(self.__class__.__name__, ws, e, self.connect_time, self.hb_time)
                self._subscribe_to_saved_posts()
                self.connect_time = time.time()
                self.hb_time = None

    def _unsubscribe_to_expired_posts_and_expunge(self):
        now = time.time()
        with self.posts_lock:
            to_unsubscribe = list(action for action, value in self.posts.items() if value[-1] <= now)
        self._expunge_expired_posts(now=now)
        for action in to_unsubscribe:
            self._unsubscribe(action)

    def _expunge_expired_posts(self, now=None):
        if now is None:
            now = time.time()
        with self.posts_lock:
            self.posts = {action: value for action, value in self.posts.items() if value[-1] > now}

    def _subscribe_to_saved_posts(self):
        self._expunge_expired_posts()
        with self.posts_lock:
            for action in self.posts:
                self._subscribe(action)

    def subscribe(self, post_url=None, hostname=None, site_id=None, question_id=None,
                  timeout=DEFAULT_TIMEOUT, max_time=None, from_time=None):
        if GlobalVars.no_edit_watcher:
            return
        if post_url and not ((hostname or site_id) and question_id):
            post_id, hostname, post_type = fetch_post_id_and_site_from_url(post_url)
            if post_type == "answer":
                question_id = datahandling.get_post_site_id_link((post_id, hostname, post_type))
                if question_id is None:
                    log("warning", "{}: Unable to get question ID when subscribing to: hostname: "
                                   "{} :: post ID:{} when subscribing to {}".format(self.__class__.__name__, hostname,
                                                                                    post_id, post_url))
                    return
            else:
                question_id = post_id
            if post_type != "question":
                log("warning", "{}: tried to edit-watch non-question: hostname: "
                               "{} :: post ID:{} when subscribing to {}".format(self.__class__.__name__, hostname,
                                                                                question_id, post_url))
                return
        if not site_id or not hostname:
            with GlobalVars.site_id_dict_lock:
                if not site_id and hostname:
                    site_id = GlobalVars.site_id_dict.get(hostname)
                if site_id and not hostname:
                    hostname = GlobalVars.site_id_dict_by_id.get(site_id)
        if not site_id or not hostname:
            log("warning", "{}: unable to determine a valid site ID or hostname when subscribing to question ID "
                           "{}:: site_id:{}::  hostname:{}::  post_url:{}".format(self.__class__.__name__, question_id,
                                                                                  site_id, hostname, post_url))
            return

        question_ids = question_id
        if not isinstance(question_ids, list):
            question_ids = [question_id]
        now = time.time()
        if from_time:
            now = from_time
        if not max_time:
            max_time = now + timeout

        to_subscribe = []
        with self.posts_lock:
            for question_id in question_ids:
                action = "{}-question-{}".format(site_id, question_id)
                if action not in self.posts:
                    self.posts[action] = (site_id, hostname, question_id, max_time)
                    to_subscribe.append(action)
                else:
                    old_max_time = self.posts[action][2]
                    if max_time > old_max_time:
                        self.posts[action] = (site_id, hostname, question_id, max_time)

        for action in to_subscribe:
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
        if GlobalVars.no_edit_watcher:
            return
        with self.posts_lock:
            copy = self.posts.copy()

        datahandling.dump_pickle(PICKLE_FILENAME, copy)

    def _unsubscribe(self, action):
        if self.socket:
            try:
                self.socket.send("-" + action)
            except websocket.WebSocketException:
                log('error', '{}: failed to unsubscribe to {}'.format(self.__class__.__name__, action))
        else:
            log('warn', '{}: tried to unsubscribe to {}, but no WebSocket available.'.format(self.__class__.__name__,
                                                                                             action))
