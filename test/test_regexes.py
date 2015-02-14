from findspam import FindSpam
import pytest


@pytest.mark.parametrize("title, body, username, site, match", [
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', True),
    ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', '', '', True),
    ('', '', 'bagprada', '', True),
    ('HOW DO YOU SOLVE THIS PROBLEM?', '', '', '', True),
    ('12 Month Loans quick @ http://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', '', '', True),
    ('support for yahoo mail 18669786819 @call for helpline number', '', '', '', True),
    ('yahoo email tech support 1 866 978 6819 Yahoo Customer Phone Number ,Shortest Wait', '', '', '', True),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', '<p>bbbbbbbbbbbbbbbbbbbbbb</p>', '', 'stackoverflow.com', True),
    ('Non-spammy title', 'baba', '', 'stackoverflow.com', True),
    ('Gmail Tech Support (1-844-202-5571) Gmail tech support number[Toll Free Number]?', '', '', 'stackoverflow.com', True),
    ('<>1 - 866-978-6819<>gmail password reset//gmail contact number//gmail customer service//gmail help number', '', '', 'stackoverflow.com', True),
    ('Hotmail technical support1 - 844-780-67 62 telephone number Hotmail support helpline number', '', '', 'stackoverflow.com', True),
    ('[[[[[1-844-202-5571]]]]]Gmail Tech support[*]Gmail tech support number', '', '', 'stackoverflow.com', True),
    ('@@<>1 -866-978-6819 FREE<><><::::::@Gmail password recovery telephone number', '', '', 'stackoverflow.com', True),
    ('1 - 844-780-6762 outlook password recovery number-outlook password recovery contact number-outlook password recovery helpline number', '', '', 'stackoverflow.com', True),
    ('hotmail customer <*<*<*[*[ 1 - 844-780-6762 *** support toll free number Hotmail Phone Number hotmail account recovery phone number', '', '', 'stackoverflow.com', True),
    ('1 - 844-780-6762 outlook phone number-outlook telephone number-outlook customer care helpline number', '', '', 'stackoverflow.com', True),
    ('Repeating word word word word word word word word word', '', '', 'stackoverflow.com', True),
    ('Visit this website: optimalstackfacts', '', '', 'stackoverflow.com', True),
    ('This asdf should asdf not asdf be asdf matched asdf because asdf the asdf words do not asdf follow on each asdf other.', '', '', 'stackoverflow.com', False),
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
    ('This is a title.', 'This is a body.<pre>bbbbbbbbbbbbbb</pre>', '', 'stackoverflow.com', False),
    ('This is another title.', 'This is another body. <code>bbbbbbbbbbbb</code>', '', 'stackoverflow.com', False)
])
def test_regexes(title, body, username, site, match):
    # If we want to test answers separatly, this should be changed
    is_answer = False
    result = FindSpam.test_post(title, body, username, site, is_answer)
    print title
    print result
    isspam = False
    if len(result) > 0:
        isspam = True
    assert match == isspam
