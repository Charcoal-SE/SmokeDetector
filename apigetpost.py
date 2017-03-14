import requests
import parsing
from globalvars import GlobalVars
import time
import HTMLParser


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
        self.score = None
        self.up_vote_count = None
        self.down_vote_count = None
        self.question_id = None
        self.is_answer = None

    def __dict__(self):
        # Basically, return this to the dict-style response that Post(api_data=DATA) expects, for proper parsing.
        return {
            'title': self.title,
            'body': self.body,
            'owner': {'display_name': self.owner_name, 'link': self.owner_url, 'reputation': self.owner_rep},
            'site': self.site,
            'question_id': self.post_id,
            'IsAnswer': self.is_answer,
            'link': self.post_url,
            'score': self.score,
            'up_vote_count': self.up_vote_count,
            'down_vote_count': self.down_vote_count,
        }


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
    if post_type == "answer":
        api_filter = "!FdmhxNQy0ZXsmxUOvWMVSbuktT"
    else:
        assert post_type == "question"
        api_filter = "!)Ehu.SHRfXhu2eCP4p6wd*Wxyw1XouU5qO83b7X5GQK6ciVat"

    request_url = "http://api.stackexchange.com/2.2/{type}s/{post_id}?site={site}&filter={api_filter}&" \
                  "key=IAkbitmze4B8KpacUfLqkw((".format(type=post_type, post_id=post_id, site=site,
                                                        api_filter=api_filter)
    response = requests.get(request_url).json()
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
    h = HTMLParser.HTMLParser()
    post_data.title = h.unescape(item['title'])
    if 'owner' in item and 'link' in item['owner']:
        post_data.owner_name = h.unescape(item['owner']['display_name'])
        post_data.owner_url = item['owner']['link']
        post_data.owner_rep = item['owner']['reputation']
    else:
        post_data.owner_name = ""
        post_data.owner_url = ""
        post_data.owner_rep = 1
    post_data.site = site
    post_data.body = item['body']
    post_data.score = item['score']
    post_data.up_vote_count = item['up_vote_count']
    post_data.down_vote_count = item['down_vote_count']
    if post_type == "answer":
        post_data.question_id = item['question_id']
    return post_data
