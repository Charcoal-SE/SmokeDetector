# -*- coding: utf-8 -*-
from findspam import FindSpam, ip_for_url_host, get_ns_ips
import pytest
from classes import Post
from helpers import log


# noinspection PyMissingTypeHints
@pytest.mark.parametrize("title, body, username, site, body_is_summary, is_answer, expected_spam", [
    # These two are really long strings, we use Python formatting to make them legible
    ('A post on which testing hangs for minutes when using \\L<city>', '<p>sh%st%s</p>\n' % ('i' * 600, '!' * 38), 'Someone', 'askubuntu.com', True, True, False),
    ('A post which was hanging for minutes in pattern-matching websites after the \\L<city> fix', '<p>%s</p>\n' % ('burhan' * 3346), 'Someone', 'askubuntu.com', True, True, False),
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
    ('Spam spam spam', '', 'garciniacambogiaforskolin', 'stackoverflow.com', False, False, True),
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
    ('', '<p>Test <a href="https://example.com/" rel="nofollow">some text</a> moo moo moo.</p><p>Another paragraph. Make it long enough to bring this comfortably over the 300-character limit. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p><p><a href="https://example.com/" rel="nofollow">https://example.com/</a></p>', '', 'stackoverflow.com', False, False, True),
    ('spam', '>>>> http://', '', 'stackoverflow.com', True, False, False),
    ('Another title', '<code>>>>>https://</code>', '', 'stackoverflow.com', False, False, False),
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
    ('Cannot access https://stackoverflow.com/ with proxy enabled', '', '', 'superuser.com', False, False, False),
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
    ('Title here', '<img src="http://example.com/11111111111.jpg" alt="my image">', '', 'stackoverflow.com', False, False, True),
    ('Title here', '<img src="http://example.com/11111111111111.jpg" alt="my image" />', '', 'stackoverflow.com', False, False, True),
    ('Title here', '<a href="http://example.com/11111111111111.html">page</a>', '', 'stackoverflow.com', False, False, False),
    ('Error: 2147467259', '', '', 'stackoverflow.com', False, False, False),
    ('Max limit on number of concurrent ajax request', """<p>Php java script boring yaaarrr <a href="http://www.price-buy.com/" rel="nofollow noreferrer">Price-Buy.com</a> </p>""", 'Price Buy', 'stackoverflow.com', True, True, True),
    ('Proof of onward travel in Japan?', """<p>The best solution to overcome the problem of your travel<a href="https://i.stack.imgur.com/eS6WQ.jpg" rel="nofollow noreferrer"><img src="https://i.stack.imgur.com/eS6WQ.jpg" alt="enter image description here"></a></p>

<p>httl://bestonwardticket.com</p>""", 'Best onward Ticket', 'travel.stackexchange.com', True, True, True),
    ('Max limit on number of concurrent ajax request', """<p>Php java script boring yaaarrr <a href="https://www.google.com/" rel="nofollow noreferrer">Google.com</a> </p>""", 'Totally Unrelated Username', 'stackoverflow.com', True, True, False),
    ('Asp.NET Identity will not consistently authenticate users', """<p>I am definitely not the only one experiencing this anomaly (<a href="https://stackoverflow.com/questions/46559016/asp-net-identity-login-sometimes-yes-and-sometimes-no">Asp.net: Identity Login sometimes yes and sometimes no</a>), and I have been combind StackExchange for some solution (I have tried literally dozens of suggestions), and simply nothing delivers a consistent fix.</p>""", 'Dan Martini', 'stackoverflow.com', False, False, False),
    ('Power a circuit off USB the correct way', """<p>I'd like to properly power a gadget off USB (2.4A USB powerbank <a href="https://rads.stackoverflow.com/amzn/click/B00X5RV14Y" rel="nofollow noreferrer">https://www.amazon.com/Anker-20100mAh-Portable-Charger-PowerCore/dp/B00X5RV14Y/ref=sr_1_3?ie=UTF8&qid=1512261941&sr=8-3</a>) consisting of:</p>""", 'iMrFelix', 'electronics.stackexchange.com', False, False, False),
    ('GUI over bash using glade', """<p>I want to make a remote control for my PC. Basically all I need is to run a command on a button click. Following this <a href="https://www.youtube.com/watch?v=cNWmleAJ2qg" rel="nofollow noreferrer">guide</a> I managed to build the <a href="https://i.stack.imgur.com/dMy9g.jpg" rel="nofollow noreferrer">layout</a> and it's everything i've ever dreamed of.
But when I try to run it using</p>""", 'Pacman', 'stackoverflow.com', False, False, False),
    ('Misleading link common file whitelist', 'File: <a href="https://www.malicious.com/"> https://google.com/file.txt </a>', '', 'stackoverflow.com', False, False, True),
    ('Misleading link common file whitelist', 'File: <a href="https://www.malicious.txt/">https://google.com</a>', '', 'stackoverflow.com', False, False, False),
    ('Misleading link: Don\'t detect link text at end of URL', 'File: <a href="https://www.example.com/foo.txt">foo.txt</a>', '', 'stackoverflow.com', False, False, False),
    ('Misleading link: No safe extensions on SO', 'File: <a href="https://www.malicious.com/">file.py</a>', '', 'stackoverflow.com', False, False, False),
    ('Misleading link: Detect safe extensions when not on SO', 'File: <a href="https://www.malicious.com/">file.py</a>', '', 'superuser.com', False, False, True),
    ('Misleading link: Don\'t detect w/o valid FLD in link text', 'File: <a href="https://www.malicious.com/foo.txt">co.uk</a>', '', 'stackoverflow.com', False, False, False),
    ('Misleading link: Do detect w/ valid FLD in link text', 'File: <a href="https://www.malicious.com/foo.txt">foobar.co.uk</a>', '', 'stackoverflow.com', False, False, True),
    ('Pattern-matching product name', 'Pro Keto Max', '', 'stackoverflow.com', False, False, True),
    ('Pattern-matching product name', 'Alpha Formula Pro', '', 'meta.stackexchange.com', False, False, False),
    ('Pattern-matching product name sucks', 'X1 X2 X3', '', 'stackoverflow.com', False, False, False),
    ('Body starts with title', 'Body starts with title and ends with <a href="https://example.com">https://example.com</a>', '', '', False, False, True),
    ('Body starts with title', 'Body starts with title and ends with <a href="https://example.com">https://example.com</a>', '', '', False, True, False),
    ('Advanced BSWT', '<p><a href="......">Product Name</a> Advanced BSWT is a must-have <a href="https://example.com">https://example.com</a></p>', '', '', False, False, True),
    ('IDNA misleading link', '<a href="http://www.h%c3%a5nd.no">http://www.h\u00E5nd.no</a>', '', '', False, False, False),
    ('Mostly punctuation', ';[].[.[.&_$)_\\*&_@$.[;*/-!#*&)(_.\'].1\\)!#_', '', '', False, False, True),
    ('Few unique', 'asdss, dadasssaadadda, daaaadadsss, ssa,,,addadas,ss\nsdadadsssadadas, sss\ndaaasdddsaaa, asd', '', '', False, False, True),
    ('ketones', 'ketones', 'ketones', 'chemistry.stackexchange.com', False, False, False),
    ('ketones', 'ketones', 'ketones', 'chemistry.stackexchange.com', False, True, False),
    ('ketones', 'ketones', 'ketones', 'chemistry.stackexchange.com', True, False, False),
    ('ketones', 'ketones', 'ketones', 'chemistry.stackexchange.com', True, True, False),
    ('keytones', '<p>Some body</p>', 'a username', 'superuser.com', False, False, True),
    ('A title', 'keytones', 'a username', 'superuser.com', False, False, True),
    ('A title', '<p>Some body</p>', 'keytones', 'superuser.com', False, False, True),
    ('keytones', '<p>Some body</p>', 'a username', 'superuser.com', False, True, False),
    ('A title', 'keytones', 'a username', 'superuser.com', False, True, True),
    ('A title', '<p>Some body</p>', 'keytones', 'superuser.com', False, True, True),
    ('keytones', '<p>Some body</p>', 'a username', 'superuser.com', True, False, True),
    ('A title', 'keytones', 'a username', 'superuser.com', True, False, True),
    ('A title', '<p>Some body</p>', 'keytones', 'superuser.com', True, False, True),
    ('keytones', '<p>Some body</p>', 'a username', 'superuser.com', True, True, False),
    ('A title', 'keytones', 'a username', 'superuser.com', True, True, True),
    ('A title', '<p>Some body</p>', 'keytones', 'superuser.com', True, True, True),
    ('C01nb4s3 support number', 'obfuscated_word in title', 'spammer', 'stackoverflow.com', False, False, True),
    ('obfuscated_word in body', 'C01nb4$3 support number', 'spammer', 'stackoverflow.com', False, False, True),
    ('''airline's responsibilities''', 'test case for "not obfuscated after all" (#7345)', 'good guy', 'stackoverflow.com', False, False, False),
    ('emoji \U0001f525 emoji', 'emoji \U0001f525 emoji \U0001f525 emoji', 'tripleee', 'stackoverflow.com', True, False, False),
    ('emoji \U0001f525 emoji \U0001f525 emoji', 'two emojis in title should trigger, others not', 'tripleee', 'stackoverflow.com', True, False, True),
    ('number sequence 1 to 30', '<p>1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30</p>', 'a username', 'math.stackexchange.com', False, False, False),
    ('Multiple consecutive numbers 1', '<p>Some1-888-884-0111 888-884-0111 +1-972-534-5446 972-534-5446 1-628-215-2166 628-215-2166 1-844-802-7535 844-802-7535 body</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('Phone numbers 01', '<p>Some1i888i884i0111 body</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('Phone numbers 02', '<p>Some+1l972l534l5446body</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('Phone numbers 03', '<p>Some972-534-5446ObOdyyy</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 01', '<p>SomeI-888-884-Olll fobody</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 02', '<p>Some888-884-OIII foo body</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 03', '<p>Some +I-972-S34-S446 body</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 04', '<p>Some 972-S34-S446 foobody</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 05', '<p>Some I-628-21S-2I66 fbody</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 06', '<p>Some 628a21Sa2l66 foobody</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 07', '<p>Some 1-844i8O2i7S3S fbody</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('homoglyph phone numbers 08', '<p>Some 844-8O2-7S3S foobody</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('Multiple consecutive homoglyph numbers 1', '<p>SomeI-888-884-Olll 888-884-OIII +I-972-S34-S446 972-S34-S446 I-628-21S-2I66 628-21S-2l66 1-844i8O2i7S3S 844a8O2a7S3S body</p>', 'a username', 'math.stackexchange.com', False, False, True),
    ('A title with a 321-987-4242 phone number', 'body not checked', 'a username', 'superuser.com', False, False, True),
    ('A title with an 50.22.30.40/32 IP', 'body not checked', 'a username', 'superuser.com', False, False, False),
    ('A title with an 502-230-4032', 'body not checked', 'a username', 'superuser.com', False, False, True),
    ('A title with a 4 digit 321-987-4.2.4.2 IP and numbers', 'body not checked', 'a username', 'superuser.com', False, False, True),
    ('A title with a 5 digit 321-987-4.2.4.23/2 IP and numbers', 'body not checked', 'a username', 'superuser.com', False, False, False),
    ('A title with a 5 digit 1.20.3.4/32 IP and numbers 182', 'body not checked', 'a username', 'superuser.com', False, False, False),
])
def test_findspam(title, body, username, site, body_is_summary, is_answer, expected_spam):
    post = Post(api_response={'title': title, 'body': body,
                              'owner': {'display_name': username, 'reputation': 1, 'link': ''},
                              'site': site, 'question_id': '1', 'IsAnswer': is_answer,
                              'BodyIsSummary': body_is_summary, 'score': 0})
    full_result = FindSpam.test_post(post)
    result = full_result[0]
    why = full_result[1]
    log('info', "Test post title:", title)
    log('info', "Result:", result)
    log('info', "Why:", why)
    scan_spam = (len(result) > 0)
    if scan_spam != expected_spam:
        print("Expected {1} on {0}".format(body, expected_spam))
    assert scan_spam == expected_spam


# noinspection PyMissingTypeHints
@pytest.mark.parametrize("title, body, username, expected_spam", [
    ('A title', '<p><a href="https://triple.ee/ns-test">foo</a>', 'tripleee', True),
    ('A title', '<p><a href="https://www.triple.ee/ns-test">foo</a>', 'tripleee', True),
    ('A title', '<p><a href="https://charcoal-se.org/ns-test">foo</a>', 'tripleee', False),
])
def test_ns(title, body, username, expected_spam):
    blacklisted_ip = get_ns_ips('triple.ee')[0]
    site = 'stackoverflow.com'
    # post = Post(api_response={'title': title, 'body': body,
    #                          'owner': {'display_name': username, 'reputation': 1, 'link': ''},
    #                          'site': site, 'question_id': '1', 'IsAnswer': False,
    #                          'BodyIsSummary': False, 'score': 0})
    what, why = ip_for_url_host(body, site, [blacklisted_ip])
    assert what is expected_spam
    if expected_spam:
        assert ' suspicious IP address {0} for NS'.format(blacklisted_ip) in why
