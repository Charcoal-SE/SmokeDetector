# coding=utf-8
from spamhandling import check_if_spam, check_if_spam_json
from datahandling import add_blacklisted_user, add_whitelisted_user, _remove_pickle
from blacklists import load_blacklists
from parsing import get_user_from_url
import pytest
import os
import json
from classes import Post


load_blacklists()
test_data_inputs = []
with open("test/data_test_spamhandling.txt", "r", encoding="utf-8") as f:
    # noinspection PyRedeclaration
    test_data_inputs = f.readlines()


# noinspection PyMissingTypeHints
@pytest.mark.parametrize("title, body, username, site, match", [
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', True),
    ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', '', '', True),
    ('', '', 'bagprada', '', True),
    ('12 Month Loans quick @ http://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', '', '', True),
    ('support for yahoo mail 18669786819 @call for helpline number', '', '', '', True),
    ('yahoo email tech support 1 866 978 6819 Yahoo Customer Phone Number ,Shortest Wait', '', '', '', True),
    ('Not a phone number 192.168.0.1', 'Not a phone number 192.168.0.1', '', '', False),
    ('What is the value of MD5 checksums if the MD5 hash itself could potentially also have been manipulated?', '', '', '', False),
    ('Probability: 6 Dice are rolled. Which is more likely, that you get exactly one 6, or that you get 6 different numbers?', '', '', '', False),
    ('The Challenge of Controlling a Powerful AI', '', 'Serban Tanasa', '', False),
    ('Reproducing image of a spiral using TikZ', '', 'Kristoffer Ryhl', '', False),
    ('What is the proper way to say "queryer"', '', 'jedwards', '', False),
    ('What\'s a real-world example of "overfitting"?', '', 'user3851283', '', False),
    ('How to avoid objects when traveling at greater than .75 light speed. or How Not to Go SPLAT?', '', 'bowlturner', '', False),
    ('Is it unfair to regrade prior work after detecting cheating?', '', 'Village', '', False),
    ('Inner workings of muscles', '', '', 'fitness.stackexchange.com', False),
    ('Cannot access http://stackoverflow.com/ with proxy enabled', '', '', 'superuser.com', False),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', '<p>bbbbbbbbbbbbbbbbbbbbbb</p>', '', 'stackoverflow.com', True),
    ('This this this this this this this this', '<p>This this this this this this this this</p>', '', 'math.stackexchange.com', True),
    ('Raw link at end', """<p>This this this this this this this this <a href="http://example.net/harmless/">http://example.org/pesky-reviews-and-scam</a></p>""", '', 'drupal.stackexchange.com', True),
    ('Enhance SD Male Enhancement Supplements', '', '', '', True),
    ('Test case for bad pattern in URL',
     '<p><a href="http://example.com/bad-reviews-canada/" rel="nofollow noreferrer">Cliquez ici</a></p>', '', '', True),
    ('Another test case for bad URL pattern',
     '<p><a href="http://example.net/harmless/">http://example.org/pesky-reviews-and-scam</a></p>', '', '', True),
    ('FP test for bad URL pattern',
     '''<p>Don't trigger on link to <a href="https://askubuntu.com/questions-about-reviews">this StackExchange member site</a></p>''', '', '', False),
    ('FP test for bad URL pattern',
     '''<p>Don't trigger on link to <a href="https://mathoverflow.net/questions-about-reviews">this StackExchange member site</a></p>''', '', '', False),
    ('Mostly Non-latin', '冰冰冰test冰冰冰冰冰冰冰冰冰冰冰冰 test 冰冰冰冰', '', '', True),
    ('Pattern Matching product name - 2 words', """<p>vxl male enhancement</p>""", '', '', True),
    ('Pattern Matching product name - 3 words', """<p>Extends Monster Male Enhancement And Male Penile Enhancement</p>""", '', '', True),
    ('A Title', """<p>E x t e n d s  M o n s t e r Male E n h a n c e m e n t And M a l e P e n i l e E n h a n c e m e n t</p>""", '', 'judaism.stackexchange.com', True),
])
def test_check_if_spam(title, body, username, site, match):
    # We can't check blacklists/whitelists in tests, so these are set to their default values

    post_dict = {
        "titleEncodedFancy": str(title),
        "bodySummary": str(body),
        "ownerDisplayName": str(username),
        "url": "TEST: No URL passed!",
        "id": "TEST: No ID passed!",
        "siteBaseHostAddress": str(site),
        "ownerUrl": "TEST: No Owner ID passed!"
    }
    json_dict = {
        "action": "155-questions-active",
        'data': json.dumps(post_dict),
        'IsAnswer': False  # If we want to test answers separately, this should be changed.
    }
    json_data = json.dumps(json_dict)
    post = Post(json_data=json_data)
    is_spam, reason, _ = check_if_spam(post)
    assert match == is_spam


