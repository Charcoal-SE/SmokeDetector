# coding=utf-8
import time

import requests
import parsing
from globalvars import GlobalVars
from helpers import get_se_api_default_params_questions_answers_posts_add_site, get_se_api_url_for_route
from models.se_api import StackExchangePostResponse, StackExchangePostItem


def api_get_post(post_url):
    with GlobalVars.api_request_lock:
        # Respect backoff, if we were given one
        if GlobalVars.api_backoff_time > time.time():
            time.sleep(GlobalVars.api_backoff_time - time.time() + 2)
        d = parsing.fetch_post_id_and_site_from_url(post_url)
        if d is None:
            return None
        post_id, site, post_type = d

        request_url = get_se_api_url_for_route("{}s/{}".format(post_type, post_id))
        params = get_se_api_default_params_questions_answers_posts_add_site(site)
        response_json = requests.get(request_url, params=params,
                                     timeout=GlobalVars.default_requests_timeout).json()
        api_response = StackExchangePostResponse.from_dict(response_json)
        if api_response.backoff:
            if GlobalVars.api_backoff_time < time.time() + api_response.backoff:
                GlobalVars.api_backoff_time = time.time() + api_response.backoff
        if not api_response.items:
            return False

    # 直接返回首个帖子模型实例，供下游按属性访问
    return api_response.items[0]
