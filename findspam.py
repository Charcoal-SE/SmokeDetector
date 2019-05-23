# -*- coding: utf-8 -*-
# noinspection PyCompatibility

import sys
import math
import regex
from difflib import SequenceMatcher
from urllib.parse import urlparse, unquote_plus
from itertools import chain
from collections import Counter
from datetime import datetime
import time
import os
import os.path as path

# noinspection PyPackageRequirements
import tld
# noinspection PyPackageRequirements
from tld.utils import TldDomainNotFound
import phonenumbers
import dns.resolver
import requests
import chatcommunicate

from helpers import log
from globalvars import GlobalVars
import blacklists


TLD_CACHE = []
DNS_CACHE = dict()
LINK_CACHE = dict()
LEVEN_DOMAIN_DISTANCE = 3
SIMILAR_THRESHOLD = 0.95
SIMILAR_ANSWER_THRESHOLD = 0.7
BODY_TITLE_SIMILAR_RATIO = 0.90
CHARACTER_USE_RATIO = 0.42
PUNCTUATION_RATIO = 0.42
REPEATED_CHARACTER_RATIO = 0.20
EXCEPTION_RE = r"^Domain (.*) didn't .*!$"
RE_COMPILE = regex.compile(EXCEPTION_RE)
COMMON_MALFORMED_PROTOCOLS = [
    ('httl://', 'http://'),
]
# These types of files frequently get caught as "misleading link"
SAFE_EXTENSIONS = {'htm', 'py', 'java', 'sh'}
SE_SITES_RE = r'(?:{sites})'.format(
    sites='|'.join([
        r'(?:[a-z]+\.)*stackoverflow\.com',
        r'(?:{doms})\.com'.format(doms='|'.join(
            [r'askubuntu', r'superuser', r'serverfault', r'stackapps', r'imgur'])),
        r'mathoverflow\.net',
        r'(?:[a-z]+\.)*stackexchange\.com']))
SE_SITES_DOMAINS = ['stackoverflow.com', 'askubuntu.com', 'superuser.com', 'serverfault.com',
                    'mathoverflow.net', 'stackapps.com', 'stackexchange.com', 'sstatic.net',
                    'imgur.com']  # Frequently catching FP
WHITELISTED_WEBSITES_REGEX = regex.compile(r"(?i)upload|\b(?:{})\b".format("|".join([
    "yfrog", "gfycat", "tinypic", "sendvid", "ctrlv", "prntscr", "gyazo", r"youtu\.?be", "past[ie]", "dropbox",
    "microsoft", "newegg", "cnet", "regex101", r"(?<!plus\.)google", "localhost", "ubuntu", "getbootstrap",
    r"jsfiddle\.net", r"codepen\.io", "pastebin"
] + [se_dom.replace(".", r"\.") for se_dom in SE_SITES_DOMAINS])))
ASN_WHITELISTED_WEBSITES = [
    "unity3d.com", "ffmpeg.org", "bitcoincore.org", "latex.codecogs.com",
    "advancedcustomfields.com", "name.com", "businessbloomer.com",
    "wkhtmltopdf.org", "thefreedictionary.com", "ruby-doc.org",
    "site.com.br", "test.ooo-pnu.ru", "swift.org", "site2.com",
    "rxweb.io", "tenforums.com", "rhydolabz.com", "javatpoint.com",
    # ^^ top 20 FP hosts that get reported due to 'bad ASN', collated by regex parsing
    # https://metasmoke.erwaysoftware.com/data/sql/queries/164-bad-asn-in-false-positives
    # As of 2019-04-18, the following had >=6 ASN detections which were FP
    "ampps.com", "bintray.com", "config.ru", "datetime.date", "myexample.com",
    "mywiki.wooledge.org", "sevenforums.com", "ultimatefreehost.in", "wa.me", "web.com",
    # As of 2019-04-18, the following had 5 ASN detections which were FP
    "androidforums.com", "getclayton.com", "indeed.com", "math.net",
    "mobilefirstplatform.ibmcloud.com", "ss.ms", "table.to",
    # As of 2019-04-18, the following had 4 ASN detections which were FP
    "code.kx.com", "daniweb.com", "files.catbox.moe", "greatrecipetips.com", "html5up.net",
    "irc.freenode.net", "italian-stresser.online", "meteocaldas.com", "techpowerup.com",
    "unit-conversion.info", "wicked.io",
    # not being added: bitcoinofficial.org, learn-neural-networks.com
    # As of 2019-04-18, the following had 3 ASN detections which were FP
    "bankingifsccodes.com", "bethelp.byethost3.com", "calculator.net", "change.by",
    "clover.com", "cognimem.com", "csde.epizy.com", "docker.bintray.io", "domaine.com",
    "dreamstime.com", "embedded101.com", "emildeveloping.com", "extjs.eu", "fixer.io",
    "fondation-zeitgeist.com", "form.media", "formcontact.esy.es", "godandscience.org",
    "kajariaceramics.com", "macappstore.org", "maven.ibiblio.org", "nayuki.io", "nxos.org",
    "pdf.datasheetcatalog.com", "php.info", "pool.sks-keyservers.net", "reg.ru", "scaan.in",
    "shop.btownmedia.com", "smtp.sendgrid.net", "sysengineering.ru", "techspot.com",
    "testking.com", "thecollegeroar.com", "ursuscode.com", "vwo.com",
    # Not added:
    # 000webhostapp.com  This domain would be reasonable to add if it didn't also whitelist all subdomains.
    # As of 2019-04-18, the following had 2 ASN detections which were FP, and appeared to be common.
    "wikileaks.org",
    # Added to prevent having 3 detections on just the domain.
    "writingexplained.org"]
COUNTRY = [
    # N Europe
    "Iceland", "Denmark", "Sweden", "Norway",
    # Oceania
    "Australia", "New Zealand", "NewZealand",
]

if GlobalVars.perspective_key:
    PERSPECTIVE = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key=" + GlobalVars.perspective_key
    PERSPECTIVE_THRESHOLD = 0.85  # conservative

# Flee before the ugly URL validator regex!
# We are using this, instead of a nice library like BeautifulSoup, because spammers are
# stupid and don't always know how to actually *link* their web site. BeautifulSoup misses
# those plain text URLs.
# https://gist.github.com/dperini/729294#gistcomment-1296121
URL_REGEX = regex.compile(
    r"""((?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)"""
    r"""(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2}))"""
    r"""(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"""
    r"""(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"""
    r"""|\b(?:(?:[A-Za-z\u00a1-\uffff0-9]-?)*[A-Za-z\u00a1-\uffff0-9]+)(?:\.(?:[A-Za-z\u00a1-\uffff0-9]-?)"""
    r"""*[A-Za-z\u00a1-\uffff0-9]+)*(?:\.(?:[A-Za-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/\S*)?""", regex.U)
TAG_REGEX = regex.compile(r"</?[abcdehiklopsu][^>]*?>|\w+://", regex.U)
NUMBER_REGEX = regex.compile(r'(?<=\D|^)\+?(?:\d[\W_]*){8,13}\d(?=\D|$)', regex.U | regex.I)

UNIFORM = math.log(1 / 36)
UNIFORM_PRIOR = math.log(1 / 5)

ENGLISH = {
    'a': -2.56940287968626,
    'e': -2.6325365263400786,
    'o': -2.9482912667071903,
    'r': -2.9867566750238046,
    'i': -3.043195438576378,
    's': -3.053589802306065,
    'n': -3.0696364572432233,
    '1': -3.134872509228817,
    't': -3.230441879550407,
    'l': -3.2558408400221905,
    '2': -3.4663376838336166,
    'm': -3.4810979044444426,
    'd': -3.5635447023561517,
    '0': -3.5958227205042967,
    'c': -3.6348280308631855,
    'p': -3.6771505079154236,
    '3': -3.7158848391017765,
    'h': -3.7019152926538648,
    'b': -3.74138548356748,
    'u': -3.8457967842578014,
    'k': -3.9048726800430713,
    '4': -3.9411171656325226,
    '5': -3.9708339604329925,
    'g': -3.961715896933319,
    '9': -4.019842096462643,
    '6': -4.041864072829501,
    '8': -4.096998079687665,
    '7': -4.122126943234552,
    'y': -4.1666976658279635,
    'f': -4.351040269361279,
    'w': -4.360690517108493,
    'j': -4.741006747760368,
    'v': -4.759276833451455,
    'z': -5.036594538526155,
    'x': -5.137009730369897,
    'q': -5.624531280146579
}
ENGLISH_PRIOR = math.log(4 / 5)


class PostFilter:
    """
    General filter for SE posts
    """

    def __init__(self, all_sites=True, sites=None, max_rep=1, max_score=0, question=True, answer=True):
        self.all_sites = all_sites
        self.sites = set(sites) if sites is not None else set()
        self.max_rep = max_rep
        self.max_score = max_score
        self.question = question
        self.answer = answer

    def match(self, post):
        """
        See if a post matches this filter
        """
        if (post.is_answer and not self.answer) or (not post.is_answer and not self.question):
            # Wrong post type
            return False
        elif self.all_sites == (post.post_site in self.sites):
            # Post is on wrong site
            return False
        elif (post.owner_rep > self.max_rep) or (post.post_score > self.max_score):
            # High score or high rep
            return False
        else:
            return True


class Rule:
    """
    A single spam-checking rule
    """

    default_filter = PostFilter()

    def __init__(self, item, reason, title=True, body=True, body_summary=True, username=True, filter=None,
                 stripcodeblocks=False, whole_post=False):
        self.regex = None
        self.func = None
        if isinstance(item, (str, URL_REGEX.__class__)):
            self.regex = item
        else:
            self.func = item
        self.reason = reason
        self.title = title
        self.body = body
        self.body_summary = body_summary
        self.username = username
        self.filter = filter or Rule.default_filter
        self.stripcodeblocks = stripcodeblocks
        self.whole_post = whole_post

    def match(self, post):
        """
        Run this rule against a post. Returns a list of 3 tuples, each in (match, reason, why) format
        """
        if not self.filter.match(post):
            # Post not matching the filter
            return [(False, "", "")] * 3

        body_to_check = post.body.replace("&nsbp;", "").replace("\xAD", "") \
                                 .replace("\u200B", "").replace("\u200C", "")
        body_name = "body" if not post.is_answer else "answer"
        reason_title = self.reason.replace("{}", "title")
        reason_username = self.reason.replace("{}", "username")
        reason_body = self.reason.replace("{}", body_name)

        if self.stripcodeblocks:
            # use a placeholder to avoid triggering "few unique characters" when most of post is code
            # XXX: "few unique characters" doesn't enable this, so remove placeholder?
            body_to_check = regex.sub("(?s)<pre>.*?</pre>", "\ncode\n", body_to_check)
            body_to_check = regex.sub("(?s)<code>.*?</code>", "\ncode\n", body_to_check)
        if self.reason == 'phone number detected in {}':
            body_to_check = regex.sub("<(?:a|img)[^>]+>", "", body_to_check)

        matched_title, matched_body, matched_username = False, False, False
        result_title, result_username, result_body = None, None, None
        if self.func:  # Functional check takes precedence over regex check
            if self.whole_post:
                matched_title, matched_username, matched_body, why_text = self.func(post)
                result_title = (matched_title, reason_title,
                                reason_title.capitalize() + " - " + why_text)
                result_username = (matched_username, reason_username,
                                   reason_username.capitalize() + " - " + why_text)
                result_body = (matched_body, reason_body,
                               reason_body.capitalize() + " - " + why_text)
            else:
                if self.title and not post.is_answer:
                    matched_title, why_text = self.func(post.title, post.post_site)
                    result_title = (matched_title, reason_title,
                                    reason_title.capitalize() + " - " + why_text)
                else:
                    result_title = (False, "", "")

                if self.username:
                    matched_username, why_text = self.func(post.user_name, post.post_site)
                    result_username = (matched_username, reason_username,
                                       reason_username.capitalize() + " - " + why_text)
                else:
                    result_username = (False, "", "")

                if self.body and not post.body_is_summary:
                    matched_body, why_text = self.func(body_to_check, post.post_site)
                    result_body = (matched_body, reason_body,
                                   reason_body.capitalize() + " - " + why_text)
                elif self.body_summary and post.body_is_summary:
                    matched_body, useless = self.func(body_to_check, post.post_site)
                    result_body = (matched_body, "", "")
                else:
                    result_body = (False, "", "")
        elif self.regex:
            compiled_regex = regex.compile(self.regex, regex.UNICODE, city=city_list)

            if self.title and not post.is_answer:
                matches = list(compiled_regex.finditer(post.title))
                result_title = (bool(matches), reason_title,
                                reason_title.capitalize() + " - " + FindSpam.match_infos(matches))
            else:
                result_title = (False, "", "")

            if self.username:
                matches = list(compiled_regex.finditer(post.user_name))
                result_username = (bool(matches), reason_username,
                                   reason_username.capitalize() + " - " + FindSpam.match_infos(matches))
            else:
                result_username = (False, "", "")

            if (self.body and not post.body_is_summary) \
                    or (self.body_summary and post.body_is_summary):
                matches = list(compiled_regex.finditer(body_to_check))
                result_body = (bool(matches), reason_body,
                               reason_body.capitalize() + " - " + FindSpam.match_infos(matches))
            else:
                result_body = (False, "", "")
        else:
            raise TypeError("A rule must have either 'func' or 'regex' valid!")

        # "result" format: tuple((title_spam, reason, why), (username_spam, reason, why), (body_spam, reason, why))
        return result_title, result_username, result_body

    def __call__(self, *args, **kwargs):
        # Preserve the functionality of a function
        if self.func:
            return self.func(*args, **kwargs)
        raise TypeError("This rule has no function set, can't call")