# noinspection PyMissingTypeHints
@pytest.mark.parametrize("data, match", [
    (test_data_inputs[0], False)
])
def test_check_if_spam_json(data, match):
    is_spam, reason, _ = check_if_spam_json(data)
    assert match == is_spam

    # Check that a malformed post isn't reported as spam
    is_spam, reason, _ = check_if_spam_json(None)
    assert not is_spam


@pytest.mark.skipif(os.path.isfile("blacklistedUsers.p"),
                    reason="shouldn't overwrite file")
def test_blacklisted_user():
    user_url = 'http://stackoverflow.com/users/1/jeff-atwood'
    user = get_user_from_url(user_url)
    add_blacklisted_user(user, "", "")
    # Construct a "fake" post object in API-format
    post = Post(api_response={'title': '', 'body': '',
                              'owner': {'display_name': user, 'reputation': 1, 'link': user_url},
                              'site': 'stackoverflow.com', 'question_id': '1', 'IsAnswer': False, 'score': 0})
    is_spam, reason, _ = check_if_spam(post)
    assert is_spam is True
    # cleanup
    _remove_pickle("blacklistedUsers.p")


# noinspection PyMissingTypeHints
@pytest.mark.skipif(os.path.isfile("whitelistedUsers.p"),
                    reason="shouldn't overwrite file")
def test_whitelisted_user():
    user_url = 'http://stackoverflow.com/users/2/geoff-dalgas'
    user = get_user_from_url(user_url)
    add_whitelisted_user(user)
    user_url2 = 'http://stackoverflow.com/users/0/test'
    user2 = get_user_from_url(user_url2)
    add_whitelisted_user(user2)
    post = Post(api_response={'title': '', 'body': '',
                              'owner': {'display_name': 'bagprada', 'reputation': 1, 'link': user_url},
                              'site': 'stackoverflow.com', 'question_id': '1', 'IsAnswer': False, 'score': 0})
    is_spam, reason, _ = check_if_spam(post)
    assert is_spam is False
    post = Post(api_response={'title': 'baba ji', 'body': '',
                              'owner': {'display_name': '', 'reputation': 1, 'link': user_url},
                              'site': 'stackoverflow.com', 'question_id': '2', 'IsAnswer': False, 'score': 0})
    is_spam, reason, _ = check_if_spam(post)
    assert is_spam is True
    post = Post(api_response={'title': 'baba ji', 'body': '',
                              'owner': {'display_name': 'bagprada', 'reputation': 1, 'link': user_url},
                              'site': 'stackoverflow.com', 'question_id': '3', 'IsAnswer': False, 'score': 0})
    is_spam, reason, _ = check_if_spam(post)
    assert is_spam is True
    post = Post(api_response={'title': 'test', 'body': '',
                              'owner': {'display_name': 'baba ji - muscle building',
                                        'reputation': 1, 'link': user_url2},
                              'site': 'stackoverflow.com', 'question_id': '0', 'IsAnswer': False, 'score': 0})
    is_spam, reason, _ = check_if_spam(post)
    assert is_spam is False
    # cleanup
    _remove_pickle("whitelistedUsers.p")
