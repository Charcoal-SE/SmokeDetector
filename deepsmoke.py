# -*- coding: utf-8 -*-
# noinspection PyCompatibility

import logging

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
        logging.warn('Force False result from Deepsmoke, error {0!r}'.format(
            err))
        return False, {'error': err}
    endtime = datetime.now()
    result['duration'] = str(endtime - starttime)
    logging.debug('Deepsmoke result {0} ({1})'.format(resp, result))
    return resp, result