class FindSpam:
    rules = []

    # supplied at the bottom of this file
    rule_bad_keywords = None
    rule_watched_keywords = None
    rule_blacklisted_websites = None
    rule_blacklisted_usernames = None

    @classmethod
    def reload_blacklists(cls):
        global bad_keywords_nwb

        blacklists.load_blacklists()
        # See PR 2322 for the reason of (?:^|\b) and (?:\b|$)
        # (?w:\b) is also useful
        cls.rule_bad_keywords.regex = r"(?is)(?:^|\b|(?w:\b))(?:{})(?:\b|(?w:\b)|$)|{}".format(
            "|".join(GlobalVars.bad_keywords), "|".join(bad_keywords_nwb))
        cls.rule_watched_keywords.regex = r'(?is)(?:^|\b|(?w:\b))(?:{})(?:\b|(?w:\b)|$)'.format(
            "|".join(GlobalVars.watched_keywords.keys()))
        cls.rule_blacklisted_websites.regex = r"(?i)({})".format(
            "|".join(GlobalVars.blacklisted_websites))
        cls.rule_blacklisted_usernames.regex = r"(?i)({})".format(
            "|".join(GlobalVars.blacklisted_usernames))
        GlobalVars.blacklisted_numbers, GlobalVars.blacklisted_numbers_normalized = \
            process_numlist(GlobalVars.blacklisted_numbers)
        GlobalVars.watched_numbers, GlobalVars.watched_numbers_normalized = \
            process_numlist(GlobalVars.watched_numbers)
        log('debug', "Global blacklists loaded")

    @staticmethod
    def test_post(post):
        result = []
        why_title, why_username, why_body = [], [], []
        for rule in FindSpam.rules:
            title, username, body = rule.match(post)
            if title[0]:
                result.append(title[1])
                why_title.append(title[2])
            if username[0]:
                result.append(username[1])
                why_username.append(username[2])
            if body[0]:
                result.append(body[1])
                why_body.append(body[2])
        result = list(set(result))
        result.sort()
        why = "\n".join(sorted(why_title + why_username + why_body)).strip()
        return result, why

    @staticmethod
    def match_info(match):
        start, end = match.span()
        group = match.group().replace("\n", "")
        return "Position {}-{}: {}".format(start + 1, end, group)

    @staticmethod
    def match_infos(matches):
        spans = {}
        for match in matches:
            group = match.group().strip().replace("\n", "")
            if group not in spans:
                spans[group] = [match.span()]
            else:
                spans[group].append(match.span())
        infos = [(sorted(spans[word]), word) for word in spans]
        infos.sort(key=lambda info: info[0])  # Sort by positions of appearances
        return ", ".join([
            "Position{} {}: {}".format(
                "s" if len(span) > 1 else "",
                ", ".join(
                    ["{}-{}".format(a, b) for a, b in span]
                    if len(span) < 14 else
                    ["{}-{}".format(a, b) for a, b in span[:12]] + ["+{} more".format(len(span) - 12)]
                ),
                word
            )
            for span, word in infos])


########################################################################################################################
# The Creator of all the spam check rules
# Do NOT touch the default values unless you want to break things
# what if a function does more than one job?
def create_rule(reason, regex=None, func=None, *, all=True, sites=[],
                title=True, body=True, body_summary=False, username=False,
                max_score=0, max_rep=1, question=True, answer=True, stripcodeblocks=False,
                whole_post=False,  # For some functions
                disabled=False):  # yeah, disabled=True is intuitive
    if not isinstance(reason, str):
        raise ValueError("reason must be a string")

    if not (body or body_summary or username):  # title-only
        answer = False  # answers have no titles, this saves some loops
    post_filter = PostFilter(all_sites=all, sites=sites, max_score=max_score, max_rep=max_rep,
                             question=question, answer=answer)
    if regex is not None:
        # Standalone mode
        rule = Rule(regex, reason=reason, filter=post_filter,
                    title=title, body=body, body_summary=body_summary, username=username,
                    stripcodeblocks=stripcodeblocks)
        if not disabled:
            FindSpam.rules.append(rule)
        return rule
    else:
        # Decorator-generator mode
        def decorator(func):
            if isinstance(func, Rule):
                func = func.func  # Extract the real function from the created rule to allow multi-creation
                try:
                    func.__call__
                except AttributeError:
                    raise ValueError("This rule does not contain a function, can't recreate") from None
            rule = Rule(func, reason=reason, filter=post_filter, whole_post=whole_post,
                        title=title, body=body, body_summary=body_summary, username=username,
                        stripcodeblocks=stripcodeblocks)
            if not disabled:
                FindSpam.rules.append(rule)
            return rule

        if func is not None:  # Function is supplied, no need to decorate
            return decorator(func)
        else:  # real decorator mode
            return decorator


def is_whitelisted_website(url):
    # Imported from method link_at_end
    return bool(WHITELISTED_WEBSITES_REGEX.search(url))


def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def contains_tld(s):
    global TLD_CACHE

    # Hackity hack.
    if len(TLD_CACHE) == 0:
        with open(path.join(tld.defaults.NAMES_LOCAL_PATH_PARENT, tld.defaults.NAMES_LOCAL_PATH), 'r') as f:
            TLD_CACHE = [x.rstrip('\n') for x in f.readlines() if x.rstrip('\n') and
                         not x.strip().startswith('//')]

    return any(('.' + x) in s for x in TLD_CACHE)


@create_rule("misleading link", title=False, max_rep=10, max_score=1, stripcodeblocks=True)
def misleading_link(s, site):
    link_regex = r"<a href=\"([^\"]+)\"[^>]*>([^<]+)<\/a>"
    compiled = regex.compile(link_regex)
    search = compiled.search(s)
    if search is None:
        return False, ''

    href, text = search[1], search[2]
    try:
        parsed_href = tld.get_tld(href, as_object=True)
        if parsed_href.fld in SE_SITES_DOMAINS:
            log('debug', "{}: SE domain".format(parsed_href.fld))
            return False, ''
        log('debug', "{}: not an SE domain".format(parsed_href.fld))
        if contains_tld(text) and ' ' not in text:
            parsed_text = tld.get_tld(text, fix_protocol=True, as_object=True)
        else:
            raise tld.exceptions.TldBadUrl('Link text is not a URL')
    except (tld.exceptions.TldDomainNotFound, tld.exceptions.TldBadUrl, ValueError) as err:
        return False, ''

    if site == 'stackoverflow.com' and parsed_text.fld.split('.')[-1] in SAFE_EXTENSIONS:
        return False, ''

    if levenshtein(parsed_href.domain, parsed_text.domain) <= LEVEN_DOMAIN_DISTANCE:  # Preempt
        return False, ''

    try:
        href_domain = unquote_plus(parsed_href.domain.encode("ascii").decode("idna"))
    except ValueError:
        href_domain = parsed_href.domain
    try:
        text_domain = unquote_plus(parsed_text.domain.encode("ascii").decode("idna"))  # people do post this, sad
    except ValueError:
        text_domain = parsed_text.domain

    if levenshtein(href_domain, text_domain) > LEVEN_DOMAIN_DISTANCE:
        return True, 'Domain {} indicated by possible misleading text {}.'.format(
            parsed_href.fld, parsed_text.fld
        )
    else:
        return False, ''


# noinspection PyUnusedLocal,PyMissingTypeHints,PyTypeChecker
@create_rule("repeating words in {}", max_rep=11, stripcodeblocks=True)
def has_repeating_words(s, site):
    # RegEx DoS warning!!!
    matcher = regex.compile(r"\b(?P<words>(?P<word>[a-z]+))(?:[][\s.,;!/\()+_-]+(?P<words>(?P=word))){4,}\b",
                            flags=regex.I | regex.S | regex.V0)
    for match in matcher.finditer(s):
        words = match.captures("words")
        word = match.group("word")
        if len(words) >= 5 and len(word) * len(words) >= 0.18 * len(s):
            return True, "{}*{}".format(repr(word), len(words))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("few unique characters in {}", title=False, max_rep=10000, max_score=10000)
def has_few_characters(s, site):
    s = regex.sub("</?(?:p|strong|em)>", "", s).rstrip()  # remove HTML paragraph tags from posts
    uniques = len(set(s) - {"\n", "\t"})
    length = len(s)
    thresholds = [  # LBound, UBound, MaxUnique
        (30, 36, 6), (36, 42, 7), (42, 48, 8), (48, 54, 9), (54, 60, 10),
        (60, 70, 11), (70, 80, 12), (80, 90, 13), (90, 100, 14), (100, 2**30, 15),
    ]
    if any([t[0] <= length < t[1] and uniques <= t[2] for t in thresholds]):
        if uniques >= 5 and site == "math.stackexchange.com":
            # Special case for Math.SE: Uniques case may trigger false-positives.
            return False, ""
        return True, "Contains {} unique character{}".format(uniques, "s" if uniques >= 2 else "")
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("repeating characters in {}", stripcodeblocks=True, max_rep=10000, max_score=10000)
def has_repeating_characters(s, site):
    s = s.strip().replace("\u200B", "").replace("\u200C", "")  # Strip leading and trailing spaces
    if "\n\n" in s or "<code>" in s or "<pre>" in s:
        return False, ""
    s = regex.sub(URL_REGEX, "", s)  # Strip URLs for this check
    if not s:
        return False, ""
    # matches = regex.compile(r"([^\s_.,?!=~*/0-9-])(\1{9,})", regex.UNICODE).findall(s)
    matches = regex.compile(r"([^\s\d_.])(\1{9,})", regex.UNICODE).findall(s)
    match = "".join(["".join(match) for match in matches])
    if len(match) / len(s) >= REPEATED_CHARACTER_RATIO:  # Repeating characters make up >= 20 percent
        return True, "{}".format(", ".join(
            ["{}*{}".format(repr(match[0]), len(''.join(match))) for match in matches]))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("link at end of {}", title=False, all=False, sites=[
    "superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com",
    "security.stackexchange.com", "patents.stackexchange.com", "money.stackexchange.com",
    "gaming.stackexchange.com", "arduino.stackexchange.com", "workplace.stackexchange.com"])
def link_at_end(s, site):   # link at end of question, on selected sites
    s = regex.sub("</?(?:strong|em|p)>", "", s)
    match = regex.compile(r"(?i)https?://(?:[.A-Za-z0-9-]*/?[.A-Za-z0-9-]*/?|plus\.google\.com/"
                          r"[\w/]*|www\.pinterest\.com/pin/[\d/]*)(?=</a>\s*$)").search(s)
    if match and not is_whitelisted_website(match.group(0)):
        return True, u"Link at end: {}".format(match.group(0))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints,PyTypeChecker
@create_rule("non-English link in {}", title=False, question=False, stripcodeblocks=True, sites=[
    "pt.stackoverflow.com", "es.stackoverflow.com", "ja.stackoverflow.com", "ru.stackoverflow.com",
    "rus.stackexchange.com", "islam.stackexchange.com", "japanese.stackexchange.com", "hinduism.stackexchange.com",
    "judaism.stackexchange.com", "buddhism.stackexchange.com", "chinese.stackexchange.com",
    "russian.stackexchange.com", "french.stackexchange.com", "portuguese.stackexchange.com",
    "spanish.stackexchange.com", "codegolf.stackexchange.com", "korean.stackexchange.com",
    "esperanto.stackexchange.com", "ukrainian.stackexchange.com"])
def non_english_link(s, site):   # non-english link in short answer
    if len(s) < 600:
        links = regex.compile(r'nofollow(?: noreferrer)?">([^<]*)(?=</a>)', regex.UNICODE).findall(s)
        for link_text in links:
            word_chars = regex.sub(r"(?u)\W", "", link_text)
            non_latin_chars = regex.sub(r"\w", "", word_chars)
            if len(word_chars) >= 1 and ((len(word_chars) <= 20 and len(non_latin_chars) >= 1) or
                                         (len(non_latin_chars) >= 0.05 * len(word_chars))):
                return True, u"Non-English link text: *{}*".format(link_text)
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints,PyTypeChecker
@create_rule("mostly non-Latin {}", stripcodeblocks=True, sites=[
    "stackoverflow.com", "ja.stackoverflow.com", "pt.stackoverflow.com", "es.stackoverflow.com",
    "islam.stackexchange.com", "japanese.stackexchange.com", "anime.stackexchange.com",
    "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com",
    "chinese.stackexchange.com", "french.stackexchange.com", "spanish.stackexchange.com",
    "portuguese.stackexchange.com", "codegolf.stackexchange.com", "korean.stackexchange.com",
    "ukrainian.stackexchange.com"], body_summary=True)
@create_rule("mostly non-Latin {}", all=False, sites=["stackoverflow.com"],
             stripcodeblocks=True, body_summary=True, question=False)
def mostly_non_latin(s, site):   # majority of post is in non-Latin, non-Cyrillic characters
    word_chars = regex.sub(r'(?u)[\W0-9]|http\S*', "", s)
    non_latin_chars = regex.sub(r"(?u)\p{script=Latin}|\p{script=Cyrillic}", "", word_chars)
    if len(non_latin_chars) > 0.4 * len(word_chars):
        return True, "Text contains {} non-Latin characters out of {}".format(len(non_latin_chars), len(word_chars))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("phone number detected in {}", body=False, sites=[
    "patents.stackexchange.com", "math.stackexchange.com", "mathoverflow.net"])
def has_phone_number(s, site):
    if regex.compile(r"(?i)\b(address(es)?|run[- ]?time|error|value|server|hostname|timestamp|warning|code|"
                     r"(sp)?exception|version|chrome|1234567)\b", regex.UNICODE).search(s):
        return False, ""  # not a phone number
    s = regex.sub("[^A-Za-z0-9\\s\"',|]", "", s)   # deobfuscate
    s = regex.sub("[Oo]", "0", s)
    s = regex.sub("[Ss]", "5", s)
    s = regex.sub("[Iil|]", "1", s)
    matched = regex.compile(r"(?<!\d)(?:\d{2}\s?\d{8,11}|\d\s{0,2}\d{3}\s{0,2}\d{3}\s{0,2}\d{4}|8\d{2}"
                            r"\s{0,2}\d{3}\s{0,2}\d{4})(?!\d)", regex.UNICODE).findall(s)
    test_formats = ["IN", "US", "NG", None]      # ^ don't match parts of too long strings of digits
    for phone_number in matched:
        if regex.compile(r"^21474(672[56]|8364)|^192168|^3221225").search(phone_number):
            return False, ""  # error code or limit of int size, or 192.168 IP, or 0xC000000_ error code
        for testf in test_formats:
            try:
                z = phonenumbers.parse(phone_number, testf)
                if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
                    log('debug', "Possible {}, Valid {}, Explain: {}".format(phonenumbers.is_possible_number(z),
                                                                             phonenumbers.is_valid_number(z), z))
                    return True, u"Phone number: {}".format(phone_number)
            except phonenumbers.phonenumberutil.NumberParseException:
                pass
    return False, ""


# noinspection PyMissingTypeHints
def check_numbers(s, numlist, numlist_normalized=None):
    """
    Extract sequences of possible phone numbers. Check extracted numbers
    against verbatim match (identical to item in list) or normalized match
    (digits are identical, but spacing or punctuation contains differences).
    """
    numlist_normalized = numlist_normalized or set()
    matches = []
    for number_candidate in NUMBER_REGEX.findall(s):
        if number_candidate in numlist:
            matches.append('{0} found verbatim'.format(number_candidate))
            continue
        # else
        normalized_candidate = regex.sub(r"[^\d]", "", number_candidate)
        if normalized_candidate in numlist_normalized:
            matches.append('{0} found normalized'.format(normalized_candidate))
    if matches:
        return True, '; '.join(matches)
    else:
        return False, ''


def process_numlist(numlist):
    processed = set(numlist)  # Sets are faster than Hong Kong journalists!
    normalized = {regex.sub(r"\D", "", entry) for entry in numlist}
    return processed, normalized


