# coding=utf-8
import requests
import parsing
from globalvars import GlobalVars
import time
import html


class PostData:
    def __init__(self):
        self.post_id = None
        self.post_url = None
        self.post_type = None
        self.site = None
        self.owner_url = None
        self.owner_name = None
        self.owner_rep = None
        self.title = None
        self.body = None
        self.body_markdown = None
        self.score = None
        self.up_vote_count = None
        self.down_vote_count = None
        self.question_id = None
        self.creation_date = None
        self.last_edit_date = None

    @property
    def as_dict(self):
        # Basically, return this to the dict-style response that Post(api_data=DATA) expects, for proper parsing.
        dictdata = {
            'title': self.title,
            'body': self.body,
            'body_markdown': self.body_markdown,
            'owner': {'display_name': self.owner_name, 'link': self.owner_url, 'reputation': self.owner_rep},
            'site': self.site,
            'question_id': self.post_id,
            'link': self.post_url,
            'score': self.score,
            'up_vote_count': self.up_vote_count,
            'down_vote_count': self.down_vote_count,
            'edited': (self.creation_date != self.last_edit_date),
            'IsAnswer': getattr(self, 'IsAnswer', False),
        }

        return dictdata

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, item):
        getattr(self, item)


def api_get_post(post_url):
    GlobalVars.api_request_lock.acquire()

    # Respect backoff, if we were given one
    if GlobalVars.api_backoff_time > time.time():
        time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
    d = parsing.fetch_post_id_and_site_from_url(post_url)
    if d is None:
        GlobalVars.api_request_lock.release()
        return None
    post_id, site, post_type = d

    request_url = "https://api.stackexchange.com/2.2/{}s/{}".format(post_type, post_id)
    params = {
        'filter': GlobalVars.se_api_question_answer_post_filter,
        'key': 'IAkbitmze4B8KpacUfLqkw((',
        'site': site
    }
    response = requests.get(request_url, params=params).json()
    if "backoff" in response:
        if GlobalVars.api_backoff_time < time.time() + response["backoff"]:
            GlobalVars.api_backoff_time = time.time() + response["backoff"]
    if 'items' not in response or len(response['items']) == 0:
        GlobalVars.api_request_lock.release()
        return False
    GlobalVars.api_request_lock.release()

    item = response['items'][0]
    post_data = PostData()
    post_data.post_id = post_id
    post_data.post_url = parsing.url_to_shortlink(item['link'])
    post_data.post_type = post_type
    post_data.title = html.unescape(item['title'])
    if 'owner' in item and 'link' in item['owner']:
        post_data.owner_name = html.unescape(item['owner']['display_name'])
        post_data.owner_url = item['owner']['link']
        post_data.owner_rep = item['owner']['reputation']
    else:
        post_data.owner_name = ""
        post_data.owner_url = ""
        post_data.owner_rep = 1
    post_data.site = site
    post_data.body = item['body']
    post_data.body_markdown = item['body_markdown']
    post_data.score = item['score']
    post_data.up_vote_count = item['up_vote_count']
    post_data.down_vote_count = item['down_vote_count']
    post_data.creation_date = item['creation_date']
    try:
        post_data.last_edit_date = item['last_edit_date']
    except KeyError:
        post_data.last_edit_date = post_data.creation_date  # Key not present = not edited
    if post_type == "answer":
        post_data.question_id = item['question_id']
    return post_data
