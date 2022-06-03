# coding=utf-8
from spamhandling import check_if_spam, check_if_spam_json, handle_spam
from datahandling import add_blacklisted_user, add_whitelisted_user, remove_pickle
from blacklists import load_blacklists
from parsing import get_user_from_url
import pytest
import os
import json
from classes import Post
from unittest import TestCase
from unittest.mock import MagicMock, call, ANY, DEFAULT
import chatcommunicate
from globalvars import GlobalVars


load_blacklists()
test_data_inputs = []
with GlobalVars.local_git_repository_file_lock:
    with open("test/data_test_spamhandling.txt", "r", encoding="utf-8") as f:
        # noinspection PyRedeclaration
        test_data_inputs = f.readlines()


class Matcher:
    def __init__(self, containing, without):
        self.containing = containing
        self.without = without

    def __eq__(self, other):
        return self.containing in other and self.without not in other


def print_mock_args(*args, **kwargs):
    print('\nMock called with:\n\targs:', args)
    print('\tkwargs:', kwargs)
    return DEFAULT


class TestRoomReports(TestCase):

    auto_post_id = 1732454

    @classmethod
    def mock_post(cls,
                  title='',
                  body='',
                  site='stackoverflow.com',
                  link='https://stackoverflow.com/q/1732454',
                  owner={'link': 'https://stackoverflow.com/users/102937/robert-harvey'},
                  post_id=1732454,
                  is_question=True,
                  increment_auto_post_id=True):
        if increment_auto_post_id:
            cls.auto_post_id += 1
            link = 'https://stackoverflow.com/{}/{}'.format('q' if is_question else 'a', cls.auto_post_id)
            post_id = cls.auto_post_id
        api_response = {
            "title": title,
            "body": body,
            "site": site,
            "link": link,
            "owner": owner
        }
        if is_question:
            api_response['question_id'] = post_id
        else:
            api_response['answer_id'] = post_id
        return Post(api_response=api_response)

    @classmethod
    def setUpClass(cls):
        # Remember the originals of the methods we are going to mock
        cls.orig_deletion_watcher = GlobalVars.deletion_watcher
        cls.orig_tell_rooms = chatcommunicate.tell_rooms
        GlobalVars.deletion_watcher = MagicMock(spec=GlobalVars.deletion_watcher, wraps=None)  # Mock the deletion watcher in test
        chatcommunicate.tell_rooms = MagicMock(spec=cls.orig_tell_rooms, wraps=None, side_effect=print_mock_args)  # Mock the tell_rooms, so we can test how it was called

    @classmethod
    def tearDownClass(cls):
        # Clean up from mocking
        GlobalVars.deletion_watcher = cls.orig_deletion_watcher
        chatcommunicate.tell_rooms = cls.orig_tell_rooms

    def setUp(self):
        print('\n\n-------------------------------Set up test------------------------------------')
        chatcommunicate.tell_rooms.reset_mock
        # .reset_mock counts as a call. We don't want that.
        chatcommunicate.tell_rooms.call_count = 0

    @classmethod
    def test_handle_spam_repeating_characters(cls):
        post = cls.mock_post(title='aaaaaaaaaaaaaa')
        is_spam, reasons, why = check_if_spam(post)
        handle_spam(post=post, reasons=reasons, why=why)
        chatcommunicate.tell_rooms.assert_called_once_with(
            Matcher(containing='aaaaaaaaaaaaaa', without='Potentially offensive title'),
            ANY,
            ANY,
            notify_site=ANY,
            report_data=ANY
        )

    @classmethod
    def test_handle_spam_offensive_title(cls):
        post = cls.mock_post(title='fuck')
        is_spam, reasons, why = check_if_spam(post)
        handle_spam(post=post, reasons=reasons, why=why)
        call_a = call(
            Matcher(containing='fuck', without='potentially offensive title'),
            ANY,
            Matcher(containing='offensive-mask', without='no-offensive-mask'),
            notify_site=ANY,
            report_data=ANY
        )
        call_b = call(
            Matcher(containing='potentially offensive title', without='fuck'),
            ANY,
            Matcher(containing='no-offensive-mask', without='offensive-mask'),
            notify_site=ANY,
            report_data=ANY
        )
        chatcommunicate.tell_rooms.assert_has_calls([call_a, call_b])


# noinspection PyMissingTypeHints
@pytest.mark.parametrize("title, body, username, site, match", [
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', True),
    ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', '', '', True),
    ('', '', 'bagprada', '', True),
    ('12 Month Loans quick @ https://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', '', '', True),
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
    ('Cannot access https://stackoverflow.com/ with proxy enabled', '', '', 'superuser.com', False),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', '<p>bbbbbbbbbbbbbbbbbbbbbb</p>', '', 'stackoverflow.com', True),
    ('This this this this this this this this', '<p>This this this this this this this this</p>', '', 'math.stackexchange.com', True),
    ('Raw link at end', """<p>This this this this this this this this <a href="https://example.net/harmless/">https://example.org/pesky-reviews-and-scam</a></p>""", '', 'drupal.stackexchange.com', True),
    ('Enhance SD Male Enhancement Supplements', '', '', '', True),
    ('Test case for bad pattern in URL',
     '<p><a href="https://example.com/bad-reviews-canada/" rel="nofollow noreferrer">Cliquez ici</a></p>', '', '', True),
    ('Another test case for bad URL pattern',
     '<p><a href="https://example.net/harmless/">https://example.org/pesky-reviews-and-scam</a></p>', '', '', True),
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
    user_url = 'https://stackoverflow.com/users/1/jeff-atwood'
    user = get_user_from_url(user_url)
    add_blacklisted_user(user, "", "")
    # Construct a "fake" post object in API-format
    post = Post(api_response={'title': '', 'body': '',
                              'owner': {'display_name': user, 'reputation': 1, 'link': user_url},
                              'site': 'stackoverflow.com', 'question_id': '1', 'IsAnswer': False, 'score': 0})
    is_spam, reason, _ = check_if_spam(post)
    assert is_spam is True
    # cleanup
    remove_pickle("blacklistedUsers.p")


# noinspection PyMissingTypeHints
@pytest.mark.skipif(os.path.isfile("whitelistedUsers.p"),
                    reason="shouldn't overwrite file")
def test_whitelisted_user():
    user_url = 'https://stackoverflow.com/users/2/geoff-dalgas'
    user = get_user_from_url(user_url)
    add_whitelisted_user(user)
    user_url2 = 'https://stackoverflow.com/users/0/test'
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
    remove_pickle("whitelistedUsers.p")
