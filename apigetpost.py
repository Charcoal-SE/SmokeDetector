import requests
from parsing import fetch_post_id_and_site_from_url, url_to_shortlink
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


def api_get_post(post_url):
    # Respect backoff, if we were given one
    if GlobalVars.api_backoff_time > time.time():
        time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
    d = fetch_post_id_and_site_from_url(post_url)
    if d is None:
        return None
    post_id, site, post_type = d
    if post_type == "answer":
        api_filter = "!FdmhxNQy0ZXsmxUOvWMVSbuktT"
    else:
        assert post_type == "question"
        api_filter = "!)Ehu.SHRfXhu2eCP4p6wd*Wxyw1XouU5qO83b7X5GQK6ciVat"

    request_url = "http://api.stackexchange.com/2.2/{type}s/{post_id}?site={site}&filter={api_filter}&key=IAkbitmze4B8KpacUfLqkw((".format(type=post_type, post_id=post_id, site=site, api_filter=api_filter)
    response = requests.get(request_url).json()
    if "backoff" in response:
        if GlobalVars.api_backoff_time < time.time() + response["backoff"]:
            GlobalVars.api_backoff_time = time.time() + response["backoff"]
    if 'items' not in response or len(response['items']) == 0:
        return False
    item = response['items'][0]
    post_data = PostData()
    post_data.post_id = post_id
    post_data.post_url = url_to_shortlink(item['link'])
    post_data.post_type = post_type
    h = HTMLParser.HTMLParser()
    post_data.title = h.unescape(item['title'])
    if 'owner' in item and item['owner'] is not None:
        post_data.owner_name = h.unescape(item['owner']['display_name'])
        post_data.owner_url = item['owner']['link']
        post_data.owner_rep = item['owner']['reputation']
    post_data.site = site
    post_data.body = item['body']
    post_data.score = item['score']
    post_data.up_vote_count = item['up_vote_count']
    post_data.down_vote_count = item['down_vote_count']
    if post_type == "answer":
        post_data.question_id = item['question_id']
    return post_data
