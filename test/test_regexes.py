from findspam import FindSpam
import pytest


@pytest.mark.parametrize("title, body, username, site,  body_is_summary, match", [
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', False, True),
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', True, True),
    ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', '', '', False, True),
    ('', '', 'bagprada', '', False, True),
    ('HOW DO YOU SOLVE THIS PROBLEM?', '', '', '', False, True),
    ('12 Month Loans quick @ http://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', '', '', False, True),
    ('support for yahoo mail 18669786819 @call for helpline number', '', '', '', False, True),
    ('yahoo email tech support 1 866 978 6819 Yahoo Customer Phone Number ,Shortest Wait', '', '', '', False, True),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', '<p>bbbbbbbbbbbbbbbbbbbbbb</p>', '', 'stackoverflow.com', False, True),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbb', '', 'stackoverflow.com', True, True),
    ('99999999999', '', '', 'stackoverflow.com', False, True),
    ('Random title', '$$$$$$$$$$$$', '', 'superuser.com', False, True),
    ('Non-spammy title', 'baba', '', 'stackoverflow.com', False, True),
    ('Gmail Tech Support (1-844-202-5571) Gmail tech support number[Toll Free Number]?', '', '', 'stackoverflow.com', False, True),
    ('<>1 - 866-978-6819<>gmail password reset//gmail contact number//gmail customer service//gmail help number', '', '', 'stackoverflow.com', False, True),
    ('Hotmail technical support1 - 844-780-67 62 telephone number Hotmail support helpline number', '', '', 'stackoverflow.com', False, True),
    ('Valid title', 'Hotmail technical support1 - 844-780-67 62 telephone number Hotmail support helpline number', '', 'stackoverflow.com', True, True),
    ('[[[[[1-844-202-5571]]]]]Gmail Tech support[*]Gmail tech support number', '', '', 'stackoverflow.com', False, True),
    ('@@<>1 -866-978-6819 FREE<><><::::::@Gmail password recovery telephone number', '', '', 'stackoverflow.com', False, True),
    ('1 - 844-780-6762 outlook password recovery number-outlook password recovery contact number-outlook password recovery helpline number', '', '', 'stackoverflow.com', False, True),
    ('hotmail customer <*<*<*[*[ 1 - 844-780-6762 *** support toll free number Hotmail Phone Number hotmail account recovery phone number', '', '', 'stackoverflow.com', False, True),
    ('1 - 844-780-6762 outlook phone number-outlook telephone number-outlook customer care helpline number', '', '', 'stackoverflow.com', False, True),
    ('Repeating word word word word word word word word word', '', '', 'stackoverflow.com', False, True),
    ('Visit this website: optimalstackfacts', '', '', 'stackoverflow.com', False, True),
    ('asdf asdf asdf asdf asdf asdf asdf asdf', '', '', 'stackoverflow.com', True, True),
    ('A title', '>>>>  http://', '', 'stackoverflow.com', False, True),
    ('spam', '>>>> http://', '', 'stackoverflow.com', True, False),
    ('Another title', '<code>>>>>http://</code>', '', 'stackoverflow.com', False, False),
    ('This asdf should asdf not asdf be asdf matched asdf because asdf the asdf words do not asdf follow on each asdf other.', '', '', 'stackoverflow.com', False, False),
    ('What is the value of MD5 checksums if the MD5 hash itself could potentially also have been manipulated?', '', '', '', False, False),
    ('Probability: 6 Dice are rolled. Which is more likely, that you get exactly one 6, or that you get 6 different numbers?', '', '', '', False, False),
    ('The Challenge of Controlling a Powerful AI', '', 'Serban Tanasa', '', False, False),
    ('Reproducing image of a spiral using TikZ', '', 'Kristoffer Ryhl', '', False, False),
    ('What is the proper way to say "queryer"', '', 'jedwards', '', False, False),
    ('What\'s a real-world example of "overfitting"?', '', 'user3851283', '', False, False),
    ('How to avoid objects when traveling at greater than .75 light speed. or How Not to Go SPLAT?', '', 'bowlturner', '', False, False),
    ('Is it unfair to regrade prior work after detecting cheating?', '', 'Village', '', False, False),
    ('Inner workings of muscles', '', '', 'fitness.stackexchange.com', False, False),
    ('Cannot access http://stackoverflow.com/ with proxy enabled', '', '', 'superuser.com', False, False),
    ('This is a title.', 'This is a body.<pre>bbbbbbbbbbbbbb</pre>', '', 'stackoverflow.com', False, False),
    ('This is another title.', 'This is another body. <code>bbbbbbbbbbbb</code>', '', 'stackoverflow.com', False, False),
    ('Yet another title.', 'many whitespace             .', '', 'stackoverflow.com', False, False),
    ('Perfectly valid title.', 'bbbbbbbbbbbbbbbbbbbbbb', '', 'stackoverflow.com', True, False),
    ('Another valid title.', 'asdf asdf asdf asdf asdf asdf asdf asdf asdf', '', 'stackoverflow.com', True, False)
])
def test_regexes(title, body, username, site, body_is_summary, match):
    # If we want to test answers separatly, this should be changed
    is_answer = False
    result = FindSpam.test_post(title, body, username, site, is_answer, body_is_summary)
    print title
    print result
    isspam = False
    if len(result) > 0:
        isspam = True
    assert match == isspam
