# -*- coding: utf-8 -*-
from findspam import FindSpam
import pytest


@pytest.mark.parametrize("title, body, username, site, body_is_summary, is_answer, match", [
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', False, False, True),
    ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', '', '', True, False, True),
    ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', '', '', False, False, True),
    ('', '', 'bagprada', '', False, False, True),
    ('12 Month Loans quick @ http://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', '', '', False, False, True),
    ('support for yahoo mail 18669786819 @call for helpline number', '', '', '', False, False, True),
    ('yahoo email tech support 1 866 978 6819 Yahoo Customer Phone Number ,Shortest Wait', '', '', '', False, False, True),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', '<p>bbbbbbbbbbbbbbbbbbbbbb</p>', '', 'stackoverflow.com', False, False, True),
    ('Yay titles!', 'bbbbbbbbbbbabcdefghijklmnop', '', 'stackoverflow.com', False, False, True),
    ('kkkkkkkkkkkkkkkkkkkkkkkkkkkk', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbb', '', 'stackoverflow.com', True, False, True),
    ('99999999999', '', '', 'stackoverflow.com', False, False, True),
    ('Spam spam spam', '', 'babylisscurl', 'stackoverflow.com', False, False, True),
    ('Question', '111111111111111111111111111111111111', '', 'stackoverflow.com', False, False, True),
    ('Question', 'I have this number: 111111111111111', '', 'stackoverflow.com', False, False, False),
    ('Random title', '$$$$$$$$$$$$', '', 'superuser.com', False, False, True),
    ('Enhance SD Male Enhancement Supplements', '', '', '', False, False, True),
    ('Title here', '111111111111111111111111111111111111', '', 'communitybuilding.stackexchange.com', False, False, True),
    ('Gmail Tech Support (1-844-202-5571) Gmail tech support number[Toll Free Number]?', '', '', 'stackoverflow.com', False, False, True),
    ('<>1 - 866-978-6819<>gmail password reset//gmail contact number//gmail customer service//gmail help number', '', '', 'stackoverflow.com', False, False, True),
    ('Hotmail technical support1 - 844-780-67 62 telephone number Hotmail support helpline number', '', '', 'stackoverflow.com', False, False, True),
    ('Valid title', 'Hotmail technical support1 - 844-780-67 62 telephone number Hotmail support helpline number', '', 'stackoverflow.com', True, False, True),
    ('[[[[[1-844-202-5571]]]]]Gmail Tech support[*]Gmail tech support number', '', '', 'stackoverflow.com', False, False, True),
    ('@@<>1 -866-978-6819 FREE<><><::::::@Gmail password recovery telephone number', '', '', 'stackoverflow.com', False, False, True),
    ('1 - 844-780-6762 outlook password recovery number-outlook password recovery contact number-outlook password recovery helpline number', '', '', 'stackoverflow.com', False, False, True),
    ('hotmail customer <*<*<*[*[ 1 - 844-780-6762 *** support toll free number Hotmail Phone Number hotmail account recovery phone number', '', '', 'stackoverflow.com', False, False, True),
    ('1 - 844-780-6762 outlook phone number-outlook telephone number-outlook customer care helpline number', '', '', 'stackoverflow.com', False, False, True),
    ('Repeating word word word word word word word word word', '', '', 'stackoverflow.com', False, False, True),
    ('Visit this website: optimalstackfacts.net', '', '', 'stackoverflow.com', False, False, True),
    ('his email address is (SOMEONE@GMAIL.COM)', '', '', 'money.stackexchange.com', False, False, True),
    ('something', 'his email address is (SOMEONE@GMAIL.COM)', '', 'money.stackexchange.com', False, False, True),
    ('asdf asdf asdf asdf asdf asdf asdf asdf', '', '', 'stackoverflow.com', True, False, True),
    ('A title', '>>>>  http://', '', 'stackoverflow.com', False, False, True),
    ('', '<p>Test <a href="http://example.com/" rel="nofollow">some text</a> moo moo moo.</p><p>Another paragraph. Make it long enough to bring this comfortably over the 300-character limit. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p><p><a href="http://example.com/" rel="nofollow">http://example.com/</a></p>', '', 'stackoverflow.com', False, False, True),
    ('spam', '>>>> http://', '', 'stackoverflow.com', True, False, False),
    ('Another title', '<code>>>>>http://</code>', '', 'stackoverflow.com', False, False, False),
    ('This asdf should asdf not asdf be asdf matched asdf because asdf the asdf words do not asdf follow on each asdf other.', '', '', 'stackoverflow.com', False, False, False),
    ('What is the value of MD5 checksums if the MD5 hash itself could potentially also have been manipulated?', '', '', '', False, False, False),
    ('Probability: 6 Dice are rolled. Which is more likely, that you get exactly one 6, or that you get 6 different numbers?', '', '', '', False, False, False),
    ('The Challenge of Controlling a Powerful AI', '', 'Serban Tanasa', '', False, False, False),
    ('Reproducing image of a spiral using TikZ', '', 'Kristoffer Ryhl', '', False, False, False),
    ('What is the proper way to say "queryer"', '', 'jedwards', '', False, False, False),
    ('What\'s a real-world example of "overfitting"?', '', 'user3851283', '', False, False, False),
    ('How to avoid objects when traveling at greater than .75 light speed. or How Not to Go SPLAT?', '', 'bowlturner', '', False, False, False),
    ('Is it unfair to regrade prior work after detecting cheating?', '', 'Village', '', False, False, False),
    ('Inner workings of muscles', '', '', 'fitness.stackexchange.com', False, False, False),
    ('Cannot access http://stackoverflow.com/ with proxy enabled', '', '', 'superuser.com', False, False, False),
    ('This is a title.', 'This is a body.<pre>bbbbbbbbbbbbbb</pre>', '', 'stackoverflow.com', False, False, False),
    ('This is another title.', 'This is another body. <code>bbbbbbbbbbbb</code>', '', 'stackoverflow.com', False, False, False),
    ('Yet another title.', 'many whitespace             .', '', 'stackoverflow.com', False, False, False),
    ('Perfectly valid title.', 'bbbbbbbbbbbbbbbbbbbbbb', '', 'stackoverflow.com', True, False, False),
    ('Yay titles!', 'bbbbbbbbbbbabcdefghijklmnopqrstuvwxyz123456789a1b2c3d4e5', '', 'stackoverflow.com', False, False, False),
    ('Long double', 'I have this value: 9999999999999999', '', 'stackoverflow.com', False, False, False),
    ('Another valid title.', 'asdf asdf asdf asdf asdf asdf asdf asdf asdf', '', 'stackoverflow.com', True, False, False),
    ('Array question', 'I have an array with these values: 10 10 10 10 10 10 10 10 10 10 10 10', '', 'stackoverflow.com', False, False, False),
    ('Array question', 'I have an array with these values: 0 0 0 0 0 0 0 0 0 0 0 0', '', 'stackoverflow.com', False, False, False),
    ('his email address is (SOMEONE@GMAIL.COM)', '', '', 'stackoverflow.com', False, False, False),
    ('something', 'his email address is (SOMEONE@GMAIL.COM)', '', 'stackoverflow.com', False, False, False),
    ('something', 'URL: &email=someone@gmail.com', '', 'meta.stackexchange.com', False, False, False),
    ('random title', 'URL: page.html#someone@gmail.com', '', 'rpg.stackexchange.com', False, False, False),
    (u'Как рандомно получать числа 1 и 2?', u'Текст вопроса с кодом <code>a = b + 1</code>', u'Сашка', 'ru.stackoverflow.com', False, False, False),
    ('Should not be caught: http://example.com', '', '', 'drupal.stackexchange.com', False, False, False),
    ('Should not be caught: https://www.example.com', '', '', 'drupal.stackexchange.com', False, False, False),
    ('Should not be caught: something@example.com', '', '', 'drupal.stackexchange.com', False, False, False),
    ('Title here', '<img src="http://example.com/11111111111.jpg" alt="my image">', '', 'stackoverflow.com', False, False, False),
    ('Title here', '<img src="http://example.com/11111111111111.jpg" alt="my image" />', '', 'stackoverflow.com', False, False, False),
    ('Title here', '<a href="http://example.com/11111111111111.html">page</a>', '', 'stackoverflow.com', False, False, False),
    ('Error: 2147467259', '', '', 'stackoverflow.com', False, False, False),
    ('Max limit on number of concurrent ajax request', """<p>Php java script boring yaaarrr <a href="http://www.price-buy.com/" rel="nofollow noreferrer">Price-Buy.com</a> </p>""", 'Price Buy', 'stackoverflow.com', True, True, True),
    ('Proof of onward travel in Japan?', """<p>The best solution to overcome the problem of your travel<a href="https://i.stack.imgur.com/eS6WQ.jpg" rel="nofollow noreferrer"><img src="https://i.stack.imgur.com/eS6WQ.jpg" alt="enter image description here"></a></p>

<p>httl://bestonwardticket.com</p>""", 'Best onward Ticket', 'travel.stackexchange.com', True, True, True),
    ('Max limit on number of concurrent ajax request', """<p>Php java script boring yaaarrr <a href="http://www.price-buy.com/" rel="nofollow noreferrer">Price-Buy.com</a> </p>""", 'Totally Unrelated Username', 'stackoverflow.com', True, True, False),
])
def test_regexes(title, body, username, site, body_is_summary, is_answer, match):
    # If we want to test answers separately, this should be changed
    # is_answer = False
    result = FindSpam.test_post(title, body, username, site, is_answer, body_is_summary, 1, 0)[0]
    print title
    print "Result:", result
    isspam = False
    if len(result) > 0:
        isspam = True
    assert match == isspam
