# -*- coding: utf-8 -*-
# noinspection PyCompatibility

import requests


deepsmoke_url = 'http://99.239.154.69/dsd/index.php'


def check_deepsmoke(s, site, *args):
    """
    Query DeepSmoke for its verdict for this post.
    """
    req = requests.get(deepsmoke_url, params={'q': s[0:270]})
    # Raise requests.exceptions.HTTPError for any server error
    req.raise_for_status()
    assert req.text.startswith('<pre>')
    resp = req.text[5:]
    assert resp.endswith('\n</pre>\n')
    resp = resp[:-8]
    if resp == 'Spam':
       return True, 'DeepSmoke response was {}'.format(resp)
    # else
    return False, ''