@create_rule("bad phone number in {}", body_summary=True, max_rep=5, max_score=1, stripcodeblocks=True)
def check_blacklisted_numbers(s, site):
    return check_numbers(s,
                         GlobalVars.blacklisted_numbers,
                         GlobalVars.blacklisted_numbers_normalized)


@create_rule("potentially bad keyword in {}", body_summary=True, max_rep=5, max_score=1, stripcodeblocks=True)
def check_watched_numbers(s, site):
    return check_numbers(s,
                         GlobalVars.watched_numbers,
                         GlobalVars.watched_numbers_normalized)


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("bad keyword in {}")
def has_customer_service(s, site):  # flexible detection of customer service
    s = s[0:300].lower()   # if applied to body, the beginning should be enough: otherwise many false positives
    s = regex.sub(r"[^A-Za-z0-9\s]", "", s)   # deobfuscate
    phrase = regex.compile(r"(tech(nical)? support)|((support|service|contact|help(line)?) (telephone|phone|"
                           r"number))").search(s)
    if phrase and site in ["askubuntu.com", "webapps.stackexchange.com", "webmasters.stackexchange.com"]:
        return True, u"Key phrase: *{}*".format(phrase.group(0))
    business = regex.compile(
        r"(?i)\b(airlines?|apple|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|"
        r"lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)\b").search(s)
    digits = len(regex.compile(r"\d").findall(s))
    if business and digits >= 5:
        keywords = regex.compile(r"(?i)\b(customer|help|care|helpline|reservation|phone|recovery|service|support|"
                                 r"contact|tech|technical|telephone|number)\b").findall(s)
        if len(set(keywords)) >= 2:
            matches = ", ".join(["".join(match) for match in keywords])
            return True, u"Scam aimed at *{}* customers. Keywords: *{}*".format(business.group(0), matches)
    return False, ""


# Bad health-related keywords in titles, health sites are exempt
@create_rule("bad keyword in {}", body=False, all=False, sites=[
    "stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com",
    "meta.stackexchange.com", "security.stackexchange.com", "webapps.stackexchange.com",
    "apple.stackexchange.com", "graphicdesign.stackexchange.com", "workplace.stackexchange.com",
    "patents.stackexchange.com", "money.stackexchange.com", "gaming.stackexchange.com", "arduino.stackexchange.com"])
def has_health(s, site):   # flexible detection of health spam in titles
    s = s[0:200]   # if applied to body, the beginning should be enough: otherwise many false positives
    capitalized = len(regex.compile(r"\b[A-Z][a-z]").findall(s)) >= 5   # words beginning with uppercase letter
    organ = regex.compile(r"(?i)\b(colon|skin|muscle|bicep|fac(e|ial)|eye|brain|IQ|mind|head|hair|peni(s|le)|"
                          r"breast|body|joint|belly|digest\w*)s?\b").search(s)
    condition = regex.compile(r"(?i)\b(weight|constipat(ed|ion)|dysfunction|swollen|sensitive|wrinkle|aging|"
                              r"suffer|acne|pimple|dry|clog(ged)?|inflam(ed|mation)|fat|age|pound)s?\b").search(s)
    goal = regex.compile(r"(?i)\b(supple|build|los[es]|power|burn|erection|tone(d)|rip(ped)?|bulk|get rid|mood)s?\b|"
                         r"\b(diminish|look|reduc|beaut|renew|young|youth|lift|eliminat|enhance|energ|shred|"
                         r"health(?!kit)|improve|enlarge|remov|vital|slim|lean|boost|str[oe]ng)").search(s)
    remedy = regex.compile(r"(?i)\b(remed(y|ie)|serum|cleans?(e|er|ing)|care|(pro)?biotic|herbal|lotion|cream|"
                           r"gel|cure|drug|formula|recipe|regimen|solution|therapy|hydration|soap|treatment|supplement|"
                           r"diet|moist\w*|injection|potion|ingredient|aid|exercise|eat(ing)?)s?\b").search(s)
    boast = regex.compile(r"(?i)\b(most|best|simple|top|pro|real|mirac(le|ulous)|secrets?|organic|natural|perfect|"
                          r"ideal|fantastic|incredible|ultimate|important|reliable|critical|amazing|fast|good)\b|"
                          r"\b(super|hyper|advantag|benefi|effect|great|valu|eas[iy])").search(s)
    other = regex.compile(r"(?i)\b(product|thing|item|review|advi[cs]e|myth|make use|your?|really|work|tip|shop|"
                          r"store|method|expert|instant|buy|fact|consum(e|ption)|baby|male|female|men|women|grow|"
                          r"idea|suggest\w*|issue)s?\b").search(s)
    score = 4 * bool(organ) + 2 * bool(condition) + 2 * bool(goal) + 2 * bool(remedy) + bool(boast) + \
        bool(other) + capitalized
    if score >= 8:
        match_objects = [organ, condition, goal, remedy, boast, other]
        words = [match.group(0) for match in match_objects if match]
        return True, u"Health-themed spam (score {}). Keywords: *{}*".format(score, ", ".join(words).lower())
    return False, ""


# Pattern-matching product name: three keywords in a row at least once, or two in a row at least twice
@create_rule("pattern-matching product name in {}", body_summary=True, stripcodeblocks=True, answer=False,
             max_rep=4, max_score=1)
def pattern_product_name(s, site):
    required_keywords = [
        "Testo(?:sterone)?s?", "Derma?(?:pholia)?", "Garcinia", "Cambogia", "Forskolin", "Diet", "Slim", "Serum",
        "Junivive", "Gain", "Allure", "Nuvella", "Blast", "Burn", "Shark", "Peni(?:s|le)", "Pills?", "CBD",
        "Elite", "Exceptional", "Enhance(?:ment)?", "Nitro", "Suppl[ei]ments?",
        "Skin", "Muscle", "Therm[ao]", "Neuro", "Luma", "Rapid", "Tone", "Keto", "Cream",
        "(?:Anti)?[ -]?Aging", "Trim", "Male", r"Weight\W?(?:Loss|Reduction)", "Radiant(?:ly)?",
        "Boost(?:er|ing)?s?", "Youth", "Monster", "Enlarge(?:ment)", "Obat", "Nutr[ai]",
    ]
    keywords = required_keywords + [
        r"(?<=(?:keto\w*|diet)\W*)\w+(?=\W*(?:keto\w*|diet))",  # Tricky approach for "keto whatever diet"
        # r"\w+(?=-)(?=(?:\W*(?:keto\w*|diet)){2,})",  # Too dangerous
        "Deep", "Pro", "Advanced?", "Divine", "Royale?", "Angele*", "Trinity", "Andro", "Force", "Healthy?",
        "Sea", "Ascend", "Premi(?:um|er)", "Master", "Ultra", "Vital", "Perfect", "Bio", "Natural?", "Oil",
        "E?xtreme", "Fit", "Thirsty?", "Grow", "Complete", "Reviews?", "Bloom(?:ing)?", "BHB", "Pures?t?", "Quick",
        "Titan", "Hyper", "X[LRT]", "[R]X", "Supply", "Power", "Aged?", "Ultimate", "Surge", "(?<!e)Xtra",
        "Brain", "Fuel", "Melt", "Fire", "Tank",
    ]
    conjunctions = [  # lol, for "keto melt and trim"
        "And", "For", "With", "In", "This", "To", "About", "Or", "Where", "What", "Is", "A",
    ]
    if site not in {"math.stackexchange.com", "mathoverflow.net"}:
        keywords.extend([r"X\d?", "Alpha", "Plus", "Prime", "Formula", "Max+"])
    keywords = regex.compile(r"(?i)\b(?P<x>{0})(?:[ -]*(?:(?:{1})[ -]*)*(?P<x>{0}))+\b".format(
        "|".join(keywords), "|".join(conjunctions)))
    required = regex.compile(r"(?i){}".format("|".join(required_keywords)))

    match_items = list(keywords.finditer(s))
    matches = [m.captures("x") for m in match_items if required.search(m.group(0))]
    # Total "unique words in each match"
    total_words = sum([n for n in [len(set([regex.sub(r"\d", "", w) for w in m])) for m in matches] if n >= 2])
    if total_words >= 3:
        return True, FindSpam.match_infos(match_items)
    return False, ""


@create_rule("bad keyword with email in {}", stripcodeblocks=True)
def keyword_email(s, site):   # a keyword and an email in the same post
    if regex.compile("<pre>|<code>").search(s) and site == "stackoverflow.com":  # Avoid false positives on SO
        return False, ""
    keyword = regex.compile(r"(?i)(\b(?:training|we (will )?(offer|develop|provide)|sell|invest(or|ing|ment)|credit|"
                            r"money|quality|legit|interest(ed)?|guarantee|rent|crack|opportunity|fundraising|campaign|"
                            r"career|employment|candidate|loan|lover|husband|wife|marriage|illuminati|brotherhood|"
                            r"(join|contact) (me|us|him)|reach (us|him)|spell(caster)?|doctor|cancer|krebs|"
                            r"(cheat|hack)(er|ing)?|spying|passport|seaman|scam|pics|vampire|bless(ed)?|atm|miracle|"
                            r"cure|testimony|kidney|hospital|wetting)s?\b|(?<=\s)Dr\.?(?=\s)|\$ ?[0-9,.]{4}|@qq\.com|"
                            r"\b(?:герпес|муж|жена|доктор|болезн))").findall(s)
    keyword = [t[0] for t in keyword]
    email = regex.compile(r"(?<![=#/])\b[A-z0-9_.%+-]+\b(?:@|\s*\(?at\)?\s*)\b(?!(example|domain|site|foo|\dx)"
                          r"(?:\.|\s*\(?dot\)?\s*)[A-z]{2,4})\b(?:[A-z0-9_.%+-]|\s*\(?dot\)?\s*)+\b"
                          r"(?:\.|\s*\(?dot\)?\s*)[A-z]{2,4}\b").search(s)
    if keyword and email:
        return True, u"Keyword *{}* with email *{}*".format(", ".join(keyword), email.group(0))
    obfuscated_email = regex.compile(
        r"(?<![=#/])\b[A-z0-9_.%+-]+ *(?:@|\W*at\W*) *(g *mail|yahoo) *(?:\.|\W*dot\W*) *com\b").search(s)
    if obfuscated_email and not email:
        return True, u"Obfuscated email {}".format(obfuscated_email.group(0))
    return False, ""


@create_rule("pattern-matching email in {}", stripcodeblocks=True)
def pattern_email(s, site):
    pattern = regex.compile(r"(?i)(?<![=#/])\b(dr|[A-z0-9_.%+-]*"
                            r"(loan|hack|financ|fund|spell|temple|herbal|spiritual|atm|heal|priest|classes|"
                            r"investment|illuminati|vampire?))[A-z0-9_.%+-]*"
                            r"@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b"
                            ).finditer(s)
    pattern = list(pattern)
    if pattern:
        return True, FindSpam.match_infos(pattern)
    return False, ""


@create_rule("bad keyword with a link in {}", title=False, question=False)
def keyword_link(s, site):   # thanking keyword and a link in the same short answer
    if len(s) > 400:
        return False, ""
    link = regex.compile(r'(?i)<a href="https?://\S+').search(s)
    if not link or is_whitelisted_website(link.group(0)):
        return False, ""
    praise = regex.compile(r"(?i)\b(nice|good|interesting|helpful|great|amazing) (article|blog|post|information)\b|"
                           r"very useful").search(s)
    thanks = regex.compile(r"(?i)\b(appreciate|than(k|ks|x))\b").search(s)
    keyword = regex.compile(r"(?i)\b(I really appreciate|many thanks|thanks a lot|thank you (very|for)|"
                            r"than(ks|x) for (sharing|this|your)|dear forum members|(very (informative|useful)|"
                            r"stumbled upon (your|this)|wonderful|visit my) (blog|site|website))\b").search(s)
    if link and keyword:
        return True, u"Keyword *{}* with link {}".format(keyword.group(0), link.group(0))
    if link and thanks and praise:
        return True, u"Keywords *{}*, *{}* with link {}".format(thanks.group(0), praise.group(0), link.group(0))
    return False, ""


@create_rule("bad keyword in link text in {}", title=False, stripcodeblocks=True)
def bad_link_text(s, site):   # suspicious text of a hyperlink
    s = regex.sub("</?(?:strong|em)>", "", s)  # remove font tags
    keywords = regex.compile(
        r"(?isu)"
        r"\b(buy|cheap) |live[ -]?stream|"
        r"\bmake (money|\$)|"
        r"\b(porno?|(whole)?sale|coins|luxury|coupons?|essays?|in \L<city>)\b|"
        r"\b\L<city>(?:\b.{1,20}\b)?(service|escort|call girls?)|"
        r"\b(?:customer|recovery|technical|recovery)? ?(?:customer|support|service|repair|contact) "
        r"(?:phone|hotline|helpline)? ?numbers?\b|"
        r"(best|make|full|hd|software|cell|data)[\w ]{1,20}(online|service|company|repair|recovery|school|university)|"
        r"\b(writing (service|help)|essay (writing|tips))", city=city_list)
    links = regex.compile(r'nofollow(?: noreferrer)?">([^<]*)(?=</a>)', regex.UNICODE).findall(s)
    business = regex.compile(
        r"(?i)(^| )(airlines?|apple|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|"
        r"lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)($| )")

    # FIXME/TODO: Remove "help" once WebApps has stopped being hit with gmail help spam. (added: Art, 2018-10-17)
    support = regex.compile(r"(?i)(^| )(customer|care|helpline|reservation|phone|recovery|service|support|contact|"
                            r"help|tech|technical|telephone|number)($| )")
    for link_text in links:
        keywords_match = keywords.search(link_text)
        if keywords_match:
            return True, u"Bad keyword *{}* in link text".format(keywords_match.group(0).strip())
        business_match = business.search(link_text)
        support_match = support.search(link_text)
        if business_match and support_match:
            return True, u"Bad keywords *{}*, *{}* in link text".format(business_match.group(0).strip(),
                                                                        support_match.group(0).strip())
    return False, ""


@create_rule("bad pattern in URL {}", title=False, body_summary=True, stripcodeblocks=True)
def bad_pattern_in_url(s, site):
    patterns = [
        r'[^"]*-reviews?(?:-(?:canada|(?:and|or)-scam))?/?',
        r'[^"]*-support/?',
    ]
    matches = regex.compile(
        r'<a href="(?P<frag>{0})"|<a href="[^"]*"(?:\s+"[^"]*")*>(?P<frag>{0})</a>'.format(
            '|'.join(patterns)), regex.UNICODE).findall(s)
    matches = [x for x in matches if not regex.match(
        r'^https?://{0}'.format(SE_SITES_RE), x[0])]
    if matches:
        return True, u"Bad fragment in link {}".format(
            ", ".join(["".join(match) for match in matches]))
    else:
        return False, ""


