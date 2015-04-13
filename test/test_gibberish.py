# -*- coding: utf-8 -*-

from gibberish import classify_gibberish, strip_unwanted
from datahandling import is_frequent_sentence
from globalvars import GlobalVars
import pytest

GlobalVars.frequent_sentences = ["try this", "try the following",
                                 "try this code"]
# actual sentences are stored in a file, above values are for testing


@pytest.mark.parametrize("sentence, expected", [
    ("try this", True),
    ("try the following", True),
    ("try this code", True),
    ("Try this:", True),
    ("Try  this :!", True),
    ("  Try this", True),
    ("Try this, it will solve your problem", False),
    ("You should try this", False)
])
def test_frequent_sentences(sentence, expected):
    assert is_frequent_sentence(sentence) == expected


@pytest.mark.parametrize("original, expected, site", [
    ("Code: <pre>code here</pre>", "Code:", "stackoverflow.com"),
    ("Code: <code>code here</code>", "Code:", "stackoverflow.com"),
    ("<strong>This is <em>a</em></strong> sentence.", "This is a sentence.", "stackoverflow.com"),
    ("$MathJax$", "", "math.stackexchange.com"),
    ("$MathJax$", "$MathJax$", "stackoverflow.com"),
    ("\$MathJax$", "\$MathJax$", "math.stackexchange.com"),
    ("$$MathJax\nMore MathJax$$", "", "math.stackexchange.com"),
    ("Formula: $2+3=5$ try this", "Formula: try this", "math.stackexchange.com"),
    ("&lt;", "<", "communitybuilding.stackexchange.com"),
    ("Multiple   spaces   ", "Multiple spaces", "stackoverflow.com"),
    (u"Other language: Как вывести из базы все данные", "Other language:", "ru.stackoverflow.com")
])
def test_strip_unwanted(original, expected, site):
    assert strip_unwanted(original, site) == expected


def test_gibberish_classification():
    assert classify_gibberish("This is code: <pre>code</pre>", "stackoverflow.com") \
        == classify_gibberish("This is code:", "superuser.com")
    assert classify_gibberish("", "stackoverflow.com") == (False, 1)
    assert classify_gibberish("asaaasaadsapgoeaaaaafallppppp", "stackoverflow.com")[0] is True