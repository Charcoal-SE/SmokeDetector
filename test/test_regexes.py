from findspam import FindSpam
import pytest

@pytest.mark.parametrize("text, match", [
     ('18669786819 gmail customer service number 1866978-6819 gmail support number', True),
     ('Is there any http://www.hindawi.com/ template for Cloud-Oriented Data Center Networking?', True),
     ('bagprada', True),
     ('What is the value of MD5 checksums if the MD5 hash itself could potentially also have been manipulated?', False),
     ('Probability: 6 Dice are rolled. Which is more likely, that you get exactly one 6, or that you get 6 different numbers?', False),
     ('HOW DO YOU SOLVE THIS PROBLEM?', True),
])

def test_regexes(text, match):
    result = FindSpam.testpost(text, "", "")
    print text
    print result
    isspam = False
    if (len(result) > 0):
        isspam = True
    assert match == isspam