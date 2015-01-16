from spamhandling import *
import pytest

@pytest.mark.parametrize("title, body, username, site, match", [
     ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', True),
     ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', '', '', True),
     ('', '', 'bagprada', '', True),
     ('HOW DO YOU SOLVE THIS PROBLEM?', '', '', '', True),
     ('12 Month Loans quick @ http://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', '', '', True),
     ('support for yahoo mail 18669786819 @call for helpline number', '', '', '', True),
     ('yahoo email tech support 1 866 978 6819 Yahoo Customer Phone Number ,Shortest Wait', '', '', '', True),
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
     ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', '<p>bbbbbbbbbbbbbbbbbbbbbb</p>', '', 'stackoverflow.com', True)
])

def test_check_if_spam(title, body, username, site, match):
    # We can't check blacklists/whitelists in tests, so these are set to their default values
    user_url = ""
    post_id = 0
    # If we want to test answers separatly, this should be changed
    is_answer = False
    is_spam = check_if_spam(title, body, username, user_url, site, post_id, is_answer)
    print title
    assert match == is_spam
