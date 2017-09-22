# -*- coding: utf-8 -*-
# noinspection PyCompatibility

import requests
from datetime import datetime


deepsmoke_url = 'http://localhost:8080/spam'


def check_deepsmoke(s, site, *args):
    """
    Query DeepSmoke for its verdict for this post.
    """
    starttime = datetime.now()
    req = requests.get(deepsmoke_url, params={'body': s[0:270]})
    # Raise requests.exceptions.HTTPError for any server error
    req.raise_for_status()
    try:
        result = req.json()
        resp = result['spam']
    except KeyError as err:
        return False, 'error {0!r}'.format(err)
    endtime = datetime.now()
    details = 'DeepSmoke response was {0} (duration: {1})'.format(
        resp, endtime - starttime)
    return (resp == 'Spam'), details