def purge_cache(cachevar, limit):
    '''
    Trim down cache variable to the specified number of newest entries.
    '''
    oldest = sorted(cachevar, key=lambda k: cachevar[k]['timestamp'])[0:limit + 1]
    remaining = oldest.pop()
    now = datetime.now()
    log('debug', 'purge_cache({0}): age of oldest entry is {1}'.format(
        limit, now - cachevar[oldest[0]]['timestamp']))
    log('debug', 'purge_cache({0}): oldest remaining entry is {1}'.format(
        limit, now - cachevar[remaining]['timestamp']))
    for old in oldest:
        # Guard against KeyError; race condition?
        if old in cachevar:
            del cachevar[old]


def dns_query(label, qtype):
    global DNS_CACHE
    if (label, qtype) in DNS_CACHE:
        log('debug', 'dns_query: returning cached {0} value for {1}'.format(
            qtype, label))
        return DNS_CACHE[(label, qtype)]['result']
    try:
        starttime = datetime.now()
        answer = dns.resolver.query(label, qtype)
    except dns.exception.DNSException as exc:
        if str(exc).startswith('None of DNS query names exist:'):
            log('debug', 'DNS label {0} not found; skipping'.format(label))
        else:
            endtime = datetime.now()
            log('warning', 'DNS error {0} (duration: {1})'.format(
                exc, endtime - starttime))
        return None
    endtime = datetime.now()
    log('debug', '{0} query duration: {1}'.format(qtype, endtime - starttime))
    DNS_CACHE[(label, qtype)] = {'result': answer, 'timestamp': endtime}
    # Periodic amortized cache cleanup: clean out oldest 1000 entries
    if len(DNS_CACHE.keys()) >= 1500:
        log('debug', 'Initiating cleanup of DNS_CACHE')
        purge_cache(DNS_CACHE, 1000)
        log('debug', 'DNS cleanup took an additional {0} seconds'.format(
            datetime.now() - endtime))
    return answer


def asn_query(ip):
    '''
    http://www.team-cymru.com/IP-ASN-mapping.html
    '''
    pi = list(reversed(ip.split('.')))
    asn = dns_query('.'.join(pi + ['origin.asn.cymru.com.']), 'txt')
    if asn is not None:
        for txt in set([str(x) for x in asn]):
            log('debug', '{0}: Raw ASN lookup result: {1}'.format(ip, txt))
            if ' | ' in txt:
                return txt.split(' | ')[0].strip('"')
    return None


def ns_for_url_domain(s, site, nslist):
    if "pytest" in sys.modules:
        for nsentry in nslist:
            if isinstance(nsentry, set):
                for ns in nsentry:
                    assert ns.endswith('.'),\
                        "Missing final dot on NS entry {0}".format(ns)
            else:
                assert nsentry.endswith('.'),\
                    "Missing final dot on NS entry {0}".format(nsentry)

    domains = []
    for hostname in post_hosts(s, check_tld=True):
        domains.append(get_domain(hostname, full=True))

    for domain in set(domains):
        ns = dns_query(domain, 'ns')
        if ns is not None:
            nameservers = set([server.target.to_text() for server in ns])
            for ns_candidate in nslist:
                if (type(ns_candidate) is set and nameservers == ns_candidate) \
                    or any(ns.endswith('.{0}'.format(ns_candidate))
                           for ns in nameservers):
                    return True, '{domain} NS suspicious {ns}'.format(
                        domain=domain, ns=','.join(nameservers))
    return False, ""


@create_rule("potentially problematic NS configuration in {}", stripcodeblocks=True, body_summary=True)
def ns_is_host(s, site):
    '''
    Check if the host name in a link resolves to the same IP address
    as the IP addresses of all its name servers.
    '''
    for hostname in post_hosts(s, check_tld=True):
        host_ip = dns_query(hostname, 'a')
        if host_ip is None:
            continue
        host_ips = set([str(x) for x in host_ip])
        domain = get_domain(hostname, full=True)
        nameservers = dns_query(domain, 'ns')
        if nameservers is not None:
            ns_ips = []
            for ns in nameservers:
                this_ns_ips = dns_query(str(ns), 'a')
                if this_ns_ips is not None:
                    ns_ips.extend([str(ip) for ip in this_ns_ips])
            if set(ns_ips) == host_ips:
                return True, 'Suspicious nameservers: all IP addresses for {0} are in set {1}'.format(
                    hostname, host_ips)
    return False, ''


@create_rule("bad NS for domain in {}", body_summary=True, stripcodeblocks=True)
def bad_ns_for_url_domain(s, site):
    return ns_for_url_domain(s, site, [
        # Don't forget the trailing dot on the resolved name!
        {'ns1.md-95.bigrockservers.com.', 'ns2.md-95.bigrockservers.com.'},
        {'ns1.md-99.bigrockservers.com.', 'ns2.md-99.bigrockservers.com.'},
        {'apollo.ns.cloudflare.com.', 'liz.ns.cloudflare.com.'},
        {'ara.ns.cloudflare.com.', 'greg.ns.cloudflare.com.'},
        {'brenda.ns.cloudflare.com.', 'merlin.ns.cloudflare.com.'},
        {'chip.ns.cloudflare.com.', 'lola.ns.cloudflare.com.'},
        {'jay.ns.cloudflare.com.', 'jule.ns.cloudflare.com.'},
        {'lee.ns.cloudflare.com.', 'ulla.ns.cloudflare.com.'},
        {'lloyd.ns.cloudflare.com.', 'reza.ns.cloudflare.com.'},
        '247support-number.com.',
        'promoocodes.com.',
        'myassignmenthelp.co.uk.',
        'socialmonkee.com.',
        'aapkeaajanese.website.',
        'healthymum.org.',
        'escortdomain.net.',
        'syrahost.com.',
        'dnsdomen.com.',
        'letter.org.in.',
    ])


# This applies to all answers, and non-SO questions
@create_rule("potentially bad NS for domain in {}", body_summary=True, stripcodeblocks=True, answer=False,
             sites=["stackoverflow.com"])
@create_rule("potentially bad NS for domain in {}", body_summary=True, stripcodeblocks=True, question=False)
def watched_ns_for_url_domain(s, site):
    return ns_for_url_domain(s, site, [
        # Don't forget the trailing dot on the resolved name here either!
        # {'dns1.namecheaphosting.com.', 'dns2.namecheaphosting.com.'},
        # {'dns11.namecheaphosting.com.', 'dns12.namecheaphosting.com.'},
        'namecheaphosting.com.',  # has FPs, don't blacklist again
        # 'domaincontrol.com.',
        # {'dns1.registrar-servers.com.', 'dns2.registrar-servers.com.'},
        {'adi.ns.cloudflare.com.', 'miles.ns.cloudflare.com.'},
        {'aida.ns.cloudflare.com.', 'lloyd.ns.cloudflare.com.'},
        {'ajay.ns.cloudflare.com.', 'lia.ns.cloudflare.com.'},
        {'alex.ns.cloudflare.com.', 'lana.ns.cloudflare.com.'},
        {'anirban.ns.cloudflare.com.', 'janet.ns.cloudflare.com.'},
        {'betty.ns.cloudflare.com.', 'kai.ns.cloudflare.com.'},
        {'bonnie.ns.cloudflare.com.', 'guss.ns.cloudflare.com.'},
        {'brad.ns.cloudflare.com.', 'brenda.ns.cloudflare.com.'},
        {'brenda.ns.cloudflare.com.', 'theo.ns.cloudflare.com.'},
        {'bruce.ns.cloudflare.com.', 'chan.ns.cloudflare.com.'},
        {'chip.ns.cloudflare.com.', 'cruz.ns.cloudflare.com.'},
        {'chris.ns.cloudflare.com.', 'tess.ns.cloudflare.com.'},
        {'dana.ns.cloudflare.com.', 'piotr.ns.cloudflare.com.'},
        {'desi.ns.cloudflare.com.', 'elmo.ns.cloudflare.com.'},
        {'damon.ns.cloudflare.com.', 'naomi.ns.cloudflare.com.'},
        {'duke.ns.cloudflare.com.', 'lola.ns.cloudflare.com.'},
        {'duke.ns.cloudflare.com.', 'wally.ns.cloudflare.com.'},
        {'elinore.ns.cloudflare.com.', 'sam.ns.cloudflare.com.'},
        {'elliot.ns.cloudflare.com.', 'sue.ns.cloudflare.com.'},
        {'elsa.ns.cloudflare.com.', 'theo.ns.cloudflare.com.'},
        {'ernest.ns.cloudflare.com.', 'pat.ns.cloudflare.com.'},
        {'eva.ns.cloudflare.com.', 'hank.ns.cloudflare.com.'},
        {'gina.ns.cloudflare.com.', 'rudy.ns.cloudflare.com.'},
        {'glen.ns.cloudflare.com.', 'jean.ns.cloudflare.com.'},
        {'greg.ns.cloudflare.com.', 'kia.ns.cloudflare.com.'},
        {'greg.ns.cloudflare.com.', 'mary.ns.cloudflare.com.'},
        {'isla.ns.cloudflare.com.', 'jeremy.ns.cloudflare.com.'},
        {'jake.ns.cloudflare.com.', 'sofia.ns.cloudflare.com.'},
        {'jean.ns.cloudflare.com.', 'piotr.ns.cloudflare.com.'},
        {'jim.ns.cloudflare.com.', 'nadia.ns.cloudflare.com.'},
        {'kia.ns.cloudflare.com.', 'noah.cs.cloudflare.com.'},
        {'laura.ns.cloudflare.com.', 'terin.ns.cloudflare.com.'},
        {'mark.ns.cloudflare.com.', 'wanda.ns.cloudflare.com.'},
        {'meg.ns.cloudflare.com.', 'theo.ns.cloudflare.com.'},
        {'naomi.ns.cloudflare.com.', 'tim.ns.cloudflare.com.'},
        {'norm.ns.cloudflare.com.', 'olga.ns.cloudflare.com.'},
        {'olga.ns.cloudflare.com.', 'seth.ns.cloudflare.com.'},
        {'pablo.ns.cloudflare.com.', 'pola.ns.cloudflare.com.'},
        {'sara.ns.cloudflare.com.', 'theo.ns.cloudflare.com.'},
        {'stan.ns.cloudflare.com.', 'vera.ns.cloudflare.com.'},
        'mihanwebhost.com.',  # FPs, don't blacklist
        'offshoreracks.com.',
        'sathyats.net.',
        'shared-host.org.',
        'web.com.ph.',
        {'ns09.domaincontrol.com.', 'ns10.domaincontrol.com.'},  # FPs, don't blacklist
        {'ns43.domaincontrol.com.', 'ns44.domaincontrol.com.'},  # FPs, don't blacklist
        {'ns57.domaincontrol.com.', 'ns58.domaincontrol.com.'},
        {'ns59.domaincontrol.com.', 'ns60.domaincontrol.com.'},
        'supercloudapps.com.',
        'vultr.com.',  # has FPs, don't move to blacklist
        'directory92.com.',
        'offshoric.com.',
        'freehostia.com.',
        'hawkhost.com.',  # has FPs, don't move to blacklist
        'greengeeks.com.',
        'supportaus.com.',
        'utecho.com.',
        '256gbserver.com.',
        'solutionsinfini.org.',
        'ownmyserver.com.',
        'websitewelcome.com.',
        'fatcow.com.',
        'vedigitize.us.',
        'serverpars.com.',
        'namedc.com.',
        'wixdns.net.',
        'a2hosting.com.',
        'md-in-20.webhostbox.net.',
        'md-in-51.webhostbox.net.',
        'cybercastco.com.',
        'web4africa.com.',
        'puredownloads.website.',
        'hostblast.net.',
        'webhouse.sk.',
        'guzelhosting.com.',
        'solidhosting.pro.',
        'justhost.com.',
        'stupidblogger.com.',
        'orangewebsite.com.',
        'omnilinks.net.',
        'servconfig.com.',
        'siteground.biz.',
        'cetpainfotech.com.',
        'sttdns.com.',
        'hover.com.',
        'stechsky.com.',
        'loopbyte.com.',
        'sgp61.siteground.asia.',
        'dynamicnetips.com.',
        'w3softech.com.',
        'blockchainhelp.pro.',
        'specializedtest.com.',
        'macsol.co.in.',
        'inmotionhosting.com.',
        'myhostindia.com.',
        'lfmserver.com.',
        'symbolhostpremiumdns.com.',
        'hostgator.in.',
        'hostspicy.com.',
    ])


def ip_for_url_host(s, site, ip_list):
    # ######## FIXME: code duplication
    for hostname in post_hosts(s, check_tld=True):
        a = dns_query(hostname, 'a')
        if a is not None:
            # ######## TODO: allow blocking of IP ranges with regex or CIDR
            for addr in set([str(x) for x in a]):
                log('debug', 'IP: IP {0} for hostname {1}'.format(
                    addr, hostname))
                if addr in ip_list:
                    return True, '{0} suspicious IP address {1}'.format(
                        hostname, addr)
    return False, ""


@create_rule("potentially bad IP for hostname in {}",
             stripcodeblocks=True, body_summary=True)
def watched_ip_for_url_hostname(s, site):
    return ip_for_url_host(
        s, site,
        # Watched IP list
        [
            # AS 8560 ONEANDONE-AS Brauerstrasse 48, DE
            '62.151.180.33',    # visit-my-website ltssecure.com / ltssoc
            # AS 15169 GOOGLE - Google LLC, US
            '23.236.62.147',    # googleusercontent.com lots of hits
            # AS 20068 - HAWKHOST - Hawk Host Inc., CA.
            '172.96.187.196',   # fake-tech-support driver-canon.com
            '198.252.105.94',   # fake-tech-support asia-canon.com etc
            # AS 22612 NAMECHEAP-NET
            '68.65.122.36',     # drugs reviewscart.co.uk / purefitketopills.com
            '104.219.248.45',   # drugs 360nutra / timesnutrition etc
            '104.219.248.81',   # drugs supplement4world / supplementgod etc
            '162.213.255.36',   # drugs / visit-my-website / cryptocurrency
            '198.54.115.65',    # drugs goldencondor / visit4supplements etc
            '198.54.116.51',    # drugs reviewsgear / crazy-bulk-review etc
            '198.54.116.85',    # drugs mummydiet.org
            '198.54.126.109',   # escorts + buy-likes
            # AS 26496 AS-26496-GO-DADDY-COM-LLC
            '23.229.180.169',   # drugs health4supplement / supplements4lifetime etc
            '23.229.217.167',   # drugs popsupplement / daddysupplement etc
            '23.229.233.231',   # drugs ultavivegarcinia.es / refollium.in etc
            '107.180.3.93',     # drugs amazonhealthstore / click2fitness etc
            '107.180.24.240',   # drugs deal2supplement / first2order etc
            '107.180.34.212',   # fake-tech-support 123helpline / allitexpert
            '107.180.40.103',   # drugs + seo getbestdelight / seotipandsolution
            '107.180.47.58',    # drugs + travel
            '107.180.59.131',   # drugs kingofsupplement.com
            '148.72.211.163',   # hostingride.in
            '160.153.129.38',   # drugs supplementswellness / buyketodiet etc
            '160.153.129.238',  # drugs bestenhancement / supplementskingpro etc
            '166.62.6.66',      # fake-tech-support + hosting ms-officesetup etc
            '166.62.28.116',    # fake-tech-support printertechsupportnumbers.com
            '192.186.227.225',  # drugs topwellnessguru / healthcare350 etc
            # AS 55293 A2HOSTING - A2 Hosting, Inc., US
            '162.254.252.93',   # paper-writing etc appsocio doneessays etc
            # AS 394695 PUBLIC-DOMAIN-REGISTRY - PDR, US
            '103.21.58.29',     # software-development infinigic / apporio.com
            '116.206.104.141',  # fake-tech-support fake-diplomas
            '162.215.253.205',  # drugs escorts drozien.com nehasuri.in etc
        ])


