from findspam import FindSpam
import pytest

@pytest.mark.parametrize("title, username, match", [
     ('18669786819 gmail customer service number 1866978-6819 gmail support number', '', True),
     ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', '', True),
     ('', 'bagprada', True),
     ('HOW DO YOU SOLVE THIS PROBLEM?', '', True),
     ('12 Month Loans quick @ http://www.quick12monthpaydayloans.co.uk/Elimination of collateral pledging', '', True),
     ('support for yahoo mail 18669786819 @call for helpline number', '', True),
     ('yahoo email tech support 1 866 978 6819 Yahoo Customer Phone Number ,Shortest Wait', '', True),
     ('What is the value of MD5 checksums if the MD5 hash itself could potentially also have been manipulated?', '', False),
     ('Probability: 6 Dice are rolled. Which is more likely, that you get exactly one 6, or that you get 6 different numbers?', '', False),
     ('The Challenge of Controlling a Powerful AI', 'Serban Tanasa', False),
     ('Reproducing image of a spiral using TikZ', 'Kristoffer Ryhl', False),
     ('What is the proper way to say "queryer"', 'jedwards', False),
     ('What\'s a real-world example of "overfitting"?', 'user3851283', False),
     ('How to avoid objects when traveling at greater than .75 light speed. or How Not to Go SPLAT?', 'bowlturner', False),
     ('Is it unfair to regrade prior work after detecting cheating?', 'Village', False),
])

def test_regexes(title, username, match):
    result = FindSpam.testpost(title, username, "")
    print title
    print result
    isspam = False
    if (len(result) > 0):
        isspam = True
    assert match == isspam
