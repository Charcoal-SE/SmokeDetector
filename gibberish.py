from GibberishClassifier import gibberishclassifier
import regex
import string
from HTMLParser import HTMLParser
from datahandling import is_frequent_sentence


def strip_unwanted(body, site):
    body_no_code = regex.sub("<pre>.*?</pre>", "", body, flags=regex.DOTALL)
    body_no_code = regex.sub("<code>.*?</code>", "", body_no_code, flags=regex.DOTALL)
    body_html_stripped = regex.sub("</?[a-zA-Z0-9_:/%?=\"'\\.,\\s-]+>", "", body_no_code)
    if site in ["math.stackexchange.com", "puzzling.stackexchange.com", "mathoverflow.net"]:
        body_no_mathjax = regex.sub(r"(?<!\\)(\$\$?).+(?<!\\)\1", "", body_html_stripped, flags=regex.DOTALL)
    else:
        body_no_mathjax = body_html_stripped
    no_unicode = ''.join([x for x in body_no_mathjax if x in string.printable])
    parser = HTMLParser()
    unescaped = parser.unescape(no_unicode)
    merged_spaces = regex.sub(r"\s+", " ", unescaped).strip()
    return merged_spaces


def classify_gibberish(body, site):
    body_plain_text = strip_unwanted(body, site)
    # Don't classify if the only text is a "frequent sentence", because
    # these are very short so they give inaccurate results when classifying.
    if body_plain_text == "" or is_frequent_sentence(body_plain_text)\
            or site in ["ja.stackoverflow.com", "ru.stackoverflow.com", "pt.stackoverflow.com"]:
        return False, 1
    score = gibberishclassifier.classify(body_plain_text)
    return True, score