@create_rule("bad IP for hostname in {}",
             stripcodeblocks=True, body_summary=True)
def bad_ip_for_url_hostname(s, site):
    return ip_for_url_host(
        s, site,
        # Blacklisted IP list
        [
            # AS 22612 NAMECHEAP-NET
            '198.54.116.110',   # drugs epbhub / healtylifetimesupplement etc
            '198.54.120.134',   # drugs advisorwellness / health4supplement etc
            # AS 24940 HETZNER-AS, DE
            '138.201.185.58',   # idea-soft.ir / sitecode.ir / npco.net
            # AS 26347 DREAMHOST-AS
            '75.119.210.224',  # triplet-spam
            # AS 26496 AS-26496-GO-DADDY-COM-LLC
            '104.25.50.105',   # crbtech.in
            '107.180.78.164',  # gs-jj.com
            '160.153.75.129',  # itunessupport.org
            # AS 32475 - SINGLEHOP-LLC - SingleHop LLC, US
            '172.96.187.196'   # fake-tech-support canonfreedownload etc
        ])


def asn_for_url_host(s, site, asn_list):
    for hostname in post_hosts(s, check_tld=True):
        if any(hostname == x or hostname.endswith("." + x) for x in ASN_WHITELISTED_WEBSITES):
            log('debug', 'Skipping ASN check for hostname {0}'.format(
                hostname))
            continue
        a = dns_query(hostname, 'a')
        if a is not None:
            for addr in set([str(x) for x in a]):
                log('debug', 'ASN: IP {0} for hostname {1}'.format(
                    addr, hostname))
                asn = asn_query(addr)
                if asn in asn_list:
                    return True, '{0} address {1} in ASN {2}'.format(
                        hostname, addr, asn)
    return False, ""


@create_rule("potentially bad ASN for hostname in {}", body_summary=True, stripcodeblocks=True)
def watched_asn_for_url_hostname(s, site):
    return asn_for_url_host(
        s, site,
        # Watched ASN list
        [
            '3842',    # RAMNODE - RamNode LLC, US
            '3595',    # GNAXNET-AS - zColo, US
            '12488',   # KRYSTAL, GR
            # '16509', # FPs do not watch -- AMAZON-02 - Amazon.com, Inc., US
            '18229',   # CTRLS-AS-IN CtrlS Datacenters Ltd., IN
            '19318',   # IS-AS-1 - Interserver, Inc, US
            '19969',   # JOESDATACENTER - Joe_s Datacenter, LLC, US.
            # '20013'  # FPs do not watch -- CYRUSONE - CyrusOne LLC, US
            # '22612', # Moderate FPs, don't double up -- NAMECHEAP-NET - Namecheap, Inc., US
            # '26496', # Massive FPs do not watch -- AS-26496-GO-DADDY-COM-LLC - GoDaddy.com, LLC, US
            '24778',   # DATAPIPE-UK, GB
            '29073',   # QUASINETWORKS, NL
            '31083',   # TELEPOINT, BG.
            '31863',   # DACEN-2 - Centrilogic, Inc., US
            '32244',   # LIQUIDWEB - Liquid Web, L.L.C, US
            '34119',   # WILDCARD-AS Wildcard UK Limited, GB
            '36024',   # AS-TIERP-36024 - TierPoint, LLC, US
            '36351',   # SOFTLAYER - SoftLayer Technologies Inc., US
            '36352',   # AS-COLOCROSSING - ColoCrossing, US
            '40676',   # AS40676 - Psychz Networks, US
            '42831',   # UKSERVERS-AS UK Dedicated Servers, Hosting and Co-Location, GB
            '43317',   # FISHNET-AS, RU
            '45839',   # SHINJIRU-MY-AS-AP Shinjiru Technology Sdn Bhd, MY
            '46261',   # QUICKPACKET - QuickPacket, LLC, US
            '46844',   # ST-BGP - Sharktech, US
            '47583',   # AS-HOSTINGER, LT
            '49335',   # NCONNECT-AS, RU
            '50673',   # SERVERIUS-AS, NL
            '55002',   # DEFENSE-NET - Defense.Net, Inc, US.
            '54290',   # HOSTWINDS - Hostwinds LLC., US
            '62731',   # 247RACK-COM - 247RACK.com, US
            '133711',  # HBSGZB-AS Home Broadband Services LLP, IN
            '197695',  # AS-REG, RU
            '200000',  # UKRAINE-AS, UA
            '393960',  # HOST4GEEKS-LLC - Host4Geeks LLC, US
            '206349',  # BLUEANGELHOST, BG.
            '395970',  # IONSWITCH - IonSwitch, LLC, US
        ])


@create_rule("offensive {} detected", body_summary=True, max_rep=101, max_score=2, stripcodeblocks=True)
def is_offensive_post(s, site):
    if not s:
        return False, ""

    offensive = regex.compile(
        r"(?is)\b((?:ur\Wm[ou]m|(yo)?u suck|[8B]={3,}[D>)]\s*[.~]*|nigg[aeu][rh]?|(ass\W?|a|a-)hole|"
        r"daf[au][qk]|(?<!brain)(mother|mutha)?f\W*u\W*c?\W*k+(a|ing?|e?[rd]| *off+| *(you|ye|u)(rself)?|"
        r" u+|tard)?|(bul+)?shit(t?er|head)?|(yo)?u(r|'?re)? (gay|scum)|dickhead|(?:fur)?fa+g+(?:ot)?s?\b|"
        r"pedo(?!bapt|dont|log|mete?r|troph)|cocksuck(e?[rd])?|"
        r"whore|cunt|jerk(ing)?\W?off|cumm(y|ie)|butthurt|queef|lesbo|"
        r"bitche?|(eat|suck|throbbing|sw[oe]ll(en|ing)?)\b.{0,20}\b(cock|dick)|dee[sz]e? nut[sz]|"
        r"dumb\W?ass|wet\W?puss(y|ie)?|slut+y?|shot\W?my\W?(hot\W?)?load)s?)\b")
    matches = list(offensive.finditer(s))
    len_of_match = 0
    text_matched = []
    for match in matches:
        len_of_match += match.end() - match.start()
        text_matched.append(match.group(0))

    if len_of_match / len(s) >= 0.015:  # currently at 1.5%, this can change if it needs to
        return True, FindSpam.match_infos(matches)
    return False, ""


@create_rule("username similar to website in {}", title=False, body_summary=True, question=False, whole_post=True)
def username_similar_website(post):
    s, username = post.body, post.user_name
    sim_ratio, sim_webs = perform_similarity_checks(s, username)
    if sim_ratio >= SIMILAR_THRESHOLD:
        return False, False, True, "Username `{}` similar to {}, ratio={}".format(
            username,
            ', '.join(['*{}* at position {}-{}'.format(w, s.index(w), s.index(w) + len(w)) for w in sim_webs]),
            sim_ratio)
    else:
        return False, False, False, ""


@create_rule("single character over used in post", max_rep=20, body_summary=True,
             all=False, sites=["judaism.stackexchange.com"])
def character_utilization_ratio(s, site):
    s = strip_urls_and_tags(s)
    counter = Counter(s)
    total_chars = len(s)
    highest_ratio = 0.0
    highest_char = ""

    for key, value in counter.items():
        char_ratio = value / float(total_chars)
        # key, value, char_ratio
        if char_ratio > highest_ratio:
            highest_ratio = char_ratio
            highest_char = key

    if highest_ratio > CHARACTER_USE_RATIO:
        return True, "The `{}` character appears in a high percentage of the post".format(highest_char)
    else:
        return False, ""


def post_links(post):
    """
    Helper function to extract URLs from a piece of HTML.
    """
    global LINK_CACHE

    if post in LINK_CACHE:
        log('debug', 'Returning cached links for post')
        return LINK_CACHE[post]['links']

    # Fix stupid spammer tricks
    edited_post = post
    for p in COMMON_MALFORMED_PROTOCOLS:
        edited_post = edited_post.replace(p[0], p[1])

    links = []
    for l in regex.findall(URL_REGEX, edited_post):
        if l[-1].isalnum():
            links.append(l)
        else:
            links.append(l[:-1])

    if len(LINK_CACHE.keys()) >= 15:
        log('debug', 'Trimming LINK_CACHE down to 5 entries')
        purge_cache(LINK_CACHE, 10)
        log('debug', 'LINK_CACHE purged')

    linkset = set(links)
    LINK_CACHE[post] = {'links': linkset, 'timestamp': datetime.now()}
    return linkset


def post_hosts(post, check_tld=False):
    '''
    Return list of hostnames from the post_links() output.

    With check_tld=True, check if the links have valid TLDs; abandon and
    return an empty result if too many don't (limit is currently hardcoded
    at 3 invalid links).

    Augment LINK_CACHE with parsed hostnames.
    '''
    global LINK_CACHE

    if post in LINK_CACHE and 'hosts' in LINK_CACHE[post]:
        return LINK_CACHE[post]['hosts']

    invalid_tld_count = 0
    hostnames = []
    for link in post_links(post):
        hostname = urlparse(link).hostname
        if hostname is None:
            hostname = urlparse('http://' + link).hostname
        if '.'.join(hostname.lower().split('.')[-2:]) in SE_SITES_DOMAINS:
            log('debug', 'Skipping {0}'.format(hostname))
            continue

        if check_tld:
            if not tld.get_tld(hostname, fix_protocol=True, fail_silently=True):
                log('debug', '{0} has no valid tld; skipping'.format(hostname))
                invalid_tld_count += 1
                if invalid_tld_count > 3:
                    log('debug', 'post_hosts: too many invalid TLDs; abandoning post')
                    hostnames = []
                    break
                continue

        hostnames.append(hostname)

    hostset = set(hostnames)
    LINK_CACHE[post]['hosts'] = hostset
    return hostset


# noinspection PyMissingTypeHints
def perform_similarity_checks(post, name):
    """
    Performs 4 tests to determine similarity between links in the post and the user name
    :param post: Test of the post
    :param name: Username to compare against
    :return: Float ratio of similarity
    """
    max_similarity, similar_links = 0.0, []

    # Keep checking links until one is deemed "similar"
    for link in post_links(post):
        domain = get_domain(link)

        # Straight comparison
        s1 = similar_ratio(domain, name)
        # Strip all spaces
        s2 = similar_ratio(domain, name.replace(" ", ""))
        # Strip all hyphens
        s3 = similar_ratio(domain.replace("-", ""), name.replace("-", ""))
        # Strip all hyphens and all spaces
        s4 = similar_ratio(domain.replace("-", "").replace(" ", ""), name.replace("-", "").replace(" ", ""))

        similarity = max(s1, s2, s3, s4)
        max_similarity = max(max_similarity, similarity)
        if similarity >= SIMILAR_THRESHOLD:
            similar_links.append(domain)

    return max_similarity, similar_links


# noinspection PyMissingTypeHints
def similar_ratio(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# noinspection PyMissingTypeHints
def get_domain(s, full=False):
    """
    Extract the domain name; with full=True, keep the TLD tacked on.
    """
    try:
        extract = tld.get_tld(s, fix_protocol=True, as_object=True, )
        if full:
            domain = extract.fld
        else:
            domain = extract.domain
    except TldDomainNotFound as e:
        invalid_tld = RE_COMPILE.match(str(e)).group(1)
        # Attempt to replace the invalid protocol
        s1 = s.replace(invalid_tld, 'http', 1)
        try:
            extract = tld.get_tld(s1, fix_protocol=True, as_object=True, )
            if full:
                domain = extract.fld
            else:
                domain = extract.domain
        except TldDomainNotFound:
            # Assume bad TLD and try one last fall back, just strip the trailing TLD and leading subdomain
            parsed_uri = urlparse(s)
            if len(parsed_uri.path.split(".")) >= 3:
                if full:
                    domain = '.'.join(parsed_uri.path.split(".")[1:])
                else:
                    domain = parsed_uri.path.split(".")[1]
            else:
                if full:
                    domain = parsed_uri.path
                else:
                    domain = parsed_uri.path.split(".")[0]
    return domain


# create_rule("answer similar to existing answer on post", whole_post=True, max_rep=50
#             all=True, sites=["codegolf.stackexchange.com"])
def similar_answer(post):
    if not post.parent:
        return False, False, False, ""

    question = post.parent
    sanitized_body = strip_urls_and_tags(post.body)

    for other_answer in question.answers:
        if other_answer.post_id != post.post_id:
            sanitized_answer = strip_urls_and_tags(other_answer.body)
            ratio = similar_ratio(sanitized_body, sanitized_answer)

            if ratio >= SIMILAR_ANSWER_THRESHOLD:
                return False, False, True, \
                    u"Answer similar to answer {}, ratio {}".format(other_answer.post_id, ratio)

    return False, False, False, ""


# noinspection PyMissingTypeHints
def strip_urls_and_tags(s):
    return URL_REGEX.sub("", TAG_REGEX.sub("", s))


@create_rule("mostly dots in {}", max_rep=50, sites=["codegolf.stackexchange.com"])
def mostly_dots(s, site):
    if not s:
        return False, ""

    # Strip code blocks here rather than with `stripcodeblocks` so we get the length of the whole post
    body = regex.sub(r"(?s)<pre([\w=\" -]*)?>.*?</pre>", "", s)
    body = regex.sub(r"(?s)<code>.*?</code>", "", body)

    body = TAG_REGEX.sub("", body)

    s = TAG_REGEX.sub("", s)
    if not s:
        return False, ""

    dot_count = body.count(".")
    if dot_count / len(s) >= 0.4:
        return True, u"Post contains {} dots out of {} characters".format(dot_count, len(s))
    else:
        return False, ""


@create_rule("mostly punctuation marks in {}",
             sites=["math.stackexchange.com", "mathoverflow.net"])
def mostly_punctuations(s, site):
    body = regex.sub(r"(?s)<pre([\w=\" -]*)?>.*?</pre>", "", s)
    body = regex.sub(r"(?s)<code>.*?</code>", "", body)
    body = strip_urls_and_tags(body)
    s = strip_urls_and_tags(s)
    if len(s) < 15:
        return False, ""

    punct_re = regex.compile(r"[[:punct:]]")
    all_punc = punct_re.findall(body.replace(".", ""))
    if not all_punc:
        return False, ""

    all_punc_set = list(set(all_punc))  # Remove duplicate
    all_counts = [all_punc.count(punc) for punc in all_punc_set]
    count = max(all_counts)
    frequency = count / len(s)
    max_punc = all_punc_set[all_counts.index(count)]

    if frequency >= PUNCTUATION_RATIO:
        return True, u"Post contains {} marks of {!r} out of {} characters".format(count, max_punc, len(s))
    else:
        return False, ""


# TODO: split this function into two
def no_whitespace(s, site, body=True):
    if (not body) and regex.compile(r"(?is)^[0-9a-z]{20,}\s*$").match(s):
        return True, "No whitespace or formatting in title"
    elif body and regex.compile(r"(?is)^<p>[0-9a-z]+</p>\s*$").match(s):
        return True, "No whitespace or formatting in body"
    return False, ""


@create_rule("no whitespace in {}", body=False, max_rep=10000, max_score=10000)
def no_whitespace_title(s, site):
    return no_whitespace(s, site, body=False)


@create_rule("no whitespace in {}", title=False, max_rep=10000, max_score=10000)
def no_whitespace_body(s, site):
    return no_whitespace(s, site, body=True)


def toxic_check(post):
    s = strip_urls_and_tags(post.body)[:3000]

    if not s:
        return False, False, False, ""

    try:
        response = requests.post(PERSPECTIVE, json={
            "comment": {
                "text": s
            },

            "requestedAttributes": {
                "TOXICITY": {
                    "scoreType": "PROBABILITY"
                }
            }
        }).json()
    except (requests.exceptions.ConnectionError, ValueError):
        return False, False, False, ""

    if "error" in response:
        err_msg = response["error"]["message"]

        if not err_msg.startswith("Attribute TOXICITY does not support request languages:"):
            log("debug", "Perspective error: {} for string {} (original body {})".format(err_msg, s, post.body))
    else:
        probability = response["attributeScores"]["TOXICITY"]["summaryScore"]["value"]

        if probability > PERSPECTIVE_THRESHOLD:
            return False, False, True, "Perspective scored {}".format(probability)

    return False, False, False, ""


if GlobalVars.perspective_key:  # don't bother if we don't have a key, since it's expensive
    toxic_check = create_rule("toxic {} detected", func=toxic_check, whole_post=True, max_rep=101, max_score=2)


@create_rule("body starts with title and ends in URL", whole_post=True, answer=False,
             sites=["codegolf.stackexchange.com"])
def body_starts_with_title(post):
    t = post.title.strip().replace(" ", "")

    # Safeguard for answers, should never hit
    if post.is_answer or len(t) <= 10:
        log('warning', "Length of post title is 10 characters or less. This is highly abnormal")
        return False, False, False, ""

    end_in_url, ending_url = link_at_end(post.body, None)
    if not end_in_url:
        # Experimental: Body *starts* with URL
        match = regex.search(r'^<p><a href="([^"]*)"', post.body)
        if not match or match:  # Disable for now
            return False, False, False, ""
        ending_url = match.group(1)
    else:
        ending_url = ending_url.replace("Link at end: ", "")

    if regex.compile(r"</?(?:pre|code)>").search(post.body):
        return False, False, False, ""

    s = strip_urls_and_tags(post.body).replace(" ", "").replace("\n", "")
    if similar_ratio(s[:len(t)], t) >= BODY_TITLE_SIMILAR_RATIO:
        return False, False, True, "Body starts with title and ends in URL: " + ending_url

    # Strip links and link text
    s = regex.sub(r"<a[^>]+>[^<>]*</a>", "", regex.sub(r">>+", "", post.body))
    s = strip_urls_and_tags(s).replace(" ", "").replace("\n", "")
    if similar_ratio(s[:len(t)], t) >= BODY_TITLE_SIMILAR_RATIO:
        return False, False, True, "Body starts with title and ends in URL: " + ending_url

    # Final check: Body contains title verbatim
    if t in strip_urls_and_tags(post.body).replace(" ", "").replace("\n", "") \
            or t in post.body:
        return False, False, True, "Body contains title and ends in URL: " + ending_url
    return False, False, False, ""


@create_rule("luncheon meat detected", title=False, max_rep=21,
             all=False, sites=["stackoverflow.com"])
def luncheon_meat(s, site):  # Random "signature" like asdfghjkl
    s = regex.search(r"<p>\s*?(\S{8,})\s*?</p>$", s.lower())

    if not s:
        return False, ""

    has_letter = regex.search(r"[A-Za-z]", s[1])
    if not has_letter:
        return False, ""

    p1 = ENGLISH_PRIOR
    p2 = UNIFORM_PRIOR

    for symbol in s[1]:
        if symbol in ENGLISH:
            p1 += ENGLISH[symbol]
            p2 += UNIFORM

    return p2 > p1, "match: {}, p1: {}, p2: {}".format(s[1], p1, p2)


@create_rule("himalayan pink salt detected", whole_post=True, disabled=True)
def turkey2(post):
    if regex.search("([01]{8}|zoe)", post.body):
        pingable = chatcommunicate._clients["stackexchange.com"].get_room(11540).get_pingable_user_names()

        if not pingable or not isinstance(pingable, list):
            return False, False, False, ""

        if post.user_name in pingable:
            return False, False, True, "Himalayan pink salt detected"

    return False, False, False, ""


# FLEE WHILE YOU STILL CAN.
@create_rule("offensive {} detected", all=False, stripcodeblocks=True, max_rep=101, max_score=1,
             sites=["hindiusm.stackexchange.com", "islam.stackexchange.com",
                    "judaism.stackexchange.com", "medicalsciences.stackexchange.com"])
def religion_troll(s, site):
    regexes = [
        r'(?:(?:Rubellite\W*(?:Fae|Yaksi)|Sarvabhouma|Rohit|Anisha|Ahmed\W*Bkhaty|Anubhav\W*Jha|Vineet\W*Aggarwal|Josh'
        r'\W*K|Doniel\W*F|mbloch)(?:|\b.{1,200}?\b)(?:(?:mother)?[sf]uck|pis+|pus+(?:y|ies)|boo+b|tit|coc*k|dick|ass'
        r'(?:hole|lick)?|penis|phallus|vagina|cunt(?:bag)?|genital|rectum|dog+ystyle|blowjob|scum(?:bag)|bitch|bastard'
        r'|slut+(?:ish|y)?|harlot|whore|bloody|rotten|diseased|swelling|lesbian|queer|(?:homo|trans|bi)(?:sexual)?|'
        r'retard|jew(?:ish)?|nig+er|nic+a|fag(?:g?[eio]t)?|heretic|idiot|sinners|raghead|muslim|hindu)(?:(?:ing|e[dr]'
        r'|e?)[sz]?)?|(?:(?:mother)?[sf]uck|pis+|pus+(?:y|ies)|boo+b|tit|coc*k|dick|ass(?:hole|lick)?|penis|phallus|'
        r'vagina|cunt(?:bag)?|genital|rectum|dog+ystyle|blowjob|scum(?:bag)|bitch|bastard|slut+(?:ish|y)?|harlot|whore'
        r'|bloody|rotten|diseased|swelling|lesbian|queer|(?:homo|trans|bi)(?:sexual)?|retard|jew(?:ish)?|nig+er|nic+a|'
        r'fag(?:g?[eio]t)?|heretic|idiot|sinners|raghead|muslim|hindu)(?:(?:ing|e[dr]|e?)[sz]?)?(?:|\b.{1,200}?\b)'
        r'(?:Rubellite\W*(?:Fae|Yaksi)|Sarvabhouma|Rohit|Anisha|Ahmed\W*Bkhaty|Anubhav\W*Jha|Vineet\W*Aggarwal|Josh'
        r'\W*K|Doniel\W*F|mbloch))',

        r'(?:[hl]indu(?:s|ism)?|jew(?:s|ish)?|juda(?:ic|ism)|kike)(?:\W*(?:(?:chew|kiss|bunch|are|is|n|it|is|and|of|an?'
        r'|the|greedy|bag|with|jewdaism)\W*)*(?:(?:worse\W*than(?:(?:\W*and)?\W*(?:aids|cancer|tuberculosis|syphilis|'
        r'tumor|internal\W*bleeding)+)+)|(?:damned|going)\W*to\W*(?:rot\W*in\W*)?hell|stinking|filthy|dirty|bloody|'
        r'(?:saggy)?\W*ass\W*?(?:hole|licker|e)?s?|w?hores?|bitch(?:es)?|idiots?|gandus?|homo(?:sexual)?s?|(?:fag|mag)'
        r'(?:g?[eio]t)?s?|morons?|(circumcised\W*)?bastards?|jhandus?|(?:mother\W*?)?fuck(?:s|ing|ers)?|sucks?|'
        r'cockroach(?:es)?|excreta|need\W*to\W*be\W*(?:exterminated|castrated)|puss(?:y|ies)(?:\W*licking)|hairy|'
        r'rotten|cock\W*(?:slurping|suck(?:ers?|ing)?)|blood\W*?suck(?:ing|ers?)|parasites?|swines?(?:\W*piss)?|'
        r'(?:scum|cunt)\W*bags?|rotten|corpses|slurping|mutilated\W*genitals?|whoremonger|rodents?|pests?|demonic|evil|'
        r'uncivilized|barbaric|racist|satanic|savage|dead\W*swines)+)+',

        r'(?:(?:stupid|bloody|gandus?|lindus?|w?hore(?:monger(?:s|ing)|s)?|impotent|dumb|(?:mother\W*?)?fuck(?:ing|ers)'
        r'?|assholes?(?:\W*?of\W*?)?|bitch(?:es)?|dirty|stinking|filthy|blood\W*?(?:thirsty|sucking)|racist|dumb|pussy)'
        r'\W*?(?:and|is|you|flesh|of|a)*\W*?)+(?:[hl]indu(?:s|ism)?|jew(?:s|ish)?|juda(?:ism|ic)|kike)',

        r'rama?\W*?(?:(?:was|is|a|an)\W*?)*\W*?(?:bastard|impotent|asshole|(?:mother\W*?)?fuck(?:ing|ers|s)|'
        r'(?:fag|mag)(?:g?[eio]t)?s?)+',

        r'(?:\b|\w*)(?:o(?:[^A-Za-z]|&#?\w+;)*)(?:d(?:[^A-Za-z]|&#?\w+;)*)(?:u(?:[^A-Za-z]|&#?\w+;)*)(?:d(?:[^A-Za-z]|'
        r'&#?\w+;)*)(?:u(?:[^A-Za-z]|&#?\w+;)*)(?:w(?:[^A-Za-z]|&#?\w+;)*)(?:a(?:[^A-Za-z]|&#?\w+;)*)\w*(?:\b|\w*)'
    ]
    offensive = any(regex.search(x, s) for x in regexes)
    return offensive, 'Potential religion site troll post' if offensive else ''


# TODO: migrate this old stub
bad_keywords_nwb = [  # "nwb" == "no word boundary"
    u"ಌ", "vashi?k[ae]r[ae]n", "garcinia", "cambogia", "forskolin", r"cbd\W?oil",
    "(eye|skin|aging) ?cream", "b ?a ?m ?(?:w ?o ?w|w ?a ?r)", "cogniq",
    r"male\Wperf(?!ormer)", "anti[- ]?aging", "(ultra|berry|body)[ -]?ketone",
    "(cogni|oro)[ -]?(lift|plex)",
    "(skin|face|eye)[- ]?(serum|therapy|hydration|tip|renewal|gel|lotion|cream)",
    r"\bnutra(?!l(?:|y|ity|i[sz]ing|i[sz]ed?)s?\b)",
    r"contact (me|us)\W*<a ", "ecoflex",
    r"\brsgold",
    "packers.{0,15}(movers|logistic)(?:.{0,25}</a>)",
    "(brain|breast|male|penile|penis)[- ]?(enhance|enlarge|improve|boost|plus|peak)(?:ment)?",
    " %[au]h ", "tapsi ?sarkar",
    "(?:networking|cisco|sas|hadoop|mapreduce|oracle|dba|php|sql|javascript|js|java|designing|marketing|"
    "salesforce|joomla)( certification)? (courses?|training)(?=.{0,25}</a>)",
    r"(?:design|development|compan(?:y|ies)|expert|institute|classes|schools?|training|courses?|jobs?"
    r"|automation|sex|services?|kindergarten)"
    r"\W*(?:center|centre|institute|work|provider)?"
    r"(?:\b.{1,8}\b)?\L<city>\b",
    r"\b\L<city>(\b.{1,8}\b)?(?:tour)",  # TODO: Populate this "after city" keyword list
    u"Ｃ[Ｏ0]Ｍ", "sunergetic", "capilux",
    r"ICQ#?\d{4}-?\d{5}", "viarex",
    r"b\W?o\W?j\W?i\W?t\W?e\W?r",
    "(?:🐽|🐷){3,}",
]

# Patterns: the top four lines are the most straightforward, matching any site with this string in domain name
pattern_websites = [
    r"(enstella|recoverysoftware|removevirus|support(number|help|quickbooks)|techhelp|calltech|exclusive|"
    r"onlineshop|video(course|classes|tutorial(?!s))|vipmodel|(?<!word)porn|wholesale|inboxmachine|(get|buy)cheap|"
    r"escort|diploma|(govt|government)jobs|extramoney|earnathome|spell(caster|specialist)|profits|"
    r"seo-?(tool|service|trick|market)|onsale|fat(burn|loss)|(\.|//|best)cheap|online-?(training|solution)"
    r"|\bbabasupport\b|movieshook|where\w*to\w*buy)"
    r"[\w-]*\.(com?|net|org|in(\W|fo)|us|ir|wordpress|blogspot|tumblr|webs(?=\.)|info)",
    r"(replica(?!t)|rs\d?gold|rssong|runescapegold|maxgain|e-cash|mothers?day|phone-?number|fullmovie|tvstream|"
    r"trainingin|dissertation|(placement|research)-?(paper|statement|essay)|digitalmarketing|infocampus|freetrial|"
    r"cracked\w{3}|bestmover|relocation|\w{4}mortgage|revenue|testo[-bsx]|cleanse|cleansing|detox|suppl[ei]ment|"
    r"loan|herbal|serum|lift(eye|skin)|(skin|eye)lift|luma(genex|lift)|renuva|svelme|santeavis|wrinkle|topcare)"
    r"[\w-]*\.(com?|net|org|in(\W|fo)|us|ir|wordpress|blogspot|tumblr|webs(?=\.)|info)",
    r"(drivingschool|crack-?serial|serial-?(key|crack)|freecrack|appsfor(pc|mac)|probiotic|remedies|heathcare|"
    r"sideeffect|meatspin|packers\S{0,3}movers|(buy|sell)\S{0,12}cvv|goatse|burnfat|gronkaffe|muskel|"
    r"tes(tos)?terone|nitric(storm|oxide)|masculin|menhealth|intohealth|babaji|spellcaster|potentbody|slimbody|"
    r"slimatrex|moist|lefair|derma(?![nt])|xtrm|factorx|(?<!app)nitro(?!us)|endorev|ketone)"
    r"[\w-]*\.(com?|net|org|in(\W|fo)|us|ir|wordpress|blogspot|tumblr|webs(?=\.)|info)",
    r"(moving|\w{10}spell|[\w-]{3}password|(?!greatfurniture)\w{5}deal|(?!nfood)\w{5}facts|\w\dfacts|\Btoyshop|"
    r"[\w-]{5}cheats|"
    r"(?!djangogirls\.org(?:$|[/?]))[\w-]{6}girls|"
    r"clothing|shoes(inc)?|cheatcode|cracks|credits|-wallet|refunds|truo?ng|viet|"
    r"trang)\.(co|net|org|in(\W|fo)|us)",
    r"(health|earn|max|cash|wage|pay|pocket|cent|today)[\w-]{0,6}\d+\.com",
    r"(//|www\.)healthy?\w{5,}\.com",
    r"https?://[\w-.]\.repair\W", r"https?://[\w-.]{10,}\.(top|help)\W",
    r"filefix(er)?\.com", r"\.page\.tl\W", r"infotech\.(com|net|in)",
    r"\.(com|net)/(xtra|muscle)[\w-]", r"http\S*?\Wfor-sale\W",
    r"fifa\d+[\w-]*?\.com", r"[\w-](giveaway|jackets|supplys|male)\.com",
    r"((essay|resume|click2)\w{6,}|(essays|(research|term)paper|examcollection|[\w-]{5}writing|"
    r"writing[\w-]{5})[\w-]*?)\.(com?|net|org|in(\W|fo)|us|us)",
    r"(top|best|expert)\d\w{0,15}\.in\W", r"\dth(\.co)?\.in", r"(jobs|in)\L<city>\.in",
    r"[\w-](recovery|repairs?|rescuer|(?<!epoch|font)converter)(pro|kit)?\.(com|net)",
    r"(corrupt|repair)[\w-]*?\.blogspot",
    r"http\S*?(yahoo|gmail|hotmail|outlook|office|microsoft)?[\w-]{0,10}"
    r"(account|tech|customer|support|service|phone|help)[\w-]{0,10}(service|"
    r"care|help|recovery|support|phone|number)",
    r"http\S*?(essay|resume|thesis|dissertation|paper)-?writing",
    r"fix[\w-]*?(files?|tool(box)?)\.com", r"(repair|recovery|fix)tool(box)?\.(co|net|org)",
    r"smart(pc)?fixer\.(co|net|org)",
    r"errorcode0x\.(?:com?)",
    r"password[\w-]*?(cracker|unlocker|reset|buster|master|remover)\.(co|net)",
    r"crack[\w-]*?(serial|soft|password)[\w-]*?\.(co|net)",
    r"(downloader|pdf)converter\.(com|net)",
    r"ware[\w-]*?download\.(com|net|info|in\W)",
    r"((\d|\w{3})livestream|livestream(ing|s))[\w]*?\.(com|net|tv)", r"\w+vs\w+live\.(com|net|tv)",
    r"(play|watch|cup|20)[\w-]*?(live|online)\.(com|net|tv)", r"worldcup\d[\w-]*?\.(com|net|tv|blogspot)",
    r"https?://(\w{5,}tutoring\w*|cheat[\w-.]{3,}|xtreme[\w-]{5,})\.",
    r"(platinum|paying|acai|buy|premium|premier|ultra|thebest|best|[/.]try)[\w]{10,}\.(co|net|org|in(\W|fo)|us)",
    r"(training|institute|marketing)[\w-]{6,}[\w.-]*?\.(co|net|org|in(\W|fo)|us)",
    r"[\w-](courses?|training)[\w-]*?\.in/",
    r"\w{9}(buy|roofing)\.(co|net|org|in(\W|fo)|us)",
    # (something)health.(something)
    r"(vitamin|dive|hike|love|strong|ideal|natural|pro|magic|beware|top|best|free|cheap|allied|nutrition|"
    r"prostate)[\w-]*?health[\w-]*?\.(co|net|org|in(\W|fo)|us|wordpress|blogspot|tumblr|webs\.)",
    # (something)cream.(something)
    r"(eye|skin|age|aging)[\w-]*?cream[\w-]*?\.(co|net|org|in(\W|fo)|us|wordpress|blogspot|tumblr|webs\.)",
    # (keyword)(something)(keyword)(something).(something)
    r"(acai|advance|aging|alpha|beauty|belle|beta|biotic|body|boost(?! solution)|brain(?!tree)|burn|colon|"
    r"[^s]cream|cr[eè]me|derma|ecig|eye|face(?!book)|fat|formula|geniu[sx]|grow|hair|health|herbal|ideal|luminous|"
    r"male|medical|medicare|muscle|natura|no2|nutrition|optimal|pearl|perfect|phyto|probio|rejuven|revive|ripped|"
    r"rx|scam|shred|skin|slim|super|testo|[/.]top|trim|[/.]try|ultra|ultra|vapor|vita|weight|wellness|xplode|yoga|"
    r"young|youth)[\w]{0,20}(about|advi[sc]|assess|blog|brazil|canada|care|center|centre|chat|complex(?!ity)|"
    r"congress|consult|critic|critique|cure|denmark|discussion|doctor|dose|essence|essential|extract|fact|formula|"
    r"france|funct?ion|genix|guide|help|idea|info|jacked|l[iy]ft|mag|market|max|mexico|norway|nutrition|order|plus|"
    r"points|policy|potency|power|practice|pro|program|report|review|rewind|site|slim|solution|suppl(y|ier)|sweden|"
    r"tip|trial|try|world|zone)[.\w-]{0,12}\.(co|net|org|in(\W|fo)|us|wordpress|blogspot|tumblr|webs\.)",
    r"(\w{11}(idea|income|sale)|\w{6}(<?!notebook)(advice|problog|review))s?\.(co|net|in(\W|fo)|us)",
    r"-(poker|jobs)\.com", r"send[\w-]*?india\.(co|net|org|in(\W|fo)|us)",
    r"(file|photo|android|iphone)recovery[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"(videos?|movies?|watch)online[\w-]*?\.", r"hd(video|movie)[\w-]*?\.",
    r"backlink(?!(o\.|watch))[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"(replica[^nt]\w{5,}|\wrolex)\.(co|net|org|in(\W|fo)|us)",
    r"customer(service|support)[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"conferences?alert[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"seo\.com(?!/\w)", r"\Wseo(?!sitecheckup)[\w-]{10,}\.(com|net|in\W)",
    r"(?<!site)24x7[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"backlink[\w-]*?\.(com|net|de|blogspot)",
    r"(software|developers|packers|movers|logistic|service)[\w-]*?india\.(com|in\W)",
    r"scam[\w-]*?(book|alert|register|punch)[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"http\S*?crazy(mass|bulk)", r'http\S*\.com\.com[/"<]',
    r"https?://[^/\s]{8,}healer",
    r'reddit\.com/\w{6}/"',
    r"world[\w-]*?cricket[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"(credit|online)[\w-]*?loan[\w-]*?\.(co|net|org|in(\W|fo)|us)",
    r"worldcup\d+live\.(com?|net|org|in(\W|fo)|us)",
    r"((concrete|beton)-?mixer|crusher)[\w-]*?\.(co|net)",
    r"\w{7}formac\.(com|net|org)",
    r"sex\.(com|net|info)", r"https?://(www\.)?sex",
    r"[\w-]{12}\.(webs|66ghz)\.com", r'online\.us[/"<]',
    r"ptvsports\d+.com",
    r"youth\Wserum",
    r"buyviewsutube",
    r"(?:celebrity-?)?net-?worth", "richestcelebrities",
    r"ufc\wfight\wnight"  # Chiesa vs Lee spam
]
city_list = [
    "Agra", "Amritsar", "Bangalore", "Bhopal", "Chandigarh",
    "Chennai", "Coimbatore", "Delhi", "Dubai", "Durgapur",
    "Ghaziabad", "Hyderabad", "Jaipur", "Jalandhar", "Kolkata",
    "Ludhiana", "Mumbai", "Madurai", "Patna", "Portland",
    "Rajkot", "Surat", "Telangana", "Udaipur", "Uttarakhand",
    "Noida", "Pune", "Rohini", "Trivandrum", "Thiruvananthapuram",
    "Nashik", "Gurgaon", "Gurugram", "Kochi", "Ernakulam", "Nagpur", "Dehradun",
    "Neemrana", "Raipur", "Faridabad", "Kanhangad", "Kanhanjad",
    "Trichy", "Tiruchirappalli", "Tiruchi", "Trichinopoly",
    "Kerala", "Mangalore", "Mangaluru", "Thane", "Bhiwandi", "Ghatkopar",
    "Mulund",
    # yes, these aren't cities but...
    "India", "Pakistan",
    # buyabans.com spammer uses creative variations
    "Sri Lanka", "Srilanka", "Srilankan",
]


################################################################################
# The giant rule registry
#
# All our regex-based rules. Functional rules are defined along with the functions
################################################################################


# General blacklists, regex will be filled at the reload_blacklist() call at the bottom
FindSpam.rule_bad_keywords = create_rule("bad keyword in {}", regex="",
                                         username=True, body_summary=True,
                                         max_rep=4, max_score=1)
FindSpam.rule_watched_keywords = create_rule("potentially bad keyword in {}", regex="",
                                             username=True, body_summary=True,
                                             max_rep=30, max_score=1)
FindSpam.rule_blacklisted_websites = create_rule("blacklisted website in {}", regex="", body_summary=True,
                                                 max_rep=50, max_score=5)
FindSpam.rule_blacklisted_usernames = create_rule("blacklisted username", regex="",
                                                  title=False, body=False, username=True)

# gratis near the beginning of post or in title, SoftwareRecs and es.stackoverflow.com are exempt
create_rule("potentially bad keyword in {}", r"(?is)(?<=^.{0,200})\bgratis\b",
            sites=['softwarerecs.stackexchange.com', 'es.stackoverflow.com'],
            body_summary=True, max_rep=11)
# Watch keto(?:nes?)?, but exempt Chemistry. Was a watch added by iBug on 1533209512.
create_rule("potentially bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))keto(?:nes?)?(?:\b|(?w:\b)|$)",
            sites=['chemistry.stackexchange.com'],
            username=True, body_summary=True,
            max_rep=30, max_score=1)
# Bad keywords in titles and usernames, all sites
create_rule("bad keyword in {}",
            r"(?i)^(?:(?=.*?\b(?:online|hd)\b)(?=.*?(?:free|full|unlimited)).*?movies?\b)|(?=.*?\b(?:acai|"
            r"kisn)\b)(?=.*?care).*products?\b|(?=.*?packer).*mover|(online|certification).*?training|"
            r"\bvs\b.*\b(live|vivo)\b|(?<!can |uld )\bwe offer\b|payday loan|смотреть.*онлайн|"
            r"watch\b.{0,50}(online|episode|free)|episode.{0,50}\bsub\b",
            title=True, body=False, username=True)
# Car insurance spammers (username only)
create_rule("bad keyword in {}", r"car\Win",
            all=False, sites=['superuser.com', 'puzzling.stackexchange.com'],
            title=False, body=False, username=True)
# Judaism etc troll, 2018-04-18 ("potentially bad" makes this watch)
create_rule('potentially bad keyword in {}', r'^John$', all=False,
            sites=['judaism.stackexchange.com', 'superuser.com', 'islam.stackexchange.com',
                   'math.stackexchange.com', 'academia.stackexchange.com', 'medicalsciences.stackexchange.com',
                   'askubuntu.com', 'skeptics.stackexchange.com', 'politics.stackeschange.com'],
            title=False, body=False, username=True,
            disabled=True)
# Corn troll on Blender.SE
create_rule("potentially bad keyword in {}", r'\bcorn\b', all=False, sites=['blender.stackexchange.com'],
            username=True)
# Bad keywords in titles only, all sites
# The rule is supposed to trigger on stuff like f.r.e.e d.o.w.n.l.o.a.d
create_rule("bad keyword in {}", r"(?i)\b(?!s.m.a.r.t|s.h.i.e.l.d|s.o.l.i.d|o.s.a.r.l)[a-z](?:\.+[a-z]){4,}\b",
            body=False)
create_rule("bad keyword in {}",
            r'(?i)[\w\s]{0,20}help(?: a)?(?: weak)? postgraduate student(?: to)? write(?: a)? book\??',
            body=False, max_rep=20, max_score=2)
# Requested by Mithrandir 2019-03-08
create_rule("potentially bad keyword in {}", r'^v\w{3,5}\Wkumar$',
            title=False, body=False, username=True,
            all=False, sites=['scifi.stackexchange.com'])
# Eltima: Nested lookarounds for length limit
create_rule("bad keyword in {}", r"(?is)(?<=^(?=.{0,750}$).*)\beltima",
            title=False, max_rep=50)
create_rule("bad keyword in {}",
            r"(?i)\b((beauty|skin|health|face|eye)[- ]?(serum|therapy|hydration|tip|renewal|shop|store|lyft|"
            r"product|strateg(y|ies)|gel|lotion|cream|treatment|method|school|expert)|fat ?burn(er|ing)?|"
            r"muscle|testo ?[sx]\w*|body ?build(er|ing)|wrinkle|probiotic|acne|peni(s|le)|erection)s?\b|"
            r"(beauty|skin) care\b",
            sites=["fitness.stackexchange.com", "biology.stackexchange.com", "medicalsciences.stackexchange.com",
                   "skeptics.stackexchange.com", "robotics.stackexchange.com", "blender.stackexchange.com"],
            body=False)
# Bad health-related keywords in titles and posts, health sites are exempt
create_rule("bad keyword in {}",
            r"(?is)virility|diet ?(plan|pill)|serum|\b(pro)?derma(?=[a-su-z\W]\w)|(fat|(?<!dead[ -]?)weight)"
            r"[ -]?(loo?s[es]|reduction)|loo?s[es] ?weight|erectile|\bherpes\b|colon ?(detox|clean)|\bpenis\b",
            sites=["fitness.stackexchange.com", "biology.stackexchange.com", "medicalsciences.stackexchange.com",
                   "skeptics.stackexchange.com", "bicycles.stackexchange.com", "islam.stackexchange.com",
                   "pets.stackexchange.com", "parenting.stackexchange.com"],
            body_summary=True, stripcodeblocks=True)
# Korean character in title: requires 3
create_rule("Korean character in {}", r"(?i)\p{Script=Hangul}.*\p{Script=Hangul}.*\p{Script=Hangul}",
            sites=["korean.stackexchange.com"], body=False)
# Chinese characters in title: requires 3
create_rule("Chinese character in {}", r"(?i)\p{Script=Han}.*\p{Script=Han}.*\p{Script=Han}",
            sites=["chinese.stackexchange.com", "japanese.stackexchange.com", "ja.stackoverflow.com"],
            body=False)
# Hindi character in title
create_rule("Hindi character in {}", r"(?i)\p{Script=Devanagari}",
            sites=["hinduism.stackexchange.com"], body=False)
# English text on non-English site: rus.SE only
create_rule("English text in {} on a localized site", r"(?i)^[a-z0-9_\W]*[a-z]{3}[a-z0-9_\W]*$",
            all=False, sites=["rus.stackexchange.com"], stripcodeblocks=True)
# Roof repair
create_rule("bad keyword in {}", "roof repair",
            sites=["diy.stackexchange.com", "outdoors.stackexchange.com", "mechanics.stackexchange.com"],
            stripcodeblocks=True, body_summary=True, max_rep=11)
# Bad keywords (only include link at end sites + SO, the other sites give false positives for these keywords)
create_rule("bad keyword in {}", r"(?i)(?<!truth )serum|\b(?<!to )supplements\b", all=False,
            sites=["stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com",
                   "meta.stackexchange.com", "security.stackexchange.com", "webapps.stackexchange.com",
                   "apple.stackexchange.com", "graphicdesign.stackexchange.com", "workplace.stackexchange.com",
                   "patents.stackexchange.com", "money.stackexchange.com", "gaming.stackexchange.com",
                   "arduino.stackexchange.com"],
            stripcodeblocks=True, body_summary=True)
# Jesus Christ, the Son of God, on SciFi.
create_rule("bad keyword in {}", r"Son of (?:David|man)", all=False, sites=["scifi.stackexchange.com"],
            username=True)
create_rule("bad keyword in {}", r"holocaust\W(witnesses|belie(f|vers?)|denier)", all=False,
            sites=["skeptics.stackexchange.com", "history.stackexchange.com"])

# Category: Suspicious links
# Suspicious sites
create_rule("pattern-matching website in {}",
            r"(?i)({}|[\w-]*?({})[\w-]*?\.(com?|net|org|in(fo)?|us|blogspot|wordpress))(?![^>]*<)".format(
                "|".join(pattern_websites), "|".join(bad_keywords_nwb)),
            stripcodeblocks=True, body_summary=True, max_score=1)
# Country-name domains, travel and expats sites are exempt
create_rule("pattern-matching website in {}",
            r"(?i)\b(?:[\w-]{6,}|\w*shop\w*)(australia|brazil|canada|denmark|france|india|mexico|norway|pakistan|"
            r"spain|sweden)\w{0,4}\.(com|net)",
            sites=["travel.stackexchange.com", "expatriates.stackexchange.com"],
            username=True, body_summary=True)
# The TLDs of Iran, Pakistan, and Tokelau in answers
create_rule("pattern-matching website in {}",
            r'(?i)http\S*?(?<![/.]tcl)\.(ir|pk|tk)(?=[/"<])',
            username=True, body_summary=True, question=False)
# Suspicious health-related websites, health sites are exempt
create_rule("pattern-matching website in {}",
            r"(?i)(bodybuilding|workout|fitness(?!e)|diet|perfecthealth|muscle|nutrition(?!ix)|"
            r"prostate)[\w-]*?\.(com|co\.|net|org|info|in\W)",
            sites=["fitness.stackexchange.com", "biology.stackexchange.com", "medicalsciences.stackexchange.com",
                   "skeptics.stackexchange.com", "bicycles.stackexchange.com"],
            username=True, body_summary=True, max_rep=4, max_score=2)
# Links preceded by arrows >>>
create_rule("link following arrow in {}",
            r"(?is)(?:>>+|[@:]+>+|==\s*>+|={4,}|===>+|= = =|Read More|Click Here).{0,20}"
            r"https?://(?!i\.stack\.imgur\.com)(?=.{0,200}$)",
            stripcodeblocks=True, answer=False, max_rep=11)
# Link at the end of a short answer
create_rule("link at end of {}",
            r'(?is)(?<=^.{0,350})<a href="https?://(?:(?:www\.)?[\w-]+\.(?:blogspot\.|wordpress\.|co\.)?\w{2,4}'
            r'/?\w{0,2}/?|(?:plus\.google|www\.facebook)\.com/[\w/]+)"[^<]*</a>(?:</strong>)?\W*</p>\s*$'
            r'|\[/url\]\W*</p>\s*$',
            sites=["raspberrypi.stackexchange.com", "softwarerecs.stackexchange.com"],
            title=False, question=False)
# URL repeated at end of post
create_rule("repeated URL at end of long post",
            r"(?s)<a href=\"(?:http://%20)?(https?://(?:(?:www\.)?"
            r"[\w-]+\.(?:blogspot\.|wordpress\.|co\.)?\w{2,10}/?"
            r"[\w-]{0,40}?/?|(?:plus\.google|www\.facebook)\.com/[\w/]+))"
            r"\" rel=\"nofollow( noreferrer)?\">"
            r"(?="
            r".{300,}<a href=\"(?:http://%20)?\1\" "
            r"rel=\"nofollow( noreferrer)?\">(?:http://%20)?\1</a>"
            r"(?:</strong>)?\W*</p>\s*$"
            r")",
            title=False, stripcodeblocks=True)
# non-linked .tk site at the end of an answer
create_rule("pattern-matching website in {}",
            r'(?is)\w{3}(?<![/.]tcl)\.tk(?:</strong>)?\W*</p>\s*$',
            title=False, question=False)
# non-linked site at the end of a short answer
create_rule("link at end of {}",
            r'(?is)(?<=^.{0,350})\w{6}\.(com|co\.uk)(?:</strong>)?\W*</p>\s*$',
            title=False, question=False)
# Shortened URL near the end of question
create_rule("shortened URL in {}",
            r"(?is)://(?:w+\.)?(goo\.gl|bit\.ly|bit\.do|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|"
            r"wp\.me|alturl\.com|tiny\.cc|9nl\.me|post\.ly|dyo\.gs|bfy\.tw|amzn\.to|adf\.ly|adfoc\.us|"
            r"surl\.cn\.com|clkmein\.com|bluenik\.com|rurl\.us|adyou\.co|buff\.ly|ow\.ly|tgig\.ir)/(?=.{0,200}$)",
            sites=["superuser.com", "askubuntu.com"],
            title=False, answer=False)
# Shortened URL in an answer
create_rule("shortened URL in {}",
            r"(?is)://(?:w+\.)?(goo\.gl|bit\.ly|bit\.do|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|"
            r"wp\.me|alturl\.com|tiny\.cc|9nl\.me|post\.ly|dyo\.gs|bfy\.tw|amzn\.to|adf\.ly|adfoc\.us|"
            r"surl\.cn\.com|clkmein\.com|bluenik\.com|rurl\.us|adyou\.co|buff\.ly|ow\.ly)/",
            sites=["codegolf.stackexchange.com"],
            stripcodeblocks=True, question=False)
# Link text without Latin characters
create_rule("non-Latin link in {}",
            r">\s*([^\s0-9A-Za-z<'\"]\s*){3,}</a>",
            sites=["ja.stackoverflow.com", "ru.stackoverflow.com", "rus.stackexchange.com", "islam.stackexchange.com",
                   "japanese.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com",
                   "buddhism.stackexchange.com", "chinese.stackexchange.com", "russian.stackexchange.com",
                   "codegolf.stackexchange.com", "korean.stackexchange.com", "ukrainian.stackexchange.com"],
            title=False, stripcodeblocks=False, question=False)
# Link text is one character within a word
create_rule("one-character link in {}",
            r'(?iu)\w<a href="[^"]+" rel="nofollow( noreferrer)?">.</a>\w',
            title=False, stripcodeblocks=True, max_rep=11, max_score=1)
# Link text consists of punctuation, answers only
create_rule("linked punctuation in {}",
            r'(?iu)rel="nofollow( noreferrer)?">(?!><>)\W+</a>',
            sites=["codegolf.stackexchange.com"],
            title=False, stripcodeblocks=True, max_rep=11, max_score=1, question=False)
# URL in title, some sites are exempt
create_rule("URL in title",
            r"(?i)https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}|"
            r"\w{3,}\.(com|net)\b.*\w{3,}\.(com|net)\b",
            sites=["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com",
                   "ja.stackoverflow.com", "superuser.com", "askubuntu.com", "serverfault.com",
                   "unix.stackexchange.com", "webmasters.stackexchange.com"],
            body=False, max_rep=11)
# URL-only title, for the exempt sites
create_rule("URL-only title",
            r"(?i)^https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}(/\S*)?$",
            all=False,
            sites=["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com",
                   "ja.stackoverflow.com", "superuser.com", "askubuntu.com", "serverfault.com",
                   "unix.stackexchange.com", "webmasters.stackexchange.com"],
            body=False, max_rep=11)

# Category: Suspicious contact information
# Phone number in post
create_rule("phone number detected in {}",
            r"(?s)(?<=^.{0,250})\b1 ?[-(. ]8\d{2}[-). ] ?\d{3}[-. ]\d{4}\b",
            sites=["math.stackexchange.com"],
            title=False, stripcodeblocks=False)
# Email check for answers on selected sites
create_rule("email in {}",
            r"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})"
            r"[A-z0-9_.%+-]+\.[A-z]{2,4}\b",
            all=False,
            sites=["biology.stackexchange.com", "bitcoin.stackexchange.com", "ell.stackexchange.com",
                   "english.stackexchange.com", "expatriates.stackexchange.com", "gaming.stackexchange.com",
                   "medicalsciences.stackexchange.com", "money.stackexchange.com", "parenting.stackexchange.com",
                   "rpg.stackexchange.com", "scifi.stackexchange.com", "travel.stackexchange.com",
                   "worldbuilding.stackexchange.com"],
            stripcodeblocks=True, question=False)
# Email check for questions: check only at the end, and on selected sites
create_rule("email in {}",
            r"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})"
            r"[A-z0-9_.%+-]+\.[A-z]{2,4}\b(?s)(?=.{0,100}$)",
            all=False,
            sites=["money.stackexchange.com", "travel.stackexchange.com", "gamedev.stackexchange.com",
                   "gaming.stackexchange.com"],
            stripcodeblocks=True, answer=False)
# QQ/ICQ/WhatsApp... numbers, for all sites
create_rule("messaging number in {}",
            r'(?i)(?<![a-z0-9])QQ?(?:(?:\w*[vw]x?|[^a-z0-9])\D{0,8})?\d{5}[.-]?\d{4,5}(?!["\d])|'
            r'\bICQ[ :]{0,5}\d{9}\b|\bwh?atsa+pp?[ :+]{0,5}\d{10}',
            stripcodeblocks=True)

# Category: Trolling
# Offensive title: titles are more sensitive
create_rule("offensive {} detected",
            r"(?i)\bfuck|(?<!brain)fuck(ers?|ing)?\b",
            body=False, max_rep=101, max_score=5)
# Numbers-only title
create_rule("numbers-only title",
            r"^(?=.*[0-9])[^\pL]*$",
            sites=["math.stackexchange.com"],
            body=False, max_rep=50, max_score=5)
# One unique character in title
create_rule("{} has only one unique char",
            r"^(.)\1+$",
            body=False, max_rep=1000000, max_score=10000)
# Parenting troll
create_rule("bad keyword in {}",
            r"(?i)\b(erica|jeff|er1ca|spam|moderator)\b",
            all=False, sites=["parenting.stackexchange.com"],
            title=False, body_summary=True, max_rep=50)
# Code Review troll
create_rule("bad keyword in {}",
            r"JAMAL",
            all=False, sites=["codereview.stackexchange.com"],
            username=True, body_summary=True)
# Eggplant emoji
create_rule("potentially bad keyword in {}",
            r"\U0001F346",  # Unicode value for the eggplant emoji
            sites=["es.stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "ja.stackoverflow.com",
                   "rus.stackexchange.com"],
            max_rep=5000, max_score=3)
# Academia kangaroos
create_rule("bad keyword in {}"
            r"(?i)kangaroos",
            all=False, sites=["academia.stackexchange.com"])
create_rule('non-Google "google search" link in {}',
            r"(?i)\b\<a href=\".{0,25}\.xyz\"( rel=\"nofollow( noreferrer)?\")?\>.{0,15}google.{0,15}\<\/a\>\b",
            title=False, stripcodeblocks=True)
# Academia image by low-rep user
create_rule('image by low-rep user',
            r'\<img src="[^"]+"(?: alt="[^"]+")?>',
            all=False, sites=["academia.stackexchange.com"],
            title=False, stripcodeblocks=True)
# Link inside nested blockquotes
create_rule('link inside deeply nested blockquotes',
            r'(?:<blockquote>\s*){3,}<p><a href="([^<>]+)"[^<>]*>\1</a>\s*</p>\s*</blockquote>',
            title=False, stripcodeblocks=True)
# Title ends with Comma (IPS Troll)
create_rule("title ends with comma",
            r".*\,$",
            all=False, sites=['interpersonal.stackexchange.com'],
            body=False, max_rep=50)
# Title starts and ends with a forward slash
create_rule("title starts and ends with a forward slash",
            r"^\/.*\/$",
            body=False)

# Category: other
create_rule("blacklisted username",
            r'^[A-Z][a-z]{3,7}(19\d{2})$',
            all=False, sites=["drupal.stackexchange.com"],
            title=False, body=False, username=True)
create_rule("blacklisted username",
            r"(?i)^jeff$",
            all=False, sites=["parenting.stackexchange.com"],
            title=False, body=False, username=True)
create_rule("blacklisted username",
            r"(?i)^keshav$",
            all=False, sites=["judaism.stackexchange.com"],
            title=False, body=False, username=True)
# Judaism etc troll, 2018-04-18 (see also disabled watch above)
create_rule("blacklisted username", r'(?i)^john$',
            all=False,
            sites=['hinduism.stackexchange.com', 'judaism.stackexchange.com', 'islam.stackexchange.com'],
            title=False, body=False, username=True)


FindSpam.reload_blacklists()
