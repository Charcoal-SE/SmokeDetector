# -*- coding: utf-8 -*-
# noinspection PyCompatibility

import sys
import math
from difflib import SequenceMatcher
from urllib.parse import urlparse, unquote_plus
from itertools import chain
from collections import Counter
from datetime import datetime
from string import punctuation
import time
import os
import os.path as path
import threading

import regex
# noinspection PyPackageRequirements
import tld
# noinspection PyPackageRequirements
from tld.utils import TldDomainNotFound
import phonenumbers
import dns.resolver
import requests
import chatcommunicate

from helpers import log, regex_compile_no_cache, strip_pre_and_code_elements, strip_code_elements
import metasmoke_cache
from globalvars import GlobalVars
import blacklists
import phone_numbers


if tuple(int(x) for x in regex.__version__.split('.')) < (2, 5, 82):
    raise ImportError(
        'Need regex >= 2020.6.8 (internal version number 2.5.82; got %s)' %
        regex.__version__)

LINK_CACHE = dict()
LINK_CACHE_lock = threading.RLock()
LEVEN_DOMAIN_DISTANCE = 3
SIMILAR_THRESHOLD = 0.95
SIMILAR_ANSWER_THRESHOLD = 0.7
BODY_TITLE_SIMILAR_RATIO = 0.90
CHARACTER_USE_RATIO = 0.42
PUNCTUATION_RATIO = 0.42
REPEATED_CHARACTER_RATIO = 0.20
IMG_TXT_R_THRES = 0.7
EXCEPTION_RE = r"^Domain (.*) didn't .*!$"
RE_COMPILE = regex_compile_no_cache(EXCEPTION_RE)
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
WHITELISTED_WEBSITES_REGEX = regex_compile_no_cache(r"(?i)upload|\b(?:{})\b".format("|".join([
    "yfrog", "gfycat", "tinypic", "sendvid", "ctrlv", "prntscr", "gyazo", r"youtu\.?be", "past[ie]", "dropbox",
    "microsoft", "newegg", "cnet", "regex101", r"(?<!plus\.)google", "localhost", "ubuntu", "getbootstrap",
    r"jsfiddle\.net", r"codepen\.io", "pastebin", r"nltk\.org", r"xahlee\.info", r"ergoemacs\.org", "regexr"
] + [se_dom.replace(".", r"\.") for se_dom in SE_SITES_DOMAINS])))
URL_SHORTENER_REGEX_FRAGMENT = r"(?:{})".format('|'.join(regex.escape(site) for site in (
    '0i.is', '1b.yt', '1th.me', '92q.com', '9nl.me', 'adf.ly', 'adfoc.us', 'adyou.co',
    'alturl.com', 'amzn.to', 'bfy.tw', 'bit.do', 'bit.ly', 'bluenik.com', 'buff.ly',
    'ckk.ai', 'cl.ly', 'clk.ink', 'clk.sh', 'clkmein.com', 'cu2.io', 'cutt.us', 'dyo.gs',
    'etsy.me', 'fb.me', 'g3t.nl',
    'goo.gl',  # doctored; see below
    'inro.in', 'is.gd', 'j.mp', 'jfi.uno', 'mex.su', 'n9.cl', 'numl.org', 'ovo.fyi',
    'ow.ly', 'pdf.ac', 'post.ly', 'qrf.in', 'rave.dj', 'rplg.co', 'rurl.us', 'sco.lt',
    'snip.ly', 'surl.cn.com', 't.co', 'tez.kr', 'tgig.ir', 'tgw.onl', 'tiny.cc',
    'tinyurl.com', 'tr.im', 'wicc.me', 'wn.nr', 'wp.me', 'x4up.org', 'xurl.es', 'zee.gl',
    'zee.im'
)))
# Special case for goo.gl; update the escaped regex with some actual non-escaped regex
# to exclude anything like goo.gl/maps/...
URL_SHORTENER_REGEX_FRAGMENT = URL_SHORTENER_REGEX_FRAGMENT.replace(
    r'goo\.gl', r'goo\.gl(?![?&/]maps/)')
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
    # Additional added not as part of a systematic investigation:
    "ntp.org", "cpu-world.com", "caniuse.com", "guru99.com", "fontawesome.com",
    "nirsoft.net",
    # Added to prevent having 3 detections on just the domain.
    "writingexplained.org", "eitren.com"]

# Hostname whitelist for the "*bad IP for hostname in {}" detections (i.e. for ip_for_url_host)
# Hostnames should be all lowercase, as the hostnames are obtained from
# urlparse().hostname, which lowercases the hostname.
WHITELISTED_IP_HOSTNAMES = [
    "alfa.com.tw",
    "angular.io",
    "api.flutter.dev",
    "bot.run",
    "build.ninja",
    "data.gov.sg",
    "docker.com",
    "ergoemacs.org",
    "flutter.dev",
    "form.as",
    "godoc.org",
    "image.network",
    "log.info",
    "maindomain.com",
    "material.angular.io",
    "model.fit",
    "newsite.com",
    "nextjs.org",
    "ourdomain.com",
    "paint.net",
    "pipeline.fit",
    "portforward.com",
    "pub.dev",
    "reactjs.org",
    "shop.pimoroni.com",
    "size.my",
    "socket.io",
    "talkerscode.com",
    "terrytao.wordpress.com",
    "thepihut.com",
    "tips4java.wordpress.com",
    "ufile.io",
    "usenix.org",
    "whatever.com",
    "www.docker.com",
    "www.sefaria.org",
    "www.usenix.org",
    "xahlee.info",
    # Some which are in "bad IP for hostname in {}", but have only FP:
    "oceansyrup.com",
    "madainproject.com",
]

# Hostname whitelist for the "*bad NS for domain in {}" detections (i.e. for ns_for_url_domain)
# Hostnames should be all lowercase, as the hostnames are obtained from
# urlparse().hostname, which lowercases the hostname.
# This was seeded with those in the query:
# https://metasmoke.erwaysoftware.com/data/sql/queries/264-domains-in-bad-ns-for-domain-detections-by-fp
# which had 0 TP and > 5 FP.
# In addition, some which had a TP or two were also included, as those TP were individually determined to be
# detected by other things, TP for some reason other than what was detected, or otherwise determined to not
# need detection by this reason:
# paint.net, caniuse.com, nesbot.com, mail.com, dev47apps.com, 2.to, rudrastyh.com, joxi.ru
WHITELISTED_NS_HOSTNAMES = [
    "1.run",
    "123.com",
    "2.to",
    "4309.co.uk",
    "4gtricks.com",
    "5.run",
    "7-zip.org",
    "a2hosting.com",
    "aaai.org",
    "aiohttp.org",
    "algoseek.com",
    "ametsoc.org",
    "anbox.io",
    "antongerdelan.net",
    "aspnetcore.app",
    "automationtesting.in",
    "bitsrc.io",
    "bot.run",
    "caniuse.com",
    "ccel.org",
    "cmake.org",
    "cmder.net",
    "coder.work",
    "coinmarketcap.com",
    "coinscious.io",
    "convertcsv.com",
    "cvedetails.com",
    "datasciencemadesimple.com",
    "deniz-tasarim.site",
    "deploy.sh",
    "desertbot.io",
    "dev47apps.com",
    "displaylink.com",
    "duply.net",
    "elecrow.com",
    "engineeringtoolbox.com",
    "ergoemacs.org",
    "euclideanspace.com",
    "everythingfonts.com",
    "example2.com",
    "expert-advice.org",
    "flashrom.org",
    "ftdichip.com",
    "gitmemory.com",
    "graphene-python.org",
    "grymoire.com",
    "hackingwithswift.com",
    "harrisgeospatial.com",
    "hashicorp.com",
    "hopechurch.xyz",
    "hostname.com",
    "howtomechatronics.com",
    "image.network",
    "inmotionhosting.com",
    "internaldomain.com",
    "ionos.com",
    "islamiqate.com",
    "item.name",
    "itsfoss.com",
    "jazz-soft.net",
    "johndcook.com",
    "joxi.ru",
    "json.org",
    "json2csharp.com",
    "jwork.org",
    "key.properties",
    "keyboard.press",
    "killernetworking.com",
    "kitgram.cn",
    "kitware.com",
    "ledsupply.com",
    "liberty-development.net",
    "linfo.org",
    "ludwig.guru",
    "mail.com",
    "mastertheboss.com",
    "melpa.org",
    "messagebox.show",
    "myhost.com",
    "mypage.com",
    "nesbot.com",
    "newtonsoft.com",
    "nextjs.org",
    "nltk.org",
    "orgmode.org",
    "otexts.com",
    "paint.net",
    "pcpartpicker.com",
    "pingcap.com",
    "pointclouds.org",
    "programming.vip",
    "qgistutorials.com",
    "qt.io",
    "quasar.dev",
    "raspberrytips.com",
    "rcompanion.org",
    "reactivex.io",
    "readme.md",
    "regexstorm.net",
    "relevantcodes.com",
    "repairwin.com",
    "requirejs.org",
    "robjhyndman.com",
    "rudrastyh.com",
    "sane-project.org",
    "scintilla.org",
    "simos.info",
    "smartmontools.org",
    "socket.io",
    "springdoc.org",
    "sqlitebrowser.org",
    "sqlteam.com",
    "stepik.org",
    "substrate.io",
    "sunfounder.cc",
    "techmikael.com",
    "terraform.io",
    "this.how",
    "this.id",
    "tiamet3d.com",
    "tinyapps.org",
    "ubuntuupdates.org",
    "uipath.com",
    "user.email",
    "uubyte.com",
    "webslesson.info",
    "wikidevi.com",
    "wintips.org",
    "wphierarchy.com",
    "wpshout.com",
    "x.com",
    "xahlee.info",
    "xda-developers.com",
    "yoursite.com",
    "zlib.net",
    # Some which are blacklisted, but have FP
    "mastertheboss.com",
    "xenarmor.com",
]


if GlobalVars.perspective_key:
    PERSPECTIVE = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key=" + GlobalVars.perspective_key
    PERSPECTIVE_THRESHOLD = 0.85  # conservative

# Flee before the ugly URL validator regex!
# We are using this, instead of a nice library like BeautifulSoup, because spammers are
# stupid and don't always know how to actually *link* their web site. BeautifulSoup misses
# those plain text URLs.
# https://gist.github.com/dperini/729294#gistcomment-1296121
URL_REGEX = regex_compile_no_cache(
    r"""((?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)"""
    r"""(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2}))"""
    r"""(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"""
    r"""(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"""
    r"""|\b(?:(?:[A-Za-z\u00a1-\uffff0-9]-?)*[A-Za-z\u00a1-\uffff0-9]+)(?:\.(?:[A-Za-z\u00a1-\uffff0-9]-?)"""
    r"""*[A-Za-z\u00a1-\uffff0-9]+)*(?:\.(?:[A-Za-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/\S*)?""", regex.U)
TAG_REGEX = regex_compile_no_cache(r"</?[abcdehiklopsu][^>]*?>|\w+://", regex.U)

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
                 stripcodeblocks=False, whole_post=False, skip_creation_sanity_check=False, rule_id=None,
                 elapsed_time_reporting=None):
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
        self.rule_id = rule_id
        self.elapsed_time_reporting = elapsed_time_reporting
        if not skip_creation_sanity_check:
            self.sanity_check()

    def sanity_check(self):
        if not self.func and not self.regex:
            raise TypeError("A rule must have either 'func' or 'regex' valid! : {}".format(self.reason))

    def match(self, post):
        """
        Run this rule against a post.

        Returns a list of 3 tuples for [result_title, result_username, result_body],
        each in (match, reason, why) format
        """
        if not self.filter.match(post):
            # Post not matching the filter
            return [(False, "", "")] * 3

        body_to_check = post.body.replace("&nsbp;", "").replace("\xAD", "") \
                                 .replace("\u200B", "").replace("\u200C", "")
        body_type = "body" if not post.is_answer else "answer"
        reason = self.reason
        reason_title = reason.replace("{}", "title")
        reason_username = reason.replace("{}", "username")
        reason_body = reason.replace("{}", body_type)

        if self.stripcodeblocks:
            # use a placeholder to avoid triggering "linked punctuation" on code-only links
            body_to_check = strip_pre_and_code_elements(body_to_check, leave_note=True)
        if reason == 'phone number detected in {}':
            body_to_check = regex.sub("<(?:a|img)[^>]+>", "", body_to_check)

        matched_title, matched_username, matched_body = False, False, False
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
                    matched_body, _ = self.func(body_to_check, post.post_site)
                    result_body = (matched_body, "", "")
                else:
                    result_body = (False, "", "")
        elif self.regex:
            try:
                compiled_regex = self.compiled_regex
            except AttributeError:
                compiled_regex = regex_compile_no_cache(self.regex, regex.UNICODE, city=city_list, ignore_unused=True)
                self.compiled_regex = compiled_regex

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
            raise TypeError("To match, a rule must have either 'func' or 'regex' valid! : {}".format(reason))

        # "result" format: tuple((title_spam, title_reason, why), (username_spam, username_reason, why),
        #                        (body_spam, body_reason, why))
        return result_title, result_username, result_body

    def __call__(self, *args, **kwargs):
        # Preserve the functionality of a function
        if self.func:
            return self.func(*args, **kwargs)
        raise TypeError("This rule has no function set, can't call")


class FindSpam:
    rules = []
    rule_ids = set()
    reasons = set()

    # supplied at the bottom of this file
    rule_bad_keywords = None
    rule_watched_keywords = None
    rule_blacklisted_websites = None
    rule_blacklisted_usernames = None

    # This is the minimum number of seconds which need to have elapsed for the Rule
    # in order for some extra text to be added to the log output in order to draw more
    # attention to the line.
    ELAPSED_TIME_DRAW_ATTENTION_MIN = 5
    # This is an arbitrarily long list of tuples representing different required elapsed times,
    # the log level to use and text to prepend to the chat message.
    # If the text for the log level doesn't exist, then a log(<log level>, report text)
    # call is not executed.
    # If there's no text to prepend to the chat message, then no chat message is sent for that entry.
    # The list is scanned through in order with the last value where the elapsed time for the Rule
    # is greater than the <minimum elapsed time> is acted upon.
    ELAPSED_TIME_LOG_AND_TELL_LEVELS = [
        # (<Log level>, <text prepended to chat message>, <minimum elapsed time>)
        ('debug', '', 1),  # > 1 s: Log a "debug" level message for the Rule; No chat message
        ('info', 'High ', 10),  # > 10 s: Log an "info" for the Rule and output to chat as "High "
        ('warning', '**Very High** ', 30),  # > 30 s: Log a "warning" and output to chat as bold "Very High"
    ]

    @classmethod
    def reload_blacklists(cls):
        global bad_keywords_nwb

        blacklists.load_blacklists()
        # See PR 2322 for the reason of (?:^|\b) and (?:\b|$)
        # (?w:\b) is also useful
        cls.rule_bad_keywords.regex = r"(?is)(?:^|\b|(?w:\b))(?:{})(?:\b|(?w:\b)|$)|{}".format(
            "|".join(GlobalVars.bad_keywords), "|".join(bad_keywords_nwb))
        try:
            del cls.rule_bad_keywords.compiled_regex
        except AttributeError:
            pass
        cls.rule_bad_keywords.sanity_check()
        cls.rule_watched_keywords.regex = r'(?is)(?:^|\b|(?w:\b))(?:{})(?:\b|(?w:\b)|$)'.format(
            "|".join(GlobalVars.watched_keywords.keys()))
        try:
            del cls.rule_watched_keywords.compiled_regex
        except AttributeError:
            pass
        cls.rule_watched_keywords.sanity_check()
        cls.rule_blacklisted_websites.regex = r"(?i)({})".format(
            "|".join(GlobalVars.blacklisted_websites))
        try:
            del cls.rule_blacklisted_websites.compiled_regex
        except AttributeError:
            pass
        cls.rule_blacklisted_websites.sanity_check()
        cls.rule_blacklisted_usernames.regex = r"(?i)({})".format(
            "|".join(GlobalVars.blacklisted_usernames))
        try:
            del cls.rule_blacklisted_usernames.compiled_regex
        except AttributeError:
            pass
        cls.rule_blacklisted_usernames.sanity_check()
        GlobalVars.blacklisted_numbers_full, GlobalVars.blacklisted_numbers, \
            GlobalVars.blacklisted_numbers_normalized = \
            phone_numbers.process_numlist(GlobalVars.blacklisted_numbers_raw)
        GlobalVars.watched_numbers_full, GlobalVars.watched_numbers, \
            GlobalVars.watched_numbers_normalized = phone_numbers.process_numlist(GlobalVars.watched_numbers_raw)
        log('debug', "Global blacklists loaded")

    @staticmethod
    def test_post(post):
        result = []
        why_title, why_username, why_body = [], [], []
        post_brief_id = "{}/{}/{}".format(post.post_site, "a" if post.is_answer else "q", post.post_id)
        for rule in FindSpam.rules:
            start_time = time.time()
            title, username, body = rule.match(post)
            end_time = time.time()
            elapsed_time = end_time - start_time
            elapsed_time_draw_attention_min = FindSpam.ELAPSED_TIME_DRAW_ATTENTION_MIN
            elapsed_time_levels = FindSpam.ELAPSED_TIME_LOG_AND_TELL_LEVELS
            if type(rule.elapsed_time_reporting) is dict:
                elapsed_time_draw_attention_min = rule.elapsed_time_reporting.get('draw_attention_min', 600)
                elapsed_time_levels = rule.elapsed_time_reporting.get('levels', [])
            draw_attention = ' <------------------' if elapsed_time > elapsed_time_draw_attention_min else ''
            log_type = ''
            tell_text = ''
            for log_level, tell_level, minimum_elapsed_time in elapsed_time_levels:
                if (elapsed_time >= minimum_elapsed_time):
                    log_type = log_level
                    tell_text = tell_level
            if log_type or tell_text:
                log_message = ('Rule elapsed time: {:.2f} s'.format(elapsed_time)
                               + ': {}: {}'.format(rule.reason, rule.rule_id)
                               + ' for [{}](https://{})'.format(post_brief_id, post_brief_id))
                if log_type:
                    log(log_type, log_message + draw_attention)
                if tell_text:
                    chatcommunicate.tell_rooms_with('long-rule-times', tell_text + log_message)
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


################################################################################
# The Creator of all the spam check rules
# Do NOT touch the default values unless you want to break things
# what if a function does more than one job?
def create_rule(reason, regex=None, func=None, *, all=True, sites=[],
                title=True, body=True, body_summary=False, username=False,
                max_score=0, max_rep=1, question=True, answer=True, stripcodeblocks=False,
                whole_post=False,  # For some functions
                disabled=False,  # yeah, disabled=True is intuitive
                rule_id=None,  # Unique rule ID [The "reason" may be on multiple rules; this is unique to the rule.]
                elapsed_time_reporting=None,
                skip_creation_sanity_check=False):
    if not isinstance(reason, str):
        raise ValueError("reason must be a string")

    if GlobalVars.valid_detection_reasons is not None and reason not in GlobalVars.valid_detection_reasons:
        # There was a list of reasons provided in the config file as valid and this detection reason isn't in that list.
        disabled = True

    if rule_id is None and reason not in FindSpam.reasons:
        # Only the first Rule with the reason can use the reason as the default rule_id.
        rule_id = reason
    if rule_id is None or rule_id in FindSpam.rule_ids:
        raise ValueError("rule_id must exist and be unique for reason: {}::  ID: {}".format(reason, rule_id))
    FindSpam.rule_ids.add(rule_id)
    FindSpam.reasons.add(reason)

    if GlobalVars.valid_rule_ids is not None and rule_id not in GlobalVars.valid_rule_ids:
        # There was a list of valid rule IDs provided in the config file and this detection isn't in that list.
        disabled = True

    if not (body or body_summary or username):  # title-only
        answer = False  # answers have no titles, this saves some loops
    post_filter = PostFilter(all_sites=all, sites=sites, max_score=max_score, max_rep=max_rep,
                             question=question, answer=answer)
    if regex is not None:
        # Standalone mode
        rule = Rule(regex, reason=reason, filter=post_filter,
                    title=title, body=body, body_summary=body_summary, username=username,
                    stripcodeblocks=stripcodeblocks, skip_creation_sanity_check=skip_creation_sanity_check,
                    rule_id=rule_id, elapsed_time_reporting=elapsed_time_reporting)
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
                        stripcodeblocks=stripcodeblocks, skip_creation_sanity_check=skip_creation_sanity_check,
                        rule_id=rule_id, elapsed_time_reporting=elapsed_time_reporting)
            if not disabled:
                FindSpam.rules.append(rule)
            return rule

        if func is not None:  # Function is supplied, no need to decorate
            return decorator(func)
        else:  # real decorator mode
            return decorator


def is_whitelisted_website(url):
    # Imported from method link_at_end
    return bool(WHITELISTED_WEBSITES_REGEX.search(url)) or metasmoke_cache.is_website_whitelisted(url)


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


@create_rule("misleading link", title=False, max_rep=11, max_score=1, stripcodeblocks=True)
def misleading_link(s, site):
    # Regex that finds the href value and the link text from an HTML <a>, if the link text
    # doesn't contain a '<' or space.
    link_regex = r"<a href=\"([^\"]++)\"[^>]*+>\s*+([^< ]++)\s*+<\/a>"
    compiled = regex.compile(link_regex)
    search = compiled.search(s)
    if search is None:
        # The s string contained no HTML <a> elements with an href and link text matching the link_regex.
        return False, ''

    href, text = search[1], search[2]
    if '.' not in text:
        # To have a first level domain, the link text must contain a '.'.
        return False, ''
    try:
        parsed_href = tld.get_tld(href, as_object=True)
        if parsed_href.fld in SE_SITES_DOMAINS:
            return False, ''
        parsed_text = tld.get_tld(text, fix_protocol=True, as_object=True)
        # The parsed_text_fld_with_extra_subdomain check verifies the tld package found an actual domain,
        # rather than a second part of a tld. The tld package has gotten better at being sure it gets
        # a full tld, when it exists, but there may be some corner cases. This is definitely needed
        # at least for some tld versions prior to 0.9.8 (e.g. 0.9.0), but possible corner cases hint
        # that this check should be retained.
        parsed_text_fld_with_extra_subdomain = tld.get_tld('foo.' + parsed_text.fld, fix_protocol=True, as_object=True)
        if parsed_text.fld == parsed_text.tld or parsed_text.tld != parsed_text_fld_with_extra_subdomain.tld:
            # The link text doesn't have a valid domain (i.e. the FLD must be more than just the TLD).
            return False, ''
    except (tld.exceptions.TldDomainNotFound, tld.exceptions.TldBadUrl, ValueError) as err:
        return False, ''

    if site == 'stackoverflow.com' and parsed_text.fld.split('.')[-1] in SAFE_EXTENSIONS:
        return False, ''

    if href.endswith('/' + text):
        # Don't detect URLs like "https://example.com/foo.txt" for link text "foo.txt".
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


def len_img_block(string):
    """ Length of image html blocks from a string. """
    all_oc = regex.findall(r'<img\s[^<>]*+>', string)
    tot_len = 0
    for oc in all_oc:
        tot_len += len(oc)
    return tot_len


# max_score=2 to prevent voting fraud
@create_rule("post is mostly images", title=False, max_rep=201, max_score=2)
def mostly_img(s, site):
    if len(s) == 0:
        return False, ""

    s_len_img = len_img_block(strip_code_elements(s))
    if s_len_img / len(s) > IMG_TXT_R_THRES:
        return True, "{:.4f} of the post is html image blocks".format(s_len_img / len(s))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("repeating characters in {}", stripcodeblocks=True, max_rep=10000, max_score=10000)
def has_repeating_characters(s, site):
    s = s.strip().replace("\u200B", "").replace("\u200C", "")  # Strip leading and trailing spaces
    if "\n\n" in s or "<code>" in s or "<pre>" in s:
        return False, ""
    s = URL_REGEX.sub("", s)  # Strip URLs for this check
    if not s:
        return False, ""
    # Don't detect a couple of common ways for people to try to include tables (reduces FP by ~20%).
    if regex.search(r"(?:(?:----+|====+)[+|]+){2}", s):
        return False, ""
    # matches = regex.compile(r"([^\s_.,?!=~*/0-9-])(\1{9,})", regex.UNICODE).findall(s)
    matches = regex.compile(r"([^\s\d_.])(\1{9,})", regex.UNICODE).findall(s)
    match = "".join(["".join(match) for match in matches])
    if len(match) / len(s) >= REPEATED_CHARACTER_RATIO:  # Repeating characters make up >= 20 percent
        return True, "{}".format(", ".join(
            ["{}*{}".format(repr(match[0]), len(''.join(match))) for match in matches]))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("link at end of {}", title=False, all=False,
             sites=["superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com",
                    "security.stackexchange.com", "patents.stackexchange.com", "money.stackexchange.com",
                    "gaming.stackexchange.com", "arduino.stackexchange.com", "workplace.stackexchange.com"],
             rule_id="link at end: main link_at_end, limited sites")
def link_at_end(s, site):   # link at end of question, on selected sites
    s = regex.sub("</?(?:strong|em|p)>", "", s)
    match = regex.compile(
        r"(?i)https?://(?:"
        "" r"[.A-Za-z0-9-]*/?[.A-Za-z0-9-]*/?|"
        "" r"plus\.google\.com/[\w/]*|"
        "" r"www\.pinterest\.com/pin/[\d/]*|"
        r")(?=</a>\s*$)").search(s)
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
    "ukrainian.stackexchange.com"], body_summary=True, rule_id="Mostly non-Latin: most sites")
@create_rule("mostly non-Latin {}", all=False, sites=["stackoverflow.com"],
             stripcodeblocks=True, body_summary=True, question=False, rule_id="Mostly non-Latin: SO answers only")
def mostly_non_latin(s, site):   # majority of post is in non-Latin, non-Cyrillic characters
    word_chars = regex.sub(r'(?u)[\W0-9]|http\S*', "", s)
    non_latin_chars = regex.sub(r"(?u)\p{script=Latin}|\p{script=Cyrillic}", "", word_chars)
    if len(non_latin_chars) > 0.4 * len(word_chars):
        return True, "Text contains {} non-Latin characters out of {}".format(len(non_latin_chars), len(word_chars))
    return False, ""


phone_number_detected_in_title_second_exclude_regex_text = (
    r"(?is)^(?:"
    "" r"(?="
    "" "" r"(?!.*?(?:quick[\W_]*+books?|binance|support|help(?:line|desk)|\bcall\b|antivirus|customer|whatsapp?))"
    "" "" r".*?(?:"
    "" "" "" r"errors?\b"
    "" "" "" r"|(?#list of words/phrases which tend to indicate FP, but are also used by some spammers)\b(?:"
    "" "" "" "" r"regex|invalid|attempt|config"
    "" "" "" "" r"|translate|spreadsheet|identify(?:ing)?|stack(?:overflow|exchange)\.com/questions/"
    "" "" "" "" r"|ref=|official build|(?-i:GUI)|chrome ?(?: version)?\d{2,3}\.\d\.\d{4}\.\d{3}"
    "" "" "" "" r"|paten[dt]|arxiv|(?:please|pls)(?: someone)?(?: help)"
    "" "" "" "" r"|(?:any|some) ?(?:one|body)(?: (?:please|pls))? help|i need help|UUID"
    "" "" "" r")\b"
    "" r"))"
    "" r"|.*?(?:"
    "" "" r"(?#IP address)\b(?<=[\s\[\](,;:@/\\-]|^)(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"  # ) syntax
    "" "" r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b(?=[\s\[\](,;:/\\-]|$)(?<!\b\d\.\d\.\d\.\d\b)"  # ) highlighting
    "" "" r"|(?#simple recent date)(?<!\d)(?:"
    "" "" "" r"(?:(?:[012]?\d|3[01])[/-]){2}20(?:1\d|2[0-6])"
    "" "" "" r"|20(?:1\d|2[0-6])(?:[/-](?:[012]?\d|3[01])){2}"
    "" "" r")(?!\d)"
    "" "" r"|(?#Hex number)0x(?:(?<=\D0x)|(?<=^0x))[\da-f]+\b"
    "" "" r"|(?#6+ in a row of same number)(?:0{6}|1{6}|2{6}|3{6}|4{6}|5{6}|6{6}|7{6}|8{6}|9{6})"
    "" "" r"|(?#first 4 digits of 32 bit MAX_INT)2147"
    "" "" r"|(?#x86, i386, i486, etc)\b(?:x86|i\d86)\b"
    "" "" r"|(?#a long sequence of digits, too long for a phone number)(?:\d[,. ]?+){14}"
    "" "" r"|(?#decade date range)(?:(?<=\D)|^)(?:(?:1\d|20)\d0s?[\W_]{0,3}){2,}"
    "" "" r"|(?:(?:(?<=\D)|^)(?#simple recent date: yyyy[/-]?mm[/-]?dd)"
    "" "" "" r"(?:1\d|20)\d\d[/-]?(?:0[1-9]|1[0-2])[/-]?(?:0[1-9]|[12]\d|3[01]))"
    "" "" r"|(?:(?#sequence 23456 with potential separators)"
    "" "" "" r"2(?:(?<=[\D]2)|(?<=^2)|(?<=\W12)|(?<=^12))[\W_]*+3[\W_]*+4[\W_]*+5[\W_]*+6(?=\d*\b))"
    "" "" r"|(?#7+ in a row of same number, with separators)(?:"
    "" "" "" r"(?:0[\W_]*+){7}"
    "" "" "" r"|(?:1[\W_]*+){7}"
    "" "" "" r"|(?:2[\W_]*+){7}"
    "" "" "" r"|(?:3[\W_]*+){7}"
    "" "" "" r"|(?:4[\W_]*+){7}"
    "" "" "" r"|(?:5[\W_]*+){7}"
    "" "" "" r"|(?:6[\W_]*+){7}"
    "" "" "" r"|(?:7[\W_]*+){7}"
    "" "" "" r"|(?:8[\W_]*+){7}"
    "" "" "" r"|(?:9[\W_]*+){7}"
    "" "" r")"
    r"))")


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("phone number detected in {}", body=False,
             sites=["patents.stackexchange.com", "math.stackexchange.com", "mathoverflow.net"],
             rule_id="phone number detected in: main has_phone_number, not patents, math, mathoverflow")
def has_phone_number(s, site):
    if regex.compile(r"(?i)\b(address(es)?|run[- ]?time|error|value|server|hostname|timestamp|warning|code|"
                     r"(sp)?exception|version|chrome|1234567)\b", regex.UNICODE).search(s):
        return False, ""  # not a phone number
    if regex.compile(phone_number_detected_in_title_second_exclude_regex_text, regex.UNICODE).search(s):
        return False, ""  # Probably not a phone number; very unlikely to be TP.
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
def get_number_matches(candidates, normalized_candidates, deobfuscated_candidates, numlist, numlist_normalized=None):
    """
    Get the matches for a set of candidates which are in a number list
    """
    numlist_normalized = numlist_normalized or set()
    matches = []

    def check_set_and_add_matches(reported_match_type, these_candidates, number_detection_list):
        nonlocal normalized_candidates
        in_both = these_candidates & number_detection_list
        if reported_match_type == 'verbatim' and in_both:
            # Need to regenerate the normalized list without the ones derived from the verbatim matches
            candidates_without_verbatim_matches = candidates - in_both
            normalized_candidates = set(phone_numbers.normalize_list(candidates_without_verbatim_matches))
        for found in in_both:
            matches.append('{} found {}'.format(found, reported_match_type))

    check_set_and_add_matches('verbatim', candidates, numlist)
    check_set_and_add_matches('normalized', normalized_candidates, numlist_normalized)
    check_set_and_add_matches('obfuscated', deobfuscated_candidates, numlist_normalized)
    return matches


# noinspection PyMissingTypeHints
def check_numbers(s, numlist, numlist_normalized=None):
    """
    Extract sequences of possible phone numbers. Check extracted numbers
    against verbatim match (identical to item in list) or normalized match
    (digits are identical, but spacing or punctuation contains differences)
    with both the original text and a number-deobfuscated version.
    """
    numlist_normalized = numlist_normalized or set()
    matches = []
    candidates, normalized_candidates, deobfuscated_candidates = phone_numbers.get_all_candidates(s)
    matches = get_number_matches(candidates, normalized_candidates, deobfuscated_candidates,
                                 numlist, numlist_normalized)
    if matches:
        return True, '; '.join(matches)
    else:
        return False, ''


@create_rule("bad phone number in {}", body_summary=True, max_rep=32, max_score=1, stripcodeblocks=True)
def check_blacklisted_numbers(s, site):
    return check_numbers(
        s,
        GlobalVars.blacklisted_numbers,
        GlobalVars.blacklisted_numbers_normalized
    )


@create_rule("potentially bad keyword in {}", body_summary=True, max_rep=32, max_score=1, stripcodeblocks=True,
             rule_id="potentially bad phone number")
def check_watched_numbers(s, site):
    return check_numbers(
        s,
        GlobalVars.watched_numbers,
        GlobalVars.watched_numbers_normalized
    )


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("potentially bad keyword in {}", all=False, rule_id="potentially bad customer support phrase",
             sites=["askubuntu.com", "webapps.stackexchange.com", "webmasters.stackexchange.com"])
def customer_support_phrase(s, site):  # flexible detection of customer service
    # We don't want to double-detect phrases which the bad keywords list already detects,
    # so we remove anything that matches those from the string to test.
    excluded = regex.compile(r"(?is)(?:^|\b|(?w:\b))(?:{})(?:\b|(?w:\b)|$)".format(
        "|".join([
            # This list contains entries from the bad keywords list which we shouldn't double-detect.
            # Entries here need to be manually kept in sync with what's in the bad_keywords.txt.
            r"(?:support|service|helpline)(?:[\W_]*+phone)?[\W_]*+numbers?+(?<=^.{0,225})",
        ]))).sub('', s)
    shortened = excluded[0:300].lower()  # If applied to body, use just the beginning: otherwise many false positives.
    shortened = regex.sub(r"[^A-Za-z0-9\s]", "", shortened)   # deobfuscate
    phrase = regex.compile(r"(tech(nical)? support)|((support|service|contact|help(line)?) (telephone|phone|"
                           r"number))").search(shortened)
    if phrase:
        return True, u"Key phrase: *{}*".format(phrase.group(0))
    return False, ""


# noinspection PyUnusedLocal,PyMissingTypeHints
@create_rule("scam aimed at customers in {}")
def scam_aimed_at_customers(s, site):  # Scams aimed at customers of specific companies or industries
    s = s[0:300].lower()   # if applied to body, the beginning should be enough: otherwise many false positives
    s = regex.sub(r"[^A-Za-z0-9\s]", "", s)   # deobfuscate
    business = regex.compile(
        r"(?i)\b(airlines?|apple|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|"
        r"lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)\b").search(s)
    digits = len(regex.compile(r"\d").findall(s))
    if business and digits >= 5:
        keywords = regex.compile(r"(?i)\b(customer|help|care|helpline|reservation|phone|recovery|service|support|"
                                 r"contact|tech|technical|telephone|number)\b").findall(s)
        if len(set(keywords)) >= 2:
            matches = ", ".join(["".join(match) for match in keywords])
            return True, u"Targeting *{}* customers. Keywords: *{}*".format(business.group(0), matches)
    return False, ""


# Bad health-related keywords in titles, health sites are exempt
@create_rule("health-themed spam in {}", body=False, all=False, sites=[
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
        return True, u"Score {}: Keywords: *{}*".format(score, ", ".join(words).lower())
    return False, ""


# Pattern-matching product name: three keywords in a row at least once, or two in a row at least twice
@create_rule("pattern-matching product name in {}", body_summary=True, stripcodeblocks=True, answer=False,
             max_rep=12, max_score=1)
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
        "Brain", "Fuel", "Melt", "Fire", "Tank", "Life",
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
                            r"cure|testimony|kidney|hospital|wetting)s?\b|(?<=\s)Dr\.?(?=\s)|"
                            r"\$(?<!\$\$) ?[0-9,.]{4}(?!\(\w+(?:\.\w+)*:\d+\))(?![^\n]+[\n]+\s+at \w)|@qq\.com|"
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
    link = regex.compile(r'(?i)<a href="https?://\S++').search(s)
    if not link or is_whitelisted_website(link.group(0)):
        return False, ""
    praise = regex.compile(r"(?i)\b(?:nice|good|interesting|helpful|great|amazing) (?:article|blog|post|information)\b"
                           r"|very useful").search(s)
    thanks = regex.compile(r"(?i)\b(?:appreciate|than(?:k|ks|x)|gratidão)\b").search(s)
    keyword_regex_text = r"(?i)\b" \
                         r"(?:" \
                         "" r"I really appreciate" \
                         "" r"|many thanks" \
                         "" r"|thanks a lot" \
                         "" r"|thank you (?:very|for)" \
                         "" r"|than(?:ks|x) for (?:sharing|this|your)" \
                         "" r"|dear forum members" \
                         "" r"|(?:" \
                         "" "" r"very (?:informative|useful)" \
                         "" "" r"|stumbled upon (?:your|this)" \
                         "" "" r"|wonderful" \
                         "" "" r"|visit my" \
                         "" r") (?:blog|site|website|channel)" \
                         r")\b"
    keyword = regex.compile(keyword_regex_text).search(s)
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
        r"sites\.google\.com/view/id\d++/google/?drive/file/downloads/storage|"
        r"\b(buy|cheap) |"
        r"live[ -]?stream|"
        r"\bmake (money|\$)|"
        r"\b(porno?|(whole)?sale|coins|luxury|coupons?|essays?|in \L<city>)\b|"
        r"\b\L<city>(?:\b.{1,20}\b)?(service|escort|call girls?)|"
        r"\b(?:customer|recovery|technical|recovery)? ?(?:customer|support|service|repair|contact) "
        r"(?:phone|hotline|helpline)? ?numbers?\b|"
        r"(best|make|full|hd|software|cell|data|media)[\w ]{1,20}"
        r"" r"(online|service|company|agency|repair|recovery|school|universit(?:y|ies)|college)|"
        r"\b(writing (service|help)|essay (writing|tips))", city=city_list, ignore_unused=True)
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
    now = datetime.utcnow()
    log('debug', 'purge_cache({0}): age of oldest entry is {1}'.format(
        limit, now - cachevar[oldest[0]]['timestamp']))
    log('debug', 'purge_cache({0}): oldest remaining entry is {1}'.format(
        limit, now - cachevar[remaining]['timestamp']))
    for old in oldest:
        # Guard against KeyError; race condition?
        if old in cachevar:
            del cachevar[old]


def dns_query(label, qtype):
    # If there's no cache then assume *now* is important
    try:
        starttime = datetime.utcnow()
        # Extend lifetime if we are running a test
        extra_params = dict()
        if "pytest" in sys.modules:
            extra_params['lifetime'] = 60
        answer = dns.resolver.resolve(label, qtype, search=True, **extra_params)
    except dns.exception.DNSException as exc:
        if str(exc).startswith('None of DNS query names exist:'):
            log('debug', 'DNS label {0} not found; skipping'.format(label))
        else:
            endtime = datetime.utcnow()
            log('warning', 'DNS error {0} (duration: {1})'.format(
                exc, endtime - starttime))
        return None
    endtime = datetime.utcnow()
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
            if isinstance(nsentry, list):
                for ns in nsentry:
                    assert ns.endswith('.'),\
                        "Missing final dot on NS entry {0}".format(ns)
            else:
                assert isinstance(nsentry, str)
                assert nsentry.endswith('.'),\
                    "Missing final dot on NS entry {0}".format(nsentry)

    domains = []
    for hostname in post_hosts(s, check_tld=True):
        if hostname in WHITELISTED_NS_HOSTNAMES:
            continue
        domains.append(get_domain(hostname, full=True))

    for domain in set(domains):
        if domain in WHITELISTED_NS_HOSTNAMES:
            continue
        ns = dns_query(domain, 'ns')
        if ns is not None:
            nameservers = set([server.target.to_text().lower() for server in ns])
            for ns_candidate in nslist:
                if (type(ns_candidate) is list and nameservers == set(ns_candidate)) \
                    or any(ns.endswith('.{0}'.format(ns_candidate))
                           for ns in nameservers):
                    return True, '{domain} NS suspicious {ns}'.format(
                        domain=domain, ns=','.join(nameservers))
    return False, ""


def get_ns_ips(domain):
    """
    Extract IP addresses of name server(s) for a domain
    """
    ns_ips = []
    dom = tld.get_tld(
        domain, fix_protocol=True, as_object=True, fail_silently=True)
    if not dom:
        log('info', 'Could not get domain for %s' % (domain))
        return []
    nameservers = dns_query(dom.fld, 'ns')
    if nameservers is not None:
        log('info', 'Name servers: %s' % sorted(str(n) for n in nameservers))
        for ns in nameservers:
            this_ns_ips = dns_query(str(ns), 'a')
            if this_ns_ips is not None:
                ns_ips.extend([str(ip) for ip in this_ns_ips])
    return ns_ips


@create_rule("potentially problematic NS configuration in {}", stripcodeblocks=True, body_summary=True)
def ns_is_host(s, site):
    '''
    Check if the host name in a link resolves to the same IP address
    as the IP addresses of all its name servers.
    '''
    for hostname in post_hosts(s, check_tld=True):
        if metasmoke_cache.is_website_whitelisted(hostname):
            continue
        host_ip = dns_query(hostname, 'a')
        if host_ip is None:
            continue
        host_ips = set([str(x) for x in host_ip])
        if host_ips and set(get_ns_ips(get_domain(hostname, full=True))) == host_ips:
            return True, 'Suspicious nameservers: all IP addresses for {0} are in set {1}'.format(
                hostname, host_ips)
    return False, ''


@create_rule("bad NS for domain in {}", body_summary=True, stripcodeblocks=True)
def bad_ns_for_url_domain(s, site):
    return ns_for_url_domain(s, site, GlobalVars.blacklisted_nses)


# This applies to all answers, and non-SO questions
@create_rule("potentially bad NS for domain in {}", body_summary=True, stripcodeblocks=True, answer=False,
             sites=["stackoverflow.com"], rule_id="potentially bad NS for domain: questions only, not SO")
@create_rule("potentially bad NS for domain in {}", body_summary=True, stripcodeblocks=True, question=False,
             rule_id="potentially bad NS for domain, answers only, all sites")
def watched_ns_for_url_domain(s, site):
    return ns_for_url_domain(s, site, GlobalVars.watched_nses)


def ip_for_url_host(s, site, ip_list):
    # ######## FIXME: code duplication
    for hostname in post_hosts(s, check_tld=True):
        if hostname in WHITELISTED_IP_HOSTNAMES:
            continue
        a = dns_query(hostname, 'a')
        if a is not None:
            # ######## TODO: allow blocking of IP ranges with regex or CIDR
            for addr in set([str(x) for x in a]):
                log('debug', 'IP: IP {0} for hostname {1}'.format(
                    addr, hostname))
                if addr in ip_list:
                    return True, '{0} suspicious IP address {1}'.format(
                        hostname, addr)
        for ip in set(get_ns_ips(hostname)):
            if ip in ip_list:
                return True, '{0} suspicious IP address {1} for NS'.format(hostname, ip)
    return False, ""


@create_rule("potentially bad IP for hostname in {}",
             stripcodeblocks=True, body_summary=True)
def watched_ip_for_url_hostname(s, site):
    return ip_for_url_host(s, site, GlobalVars.watched_cidrs)


@create_rule("bad IP for hostname in {}",
             stripcodeblocks=True, body_summary=True)
def bad_ip_for_url_hostname(s, site):
    return ip_for_url_host(
        s, site,
        GlobalVars.blacklisted_cidrs)


def asn_for_url_host(s, site, asn_list):
    for hostname in post_hosts(s, check_tld=True):
        if any(hostname == x or hostname.endswith("." + x) or metasmoke_cache.is_website_whitelisted(hostname)
               for x in ASN_WHITELISTED_WEBSITES):
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
    return asn_for_url_host(s, site, GlobalVars.watched_asns)


@create_rule("offensive {} detected", body_summary=True, max_rep=101, max_score=2, stripcodeblocks=True,
             rule_id="offensive detected: main is_offensive_post, no code")
def is_offensive_post(s, site):
    if not s:
        return False, ""

    # https://regex101.com/r/EI2yLQ/1
    offensive = regex.compile(
        r"(?is)\b((?:(?:ur\Wm[ou]m|(yo)?u suck|[8B]={3,}[D>)]\s*[.~]*|n[il1]gg[aeu3][rh]?|(ass\W?|a|a-)hole|"
        r"daf[au][qk]|(?<!brain)(mother|mutha)?f\W*u\W*c?\W*k+(a|ing?|e?[rd]| *off+| *(you|ye|u)(rself)?|"
        r" u+|tard)?|(bul+)?shit(t?er|head)?|(yo)?u(r|'?re)? (gay|scum)|dickhead|(?:fur)?fa+g+(?:ot)?s?\b|"
        r"pedo(?!bapt|dont|log|mete?r|troph)|fascis[tm]s?|cocksuck(e?[rd])?|"
        r"whore|cunt|jerk(ing)?\W?off|cumm(y|ie)|butthurt|queef|lesbo|"
        r"bitche?|(eat|suck|throbbing|sw[oe]ll(en|ing)?)\b.{0,20}\b(cock|dick)|dee[sz]e? nut[sz]|"
        r"dumb\W?ass|wet\W?puss(y|ie)?|s[1l]ut+y?|shot\W?my\W?(hot\W?)?load)s?)+)\b")

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
    body, username = post.body, post.user_name
    body_lowercase = body.lower()
    sim_ratio, sim_webs = perform_similarity_checks(body, username)
    if sim_ratio >= SIMILAR_THRESHOLD:
        return False, False, True, "Username `{}` similar to {}, ratio={}".format(
            username,
            ', '.join(['*{}* at position {}-{}'.format(w,
                                                       body_lowercase.index(w.lower()),
                                                       body_lowercase.index(w.lower()) + len(w)) for w in sim_webs]),
            sim_ratio)
    else:
        return False, False, False, ""


@create_rule("single character over used in post", max_rep=22, body_summary=True,
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

    with LINK_CACHE_lock:
        if post in LINK_CACHE:
            log('debug', 'Returning cached links for post')
            return LINK_CACHE[post]['links']

    # Fix stupid spammer tricks
    edited_post = post
    for p in COMMON_MALFORMED_PROTOCOLS:
        edited_post = edited_post.replace(p[0], p[1])

    links = []
    for l in URL_REGEX.findall(edited_post):
        if l[-1].isalnum():
            links.append(l)
        else:
            links.append(l[:-1])

    with LINK_CACHE_lock:
        if len(LINK_CACHE.keys()) >= 15:
            log('debug', 'Trimming LINK_CACHE down to 5 entries')
            purge_cache(LINK_CACHE, 10)
            log('debug', 'LINK_CACHE purged')

        linkset = set(links)
        LINK_CACHE[post] = {'links': linkset, 'timestamp': datetime.utcnow()}
        return linkset


def post_hosts(post, check_tld=False):
    '''
    Return list of hostnames from the post_links() output.

    With check_tld=True, check if the links have valid TLDs; abandon and
    return an empty result if too many do not (limit is currently hardcoded
    at 3 invalid links).

    Augment LINK_CACHE with parsed hostnames.
    '''
    global LINK_CACHE

    with LINK_CACHE_lock:
        if post in LINK_CACHE and 'hosts' in LINK_CACHE[post]:
            return LINK_CACHE[post]['hosts']

    invalid_tld_count = 0
    hostnames = []
    for link in post_links(post):
        try:
            hostname = urlparse(link).hostname
            if hostname is None:
                hostname = urlparse('http://' + link).hostname
        except ValueError as err:
            log('debug', 'ValueError {0} when parsing {1}'.format(err, link))
            continue
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
    with LINK_CACHE_lock:
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


# create_rule("answer similar to existing answer on post", whole_post=True, max_rep=52
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


@create_rule("mostly punctuation marks in {}", max_rep=52,
             sites=["math.stackexchange.com", "mathoverflow.net", "codegolf.stackexchange.com"])
def mostly_punctuations(s, site):
    # Strip code blocks here rather than with `stripcodeblocks` so we get the length of the whole post in s.
    body = regex.sub(r"(?s)<pre([\w=\" -]*)?>.*?</pre>", "", s)
    body = regex.sub(r"(?s)<code>.*?</code>", "", body)
    body = strip_urls_and_tags(body)
    s = strip_urls_and_tags(s)
    if len(s) < 15:
        return False, ""
    # Don't detect a couple of common ways for people to try to include tables (reduces FP by ~20%).
    if regex.search(r"(?:(?:----+|====+)[+|]+){2}", s):
        return False, ""

    punct_re = regex.compile(r"[[:punct:]]")
    all_punc = punct_re.findall(body)
    if not all_punc:
        return False, ""

    num_punc = len(all_punc)
    all_punc_set = list(set(all_punc))  # Remove duplicates
    overall_frequency = num_punc / len(s)

    if overall_frequency >= PUNCTUATION_RATIO:
        return True, u"Post contains {} marks of {!r} out of {} characters".format(num_punc,
                                                                                   "".join(all_punc_set), len(s))
    else:
        return False, ""


@create_rule("no whitespace in {}", body=False, max_rep=10000, max_score=10000, rule_id="No whitespace in titles")
def no_whitespace_title(s, site):
    if regex.compile(r"(?is)^[0-9a-z]{20,}\s*$").match(s):
        return True, "No whitespace or formatting in title"
    else:
        return False, ""


@create_rule("no whitespace in {}", title=False, max_rep=10000, max_score=10000, rule_id="No whitespace in bodies")
def no_whitespace_body(s, site):
    if regex.compile(r"(?is)^<p>[0-9a-z]+</p>\s*$").match(s):
        return True, "No whitespace or formatting in body"
    else:
        return False, ""


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
             all=False, sites=["stackoverflow.com", "superuser.com"])
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
        with chatcommunicate._clients_lock:
            pingable = chatcommunicate._clients["stackexchange.com"].get_room(11540).get_pingable_user_names()

        if not pingable or not isinstance(pingable, list):
            return False, False, False, ""

        if post.user_name in pingable:
            return False, False, True, "Himalayan pink salt detected"

    return False, False, False, ""


# FLEE WHILE YOU STILL CAN.
@create_rule("offensive {} detected", all=False, stripcodeblocks=True, max_rep=101, max_score=1,
             sites=["hindiusm.stackexchange.com", "islam.stackexchange.com",
                    "judaism.stackexchange.com", "medicalsciences.stackexchange.com"],
             rule_id="offensive detected: religion_troll")
def religion_troll(s, site):
    regexes = [
        r'(?:(?:Rubellite\W*(?:Fae|Yaksi)|Sarvabhouma|Rohit|Anisha|Ahmed\W*Bkhaty|Anubhav\W*Jha|Vineet\W*Aggarwal|Josh'
        r'\W*K|Doniel\W*F|mbloch)(?:|\b.{1,200}?\b)(?:(?:mother)?[sf]uck|pis+|pus+(?:y|ies)|boo+b|tit|coc*k|dick|ass'
        r'(?:hole|lick)?|penis|phallus|vagina|cunt(?:bag)?|genital|rectum|dog+ystyle|blowjob|scum(?:bag)|bitch|bastard'
        r'|slut+(?:ish|y)?|harlot|whore|bloody|rotten|diseased|swelling|lesbian|queer|(?:homo|trans|bi)(?:sexual)?|'
        r'|tran+(?:y|ie)s?|'
        r'retard|jew(?:ish)?|nig+er|nic+a|fag(?:g?[eio]t)?|heretic|idiot|sinners|raghead|muslim|hindu)(?:(?:ing|e[dr]'
        r'|e?)[sz]?)?|(?:(?:mother)?[sf]uck|pis+|pus+(?:y|ies)|boo+b|tit|coc*k|dick|ass(?:hole|lick)?|penis|phallus|'
        r'vagina|cunt(?:bag)?|genital|rectum|dog+ystyle|blowjob|scum(?:bag)|bitch|bastard|slut+(?:ish|y)?|harlot|whore'
        r'|bloody|rotten|diseased|swelling|lesbian|queer|(?:homo|trans|bi)(?:sexual)?'
        r'|tran+(?:y|ie)s?|retard|jew(?:ish)?|nig+er|nic+a|'
        r'fag(?:g?[eio]t)?|heretic|idiot|sinners|raghead|muslim|hindu)(?:(?:ing|e[dr]|e?)[sz]?)?(?:|\b.{1,200}?\b)'
        r'(?:Rubellite\W*(?:Fae|Yaksi)|Sarvabhouma|Rohit|Anisha|Ahmed\W*Bkhaty|Anubhav\W*Jha|Vineet\W*Aggarwal|Josh'
        r'\W*K|Doniel\W*F|mbloch))',

        r'(?:[hl]indu(?:s|ism)?|jew(?:s|ish)?|juda(?:ic|ism)|kike'
        r'|tran+(?:y|ie)s?|(?:homo|trans|bi)(?:sexual)?)(?:\W*(?:(?:chew|kiss|bunch|are|is|n|it|is|and|of|an?'
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
    u"ಌ",
    "vashi?k[ae]r[ae]n",
    "garcinia",
    "cambogia",
    "forskolin",
    r"cbd\W?oil",
    "(?:eye|skin|aging) ?cream",
    "b ?a ?m ?(?:w ?o ?w|w ?a ?r)",
    "cogniq",
    r"male\Wperf(?!ormer)",
    "anti[- ]?aging",
    "(?:ultra|berry|body)[ -]?ketone",
    "(?:cogni|oro)[ -]?(?:lift|plex)",
    "(?:skin|face(?<!interface)(?<!surface)|eye)[- ]?(?:serum|therapy|hydration|tip|renewal|gel|lotion|cream)",
    r"\bnutra(?!l(?:|y|ity|i[sz]ing|i[sz]ed?)s?\b)",
    r"contact (?:me|us)\W*<a ",
    r"\brsgold",
    "ductcleaning",
    "packers.{0,15}(?:movers|logistic)(?:.{0,25}</a>)",
    "(?:brain|breast|male|penile|penis)[- ]?(?:enhance|enlarge|improve|boost|plus|peak)(?:ment)?",
    "tapsi ?sarkar",

    r"(?:"
    "" r"networking|cisco|sas|hadoop|mapreduce|oracle|dba|php|sql|javascript|js|java|designing|marketing"
    "" r"|salesforce|joomla"
    r")"
    r"(?: certification)? (?:courses?|training)(?=.{0,25}</a>)",

    r"(?:"
    "" r"design|development|compan(?:y|ies)|agen(?:ts?|c(?:y|ies))|experts?|institutes?|classes|schools?"
    "" r"|colleges?|universit(?:y|ies)|training|courses?|jobs?|institutions?"
    "" r"|automation|sex|services?|kindergarten"
    "" r"|services?|maintenance|clinic|surgeons?|treatments?|rehabilitation"
    "" r"|studios?|designers?"
    "" r"|restaurants?|food|cuisine|delicac(?:y|ies)"
    r")"
    r"\W*+(?:center|centre|institute|work|provider)?"
    r"(?:\b.{1,8}\b)?\L<city>\b",

    r"\b\L<city>(?:\b.{1,8}\b)?(?:tour)",  # TODO: Populate this "after city" keyword list
    u"Ｃ[Ｏ0]Ｍ",
    "sunergetic",
    "capilux",
    r"ICQ#?\d{4}-?\d{5}",
    "viarex",
    r"b\W?o\W?j\W?i\W?t\W?e\W?r",
    "(?:🐽|🐷){3,}+",
]

# Patterns: the top four lines are the most straightforward, matching any site with this string in domain name
pattern_websites = [
    r"(?:"
    "" r"enstella|recoverysoftware|removevirus|support(?:number|help|quickbooks)|techhelp|calltech|exclusive"
    "" r"|onlineshop|video(?:course|classes|tutorial(?!s))|vipmodel|porn(?<!wordporn)|wholesale|inboxmachine"
    "" r"|(?:get|buy)cheap|escort|diploma|gov(?:t|ernment)jobs|extramoney|earnathome|spell(?:caster|specialist)|profits"
    "" r"|seo-?(?:tool|service|trick|market)|onsale|fat(?:burn|loss)|(?:\.|//|best)cheap|online-?(?:training|solution)"
    "" r"|\bbabasupport\b|movieshook|where\w*to\w*buy"
    "" r"|norton(?!\.com(?<=[^\da-z-]norton\.com))"
    r")"
    r"[\w-]*+\.(?:com?|net|org|in(?:\W|fo)|us|ir|wordpress|blogspot|tumblr|webs(?=\.)|info)",

    r"(?:"
    "" r"replica(?!t)|rs\d?gold|rssong|runescapegold|maxgain|e-cash|mothers?day|phone-?number|fullmovie|tvstream"
    "" r"|trainingin|dissertation"
    "" r"|(?:placement|research)-?(?:paper|statement|essay)"
    "" r"|digitalmarketing|infocampus|freetrial"
    "" r"|cracked\w{3}|bestmover|relocation|\w{4}mortgage|revenue|testo[-bsx]|cleanse|cleansing|detox|suppl[ei]ment"
    "" r"|loan|herbal|serum"
    "" r"|lift(?:eye|skin)|(?:skin|eye)lift"
    "" r"|luma(?:genex|lift)|renuva|svelme|santeavis|wrinkle|topcare"
    r")"
    r"[\w-]*+\.(?:com?|net|org|in(?:\W|fo)|us|ir|wordpress|blogspot|tumblr|webs(?=\.)|info)",

    r"(?:"
    "" r"drivingschool|crack-?serial|serial-?(?:key|crack)|freecrack|appsfor(?:pc|mac)|probiotic|remedies|heathcare"
    "" r"|sideeffect|meatspin|packers\S{0,3}movers|(?:buy|sell)\S{0,12}cvv|goatse|burnfat|gronkaffe|muskel"
    "" r"|tes(?:tos)?terone|nitric(?:storm|oxide)|masculin|menhealth|intohealth|babaji|spellcaster|potentbody|slimbody"
    "" r"|slimatrex|moist|lefair|derma(?![nt])|xtrm|factorx|nitro(?<!appnitro)(?!us)|endorev|ketone"
    r")"
    r"[\w-]*+\.(?:com?|net|org|in(?:\W|fo)|us|ir|wordpress|blogspot|tumblr|webs(?=\.)|info)",

    r"(?:"
    "" r"moving|\w{10}spell|[\w-]{3}password|\w{5}deal(?<!greatfurnituredeal)|\w{5}facts(?<!nfoodfacts)|\w\dfacts"
    "" r"|\Btoyshop"
    "" r"|[\w-]{5}cheats"
    "" r"|[\w-]{6}girls(?<!djangogirls)(?!\.org(?:$|[/?]))"
    "" r"|clothing|shoes(?:inc)?|cheatcode|cracks|credits|-wallet|refunds|truo?ng|viet|trang"
    r")"
    r"\.(?:co|net|org|in(?:\W|fo)|us)",

    r"(?:health|earn|max|cash|wage|pay|pocket|cent|today)[\w-]{0,6}\d+\.com",
    r"(?://|www\.)healthy?\w{5,}+\.com",
    r"https?://[\w.-]\.repair\W",
    r"https?://[\w.-]{10,}\.(?:top|help)(?<!programmer\.help)(?<!documentation\.help)\W",
    r"filefix(?:er)?\.com",
    r"\.page\.tl\W",
    r"(?<=pure)infotech\.(?:com|net|in)",
    r"\.(?:com|net)/(?:xtra|muscle)[\w-]",
    r"http\S*?\Wfor-sale\W",
    r"fifa\d+[\w-]*+\.com",
    r"[\w-](?:giveaway|jackets|supplys|male)\.com",

    r"(?:"
    "" r"(?:essay|resume|click2)\w{6,}"
    "" r"|(?:essays|(?:research|term)paper|examcollection|[\w-]{5}writing|writing[\w-]{5})[\w-]*+"
    r")"
    r"\.(?:com?|net|org|in(?:\W|fo)|us|us)",

    r"(?:top|best|expert)\d\w{0,15}+\.in\W",
    r"\dth(?:\.co)?\.in",
    r"(?:jobs|in)-?\L<city>\.in",
    r"[\w-](?:recovery|repairs?|rescuer|converter(?<!(?:epoch|font)converter))(?:pro|kit)?\.(?:com|net)",
    r"(?:corrupt|repair)[\w-]*+\.blogspot",

    # The following may have been intended to include (?:yahoo|gmail|hotmail|outlook|office|microsoft)?[\w-]{0,10}
    # But, the regex made that superfluous.
    r"http\S*?"
    r"(?:accounts?+|tech|customers?+|supports?+|services?+|phones?+|helps?+)"
    r"[\w-]{0,10}"
    r"(?:services?+|cares?+|helps?+|recover(?:y|ies)?+|supports?+|phones?+|numbers?+)",

    r"http\S*?(?:essay|resume|thesis|dissertation|paper)-?writing",
    r"fix[\w-]*?(?:files?|tool(?:box)?)\.com",
    r"(?:repair|recovery|fix)tool(?:box)?\.(?:co|net|org)",
    r"smart(?:pc)?fixer\.(?:co|net|org)",
    r"errorcode0x\.(?:com?)",
    r"password[\w-]*?(?:cracker|unlocker|reset|buster|master|remover)\.(?:co|net)",
    r"crack[\w-]*?(?:serial|soft|password)[\w-]*+\.(?:co|net)",
    r"(?:downloader|pdf)converter\.(?:com|net)",
    r"ware[\w-]*?download\.(?:com|net|info|in\W)",
    r"(?:(?:\d|\w{3})livestream|livestream(?:ing|s))[\w]*+\.(?:com|net|tv)",
    r"\wvs\w+live\.(?:com|net|tv)",
    r"(?:play|watch|cup|20)[\w-]*?(?:live|online)\.(?:com|net|tv)",
    r"worldcup\d[\w-]*+\.(?:com|net|tv|blogspot)",
    r"https?://(?:\w{5,}tutoring\w*+|cheat[\w-.]{3,}+|xtreme[\w-]{5,}+)\.",
    r"(?:platinum|paying|acai|buy|premium|premier|ultra|thebest|best|[/.]try)\w{10,}+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"(?:training|institute|marketing)[\w-]{6}[\w.-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"[\w-](?:courses?|training)[\w-]*+\.in/",
    r"\w{9}(?:buy|roofing)\.(?:co|net|org|in(?:\W|fo)|us)",

    # (?:something)health.(?:something)
    r"(?:vitamin|dive|hike|love|strong|ideal|natural|pro|magic|beware|top|best|free|cheap|allied|nutrition|prostate)"
    r"[\w-]*?health[\w-]*+"
    r"\.(?:co|net|org|in(?:\W|fo)|us|wordpress|blogspot|tumblr|webs\.)",

    # (?:something)cream.(?:something)
    r"(?:eye|skin|age|aging)[\w-]*?cream[\w-]*+"
    r"\.(?:co|net|org|in(?:\W|fo)|us|wordpress|blogspot|tumblr|webs\.)",

    # (?:keyword)(?:something)(?:keyword)(?:something).(?:something)
    r"(?:"
    "" r"acai|advance|aging|alpha|beauty|belle|beta|biotic|body|boost(?! solution)|brain(?!tree)|burn"
    "" r"|colon|[^s]cream|cr[eè]me|derma|ecig|eye|face(?!book)|fat|formula|geniu[sx]|grow"
    "" r"|hair|health|herbal|ideal|luminous"
    "" r"|male|medical|medicare|muscle|natura|no2|nutrition|optimal|pearl|perfect|phyto|probio"
    "" r"|rejuven|revive|ripped|rx|scam|shred|skin|slim|super"
    "" r"|testo|[/.]top|trim|[/.]try|ultra|ultra|vapor|vita|weight|wellness|xplode|yoga"
    "" r"|young|youth"
    r")"
    r"[\w]{0,20}"
    r"(?:"
    "" r"about|advi[sc]|assess|blog|brazil"
    "" r"|canada|care|center|centre|chat|complex(?!ity)|congress|consult|critic|critique|cure"
    "" r"|denmark|discussion|doctor|dose"
    "" r"|essence|essential|extract|fact|formula|france|funct?ion"
    "" r"|genix|guide|help|idea|info|jacked|l[iy]ft"
    "" r"|mag|market|max|mexico|norway|nutrition|order|plus"
    "" r"|points|policy|potency|power|practice|pro|program"
    "" r"|report|review|rewind|site|slim|solution|suppl(?:y|ier)|sweden"
    "" r"|tip|trial|try|world|zone"
    r")"
    r"[.\w-]{0,12}"
    r"\.(?:co|net|org|in(?:\W|fo)|us|wordpress|blogspot|tumblr|webs\.)",

    r"(?:"
    "" r"\w{11}(?:idea|income|sale)|\w{6}(?:advice|problog|review)"
    "" r"(?<!notebookadvice)(?<!notebookproblog)(?<!notebookreview)"
    r")"
    r"s?"
    r"\.(?:co|net|in(?:\W|fo)|us)",

    r"-(?:poker|jobs)\.com",
    r"send[\w-]*?india\.(?:co|net|org|in(?:\W|fo)|us)",
    r"(?:file|photo|android|iphone)recovery[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"(?:videos?|movies?|watch)online[\w-]*+\.",
    r"hd(?:video|movie)[\w-]*+\.",
    r"backlink(?!(?:o\.|watch))[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"(?:replica[^nt]\w{5,}+|\wrolex)\.(?:co|net|org|in(?:\W|fo)|us)",
    r"customer(?:service|support)[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"conferences?alert[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"seo\.com(?!/\w)",
    r"\Wseo(?!sitecheckup)[\w-]{10,}+\.(?:com|net|in\W)",
    r"24x7(?<!site24x7)[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"backlink[\w-]*+\.(?:com|net|de|blogspot)",
    r"(?:software|developers|packers|movers|logistic|service)[\w-]*?india\.(?:com|in\W)",
    r"scam[\w-]*?(?:book|alert|register|punch)[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"http\S*?crazy(?:mass|bulk)",
    r'http\S*\.com\.com[/"<]',
    r"https?://[^/\s]{8,}healer",
    r'reddit\.com/\w{6}/"',
    r"world[\w-]*?cricket[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"(?:credit|online)[\w-]*?loan[\w-]*+\.(?:co|net|org|in(?:\W|fo)|us)",
    r"worldcup\d+live\.(?:com?|net|org|in(?:\W|fo)|us)",
    r"(?:(?:concrete|beton)-?mixer|crusher)[\w-]*+\.(?:co|net)",
    r"\w{7}formac\.(?:com|net|org)",
    r"sex\.(?:com|net|info)",
    r"https?://(?:www\.)?sex",
    r"[\w-]{12}\.(?:webs|66ghz)\.com",
    r'online\.us[/"<]',
    r"ptvsports\d+.com",
    r"youth\Wserum",
    r"buyviewsutube",
    r"(?:celebrity-?)?net-?worth",
    "richestcelebrities",
    r"ufc\wfight\wnight",  # Chiesa vs Lee spam
    # football live streaming spam
    r"football[\w-]{0,100}+(?:\.[\w-]{0,100}+)*\.(?:com?|net|org|in(?:fo)?|us|blogspot|wordpress|live)"
]
city_list = [
    "Agra", "Ahmedabad", "Ajanta", "Almora", "Alwar", "Ambattur", "Amritsar", "Anand Nagar", "Andheri",
    "Bangalore", "Banswarabhiwadi", "Bhilwara", "Bhimtal", "Bhiwandi", "Bhopal",
    "Calcutta", "Calicut", "Chandigarh",
    "Chennai", "Chittorgarh", "Coimbatore", "Colaba",
    "Darjeeling", "Dehradun", "Dehrdun", "Delhi", "Dharamshala", "Dharamsala", "Durgapur",
    "Ernakulam", "Faridabad",
    "Ghatkopar", "Ghaziabad", "Gurgaon", "Gurugram", "Guwahati",
    "Haldwani", "Haridwar", "Hyderabad",
    "Indore",
    "Jaipur", "Jalandhar", "Jim Corbett",
    "Kandivali", "Kangra", "Kanhangad", "Kanhanjad", "Kashmir", "Karnal", "Kerala",
    "Kochi", "Kolkata", "Kota",
    "Lokhandwala", "Lonavala", "Ludhiana",
    "Madurai", "Malad", "Marine Lines", "Manalis", "Mangalore", "Mangaluru", "Marathahalli", "Mayur Vihar",
    "Meghalaya", "Mehrauli", "Model Town", "Moti Nagar", "Mulund", "Mumbai",
    "Nagpur", "Nainital", "Nashik", "Neemrana", "Noida",
    "Palam", "Patna", "Pune",
    "Raipur", "Rajkot", "Ramnagar", "Rishikesh", "Rohini",
    "Sonipat", "Srinagar", "Surat",
    "Telangana", "Thane", "Thiruvananthapuram", "Tiruchi", "Tiruchirappalli", "Tirupati",
    "Trichinopoly", "Trichy", "Trivandrum", "Tura",
    "Udaipur", "Uttarakhand",
    "Vadodara", "Vasant Kunj", "Vasant Vihar", "Visakhapatnam", "Worli",
    # not in India
    "Ajman", "Dubai", "Fujairah", "Hamad", "Lahore", "Lusail", "Portland", "Sharjah",
    # yes, these aren't cities but...
    "Abu Dhabi", "Abudhabi", "India", "Malaysia", "Pakistan", "Qatar",
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
                                         max_rep=32, max_score=1, skip_creation_sanity_check=True,
                                         rule_id="main blacklisted keywords")
FindSpam.rule_watched_keywords = create_rule("potentially bad keyword in {}", regex="",
                                             username=True, body_summary=True,
                                             max_rep=32, max_score=1, skip_creation_sanity_check=True,
                                             rule_id="main watchlist",
                                             elapsed_time_reporting={
                                                 'draw_attention_min': 20,
                                                 'levels': [
                                                     ('debug', '', 10),
                                                     ('info', 'High ', 20),
                                                     ('warning', '**Very High** ', 45),
                                                 ],
                                             })
FindSpam.rule_blacklisted_websites = create_rule("blacklisted website in {}", regex="", body_summary=True,
                                                 max_rep=52, max_score=5, skip_creation_sanity_check=True,
                                                 rule_id="main blacklisted websites")
FindSpam.rule_blacklisted_usernames = create_rule("blacklisted username", regex="",
                                                  title=False, body=False, username=True,
                                                  skip_creation_sanity_check=True,
                                                  rule_id="main blacklisted usernames")

# gratis near the beginning of post or in title, SoftwareRecs and es.stackoverflow.com are exempt
create_rule("potentially bad keyword in {}", r"(?is)gratis\b(?<=^.{0,200}\bgratis\b)",
            sites=['softwarerecs.stackexchange.com', 'es.stackoverflow.com'],
            body_summary=True, max_rep=11,
            rule_id="Potentialy bad keywords: gratis, not softwarerecs and es.SO")
# Blacklist keto(?:nes?)?, but exempt Chemistry. Was a watch added by iBug on 1533209512.
# not medicalsciences, fitness, biology
create_rule("bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))keto(?:nes?)?(?:\b|(?w:\b)|$)",
            sites=['chemistry.stackexchange.com',
                   'medicalsciences.stackexchange.com',
                   'fitness.stackexchange.com',
                   'biology.stackexchange.com',
                   'stackoverflow.com'],
            username=True, body_summary=True,
            max_rep=32, max_score=1,
            rule_id="bad keywords: keto, not sciences and SO")
# Blacklist keto(?:nes?)?, but exempt Chemistry. Was a watch added by iBug on 1533209512.
# Stack Overflow, but not in code
create_rule("bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))keto(?:nes?)?(?:\b|(?w:\b)|$)", all=False, stripcodeblocks=True,
            sites=['stackoverflow.com'],
            username=True, body_summary=True,
            max_rep=32, max_score=1,
            rule_id="bad keywords: keto, not in code, SO")
# Watch keto(?:nes?)? on sites where it's not blacklisted, exempt Chemistry. Was a watch added by iBug on 1533209512.
create_rule("potentially bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))keto(?:nes?)?(?:\b|(?w:\b)|$)", all=False,
            sites=['medicalsciences.stackexchange.com',
                   'fitness.stackexchange.com',
                   'biology.stackexchange.com'],
            username=True, body_summary=True,
            max_rep=32, max_score=1,
            rule_id="Potentialy bad keywords: keto, not medicalsciences, fitness, biology")
# Watch (?-i:SEO|seo)$, but exempt Webmasters for titles, but not usernames. Was a watch by iBug on 1541730383. (pt1)
create_rule("potentially bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))(?-i:SEO|seo)$",
            sites=['webmasters.stackexchange.com'],
            title=True, body=False, username=False,
            max_rep=32, max_score=1,
            rule_id="Potentialy bad keywords: SEO, titles only, not webmasters")
# Watch (?-i:SEO|seo)$, but exempt Webmasters for titles, but not usernames. Was a watch by iBug on 1541730383. (pt2)
create_rule("potentially bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))(?-i:SEO|seo)$",
            title=False, body=False, username=True,
            max_rep=32, max_score=1,
            rule_id="Potentialy bad keywords: SEO, usernames only")

# Bad keywords in titles and usernames, all sites
# %TP: 2020-06-27 01:00UTC: ~97.65%TP
# Title Results: 2925/TP:2864/FP:60/NAA:0
# Username Results: 54/TP:45/FP:6/NAA:3
create_rule("bad keyword in {}",
            r"(?i)"
            r"^(?:"
            "" r"(?=.{0,150}?\b(?:online|hd)\b)"
            "" r"(?=.{0,150}?(?:free|full|unlimited))"
            "" r".{0,150}?movies?\b"
            r")"
            r"|^(?=.{0,150}?skin).{0,150}(?:care|product)s?\b"
            r"|^(?=.{0,150}?packer).{0,150}mover"
            r"|(online|certification).{0,150}?training",
            title=True, body=False, username=True,
            max_rep=32, max_score=1,
            rule_id="bad keywords: movies, free, skin care, training, not bodies")

# Potentially bad keywords in titles and usernames, all sites
# Not suffient %TP for blacklist: 2020-06-27 01:00UTC: ~77.59%TP
# Title Results: 398/TP:312/FP:81/NAA:3
# Username Results: 17/TP:10/FP:8/NAA:0
create_rule("potentially bad keyword in {}",
            r"(?i)"
            r"\bvs\b(?![\W_]*+(?:code|mvc)\b).{0,150}\b(live|vivo)\b"
            r"|\bwe offer(?<!(?:can |uld )we offer)\b"
            r"|payday[\W_]*+loan"
            r"|смотреть.{0,150}онлайн"
            r"|watch\b.{0,150}(online|episode|free\b)"
            r"|episode.{0,150}\bsub\b",
            title=True, body=False, username=True,
            max_rep=32, max_score=1,
            rule_id="Potentialy bad keywords: videos, payday loans, titles and usernames")

# Car insurance spammers (username only)
create_rule("bad keyword in {}", r"car\Win",
            all=False, sites=['superuser.com', 'puzzling.stackexchange.com'],
            title=False, body=False, username=True,
            rule_id="bad keywords: car in, usernames only, SU and puzzling")
# Judaism etc troll, 2018-04-18 ("potentially bad" makes this watch)
create_rule('potentially bad keyword in {}', r'^John$', all=False,
            sites=['judaism.stackexchange.com', 'superuser.com', 'islam.stackexchange.com',
                   'math.stackexchange.com', 'academia.stackexchange.com', 'medicalsciences.stackexchange.com',
                   'askubuntu.com', 'skeptics.stackexchange.com', 'politics.stackeschange.com'],
            title=False, body=False, username=True,
            disabled=True,
            rule_id="Potentialy bad keywords: username: John, selected sites")
# Corn troll on Blender.SE
create_rule("potentially bad keyword in {}", r'\bcorn\b', all=False, sites=['blender.stackexchange.com'],
            username=True,
            rule_id="Potentialy bad keywords: username: corn, blender")
# Bad keywords in titles only, all sites
# The rule is supposed to trigger on stuff like f.r.e.e d.o.w.n.l.o.a.d
# 2020-04-20: This next one hasn't seen a TP in almost 2 years. Overall, it's running about 50% TP.
create_rule("potentially bad keyword in {}",
            r"(?i)\b(?!s.m.a.r.t|s.h.i.e.l.d|h.i.e.l.d|s.o.l.i.d|o.s.a.r.l)[a-z](?:\.+[a-z]){4,}\b",
            body=False,
            rule_id="Potentialy bad keywords: obfuscated smart shield, not bodies")
create_rule("bad keyword in {}",
            r'(?i)[\w\s]{0,20}help(?: a)?(?: weak)? postgraduate student(?: to)? write(?: a)? book\??',
            body=False, max_rep=22, max_score=2,
            rule_id="bad keywords: help postgrad write, not bodies")
# Requested by Mithrandir 2019-03-08
create_rule("potentially bad keyword in {}", r'^v\w{3,5}\Wkumar$',
            title=False, body=False, username=True,
            all=False, sites=['scifi.stackexchange.com'],
            rule_id="Potentialy bad keywords: username *kumar, scifi")
create_rule("bad keyword in {}",
            r"(?i)\b(?:(?:beauty|skin|health|face|eye)[- ]?(?:serum|therapy|hydration|tip|renewal|shop|store|lyft|"
            r"product|strateg(?:y|ies)|gel|lotion|cream|treatment|method|school|expert)|fat ?burn(?:er|ing)?|"
            r"muscle|testo ?[sx]\w*|body ?build(?:er|ing)|wrinkle|probiotic|acne|peni(?:s|le)|erection)s?\b|"
            r"(?:beauty|skin) care\b",
            sites=["fitness.stackexchange.com", "biology.stackexchange.com", "medicalsciences.stackexchange.com",
                   "skeptics.stackexchange.com", "robotics.stackexchange.com", "blender.stackexchange.com"],
            body=False,
            rule_id="bad keywords: beauty, skin care, etc, not bodies, not sciences")
# Bad health-related keywords in titles and posts, health sites and SciFi are exempt
# If you change some here, you should look at changing these for SciFi in the two below.
create_rule("bad keyword in {}",
            r"(?is)virility|diet ?(?:plan|pill)|serum|\b(?:pro)?derma(?=[a-su-z\W]\w)"
            r"|(?:fat|weight(?<!dead[ -]?weight))[ -]?(?:loo?s[es]|reduction)|loo?s[es] ?weight"
            r"|erectile|\bherpes\b|colon ?(?:detox|clean)|\bpenis\b",
            sites=["fitness.stackexchange.com", "biology.stackexchange.com", "medicalsciences.stackexchange.com",
                   "skeptics.stackexchange.com", "bicycles.stackexchange.com", "islam.stackexchange.com",
                   "pets.stackexchange.com", "parenting.stackexchange.com", "scifi.stackexchange.com"],
            body_summary=True, stripcodeblocks=True,
            rule_id="bad keywords: health related, not health sites and SciFi")
# For SciFi, split the health-related keywords in titles and posts into "bad" and "potentially bad", and ignore "serum"
create_rule("bad keyword in {}",
            r"(?is)virility|diet ?(?:plan|pill)|\b(?:pro)?derma(?=[a-su-z\W]\w)"
            r"|fat[ -]?(?:loo?s[es]|reduction)"
            r"|erectile|\bherpes\b|colon ?(?:detox|clean)",
            all=False, sites=["scifi.stackexchange.com"],
            body_summary=True, stripcodeblocks=True,
            rule_id="bad keywords: lesser health related, scifi")
create_rule("potentially bad keyword in {}",
            r"(?is)"
            r"weight(?<!dead[ -]?weight)[ -]?(?:loo?s[es]|reduction)|loo?s[es] ?weight"
            r"|\bpenis\b",
            all=False, sites=["scifi.stackexchange.com"],
            body_summary=True, stripcodeblocks=True,
            rule_id="Potentialy bad keywords: weight reduction/loss, scifi")
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
create_rule("bad keyword in {}", r"(?is)roof repair",
            sites=["diy.stackexchange.com", "outdoors.stackexchange.com", "mechanics.stackexchange.com"],
            stripcodeblocks=True, body_summary=True, max_rep=11,
            rule_id="bad keywords: roof repair, diy, outdoors, mechanics")
# Bad keywords (only include link at end sites + SO, the other sites give false positives for these keywords)
create_rule("bad keyword in {}", r"(?i)serum(?<!truth serum)|\bsupplements(?<!to supplements)\b", all=False,
            sites=["stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com",
                   "meta.stackexchange.com", "security.stackexchange.com", "webapps.stackexchange.com",
                   "apple.stackexchange.com", "graphicdesign.stackexchange.com", "workplace.stackexchange.com",
                   "patents.stackexchange.com", "money.stackexchange.com", "gaming.stackexchange.com",
                   "arduino.stackexchange.com"],
            stripcodeblocks=True, body_summary=True,
            rule_id="bad keywords: serum, supplements, limited sites, no code")
# Jesus Christ, the Son of God, on SciFi.
create_rule("bad keyword in {}", r"Son of (?:David|man)", all=False, sites=["scifi.stackexchange.com"],
            username=True,
            rule_id="bad keywords: usernames:son of david, scifi")
# Holocaust troll
create_rule("bad keyword in {}", r"(?is)holocaust\W(witnesses|belie(?:f|vers?)|deni(?:er|al)|is\Wreal)",
            all=False, sites=["skeptics.stackexchange.com", "history.stackexchange.com"],
            rule_id="bad keywords: holocaust, not skeptics, history")
# Online poker, except poker.SE
create_rule("bad keyword in {}", r"(?is)(?:^|\b|(?w:\b))(?:(?:poker|casino)\W*online"
            r"|online\W*(?:poker|casino))(?:\b|(?w:\b)|$)", all=True,
            sites=["poker.stackexchange.com"],
            rule_id="bad keywords: online poker, casino, not poker")
# Category: Suspicious links
# Suspicious sites 1
create_rule("pattern-matching website in {}",
            r"(?i)(?:{})(?![^>]*<)".format("|".join(pattern_websites)),
            stripcodeblocks=True, body_summary=True, max_score=1,
            rule_id="pattern matching website: main pattern_websites")
# Suspicious sites 2
create_rule("pattern-matching website in {}",
            r"(?i)(?:(?:{})[\w-]*+\.(?:com?|net|org|in(?:fo)?|us|blogspot|wordpress))(?![^<>]*+<)".format(
                "|".join(bad_keywords_nwb)),
            stripcodeblocks=True, body_summary=True, max_score=1,
            rule_id="pattern matching website: bad_keywords_nwb")
# Country-name domains, travel and expats sites are exempt
create_rule("pattern-matching website in {}",
            r"(?i)\b(?:[\w-]{6,}|\w*shop\w*)(australia|brazil|canada|denmark|france|india|mexico|norway|pakistan|"
            r"spain|sweden)\w{0,4}\.(com|net)",
            sites=["travel.stackexchange.com", "expatriates.stackexchange.com"],
            username=True, body_summary=True,
            rule_id="pattern matching website: shop or various countries")
# The TLDs of Iran, Pakistan, United Arab Emirates, or Tokelau in answers
create_rule("pattern-matching website in {}",
            r'(?i)http\S*?(?<![/.]tcl)\.(ae|ir|pk|tk)(?=[/"<])',
            username=True, body_summary=True, question=False,
            rule_id="pattern matching website: commonly problematic TLDs")
# Suspicious health-related websites, health sites are exempt
create_rule("pattern-matching website in {}",
            r"(?i)(?:bodybuilding|workout|fitness(?!e)|diet(?!pi\.com(?<=(?<!-)\bdietpi\.com)\b(?![.-]))|"
            r"perfecthealth|muscle|nutrition(?!ix)|prostate)"
            r"[\w-]*?\.(?:com|co\.|net|org|info|in\W)",
            sites=["fitness.stackexchange.com", "biology.stackexchange.com", "medicalsciences.stackexchange.com",
                   "skeptics.stackexchange.com", "bicycles.stackexchange.com"],
            username=True, body_summary=True, max_rep=22, max_score=2,
            rule_id="pattern matching website: health themed, not health sites")
# Links preceded by arrows >>>
create_rule("link following arrow in {}",
            r"(?is)(?:>>+|[@:]+>+|==\s*>+|={4,}|===>+|= = =|Read More|Click Here).{0,20}"
            r"https?://(?!i\.stack\.imgur\.com)(?=.{0,200}$)",
            stripcodeblocks=True, answer=False, max_rep=11)
# Link at the end of a short answer
create_rule("link at end of {}",
            r'(?is)<a href="https?://(?<=^.{0,368})(?:(?:www\.)?[\w-]+\.(?:blogspot\.|wordpress\.|co\.)?\w{2,4}'
            r'/?\w{0,2}/?|(?:plus\.google|www\.facebook)\.com/[\w/]+)"[^<]*</a>(?:</strong>)?\W*</p>\s*$'
            r'|\[/url\]\W*</p>\s*$',
            sites=["raspberrypi.stackexchange.com", "softwarerecs.stackexchange.com"],
            title=False, question=False,
            rule_id="link at end: short answers or [/url], not raspberrypi, softwarerecs")
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
            title=False, question=False,
            rule_id="pattern matching website: .tk at end of post")
# non-linked site at the end of a short answer
create_rule("link at end of {}",
            r'(?is)\b\w{6,}+\.(?:com?|co\.uk|in|io|html?|onl|nl|ir)(?<=^.{0,365})(?:</strong>)?\W*</p>\s*$',
            title=False, question=False,
            rule_id="link at end: non-linked site at the end of a short answer")
# Shortened URL near the end of question
create_rule("shortened URL in {}",
            r"(?is)://(?:w+\.)?" + URL_SHORTENER_REGEX_FRAGMENT + r"/(?=.{0,200}$)",
            sites=["superuser.com", "askubuntu.com"],
            title=False, answer=False,
            rule_id="shortened URL in: questions, not titles, not SU, AU")
# Shortened URL in an answer
create_rule("shortened URL in {}",
            r"(?is)://(?:w+\.)?" + URL_SHORTENER_REGEX_FRAGMENT + r"/",
            sites=["codegolf.stackexchange.com"],
            stripcodeblocks=True, question=False,
            rule_id="shortened URL in: answers, no code, no codegolf")
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
            title=False, stripcodeblocks=True, max_rep=11, max_score=1)
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
            r"(?s)\b1 ?[-(. ]8\d{2}[-). ] ?\d{3}[-. ]\d{4}\b(?<=^.{0,267})",
            sites=["math.stackexchange.com"],
            title=False, stripcodeblocks=False,
            rule_id="phone number detected in: bodies, simplified NorAm number starts with 8 near start, math")
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
            stripcodeblocks=True, question=False,
            rule_id="email in: basic regex, answers, limited sites")
# Email check for questions: check only at the end, and on selected sites
create_rule("email in {}",
            r"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})"
            r"[A-z0-9_.%+-]+\.[A-z]{2,4}\b(?s)(?=.{0,100}$)",
            all=False,
            sites=["money.stackexchange.com", "travel.stackexchange.com", "gamedev.stackexchange.com",
                   "gaming.stackexchange.com"],
            stripcodeblocks=True, answer=False,
            rule_id="email in: basic regex near end, money, travel, gamedev, gaming")
# QQ/ICQ/WhatsApp... numbers, for all sites
create_rule("messaging number in {}",
            r'(?i)(?<![a-z0-9])QQ?(?:(?:\w*[vw]x?|[^a-z0-9])\D{0,8})?\d{5}[.-]?\d{4,5}(?!["\d])|'
            r'\bICQ[ :]{0,5}\d{9}\b|\bwh?atsa+pp?[ :+]{0,5}\d{10}',
            stripcodeblocks=True)


# Homoglyph obfuscation, used both by trolls and spammers
obfuscation_keywords = [
    # Trolls && cussing
    "c" + "ock",
    "c" + "unt",
    "d" + "ick",
    "f" + "uck",
    "mother" + "f" + "ucker",
    "p" + "enis",
    "p" + "ussy",
    "w" + "hore",
    "black helicopters",
    "attack helicopters",

    # Phone support scam
    # Rule only covers single words for the time being
    # Also, comment out really short ones to reduce chance for FPs
    # "amazon prime",
    # "avg",
    "aofexpro.com",
    "bellsouth",
    "binance",
    "crypto.com",
    "coinbase",
    "comcast",
    # "ebay",
    "earthlink",
    "epson",
    # "eset",
    "gemini",
    # "hp printer",
    # "icloud",
    "kraken",
    "mozilla",
    # "msn",
    "norton",
    "paypal",
    "printer",  # maybe remove if we enable "hp printer"
    "quickbooks",
    "roadrunner",
    # "sage",
    "sbcglobal",
    "ticketmaster",
    # "trust wallet",
    "turbotax",
    "uphold",
    "verizon",
    "wallet",  # maybe remove if we enable "trust wallet"

    "airlines",
    "support",
    "phone",
    "number",
    "helpline"
]


# Simple 1337 translator
def create_1337_translation():
    # It is currently relied upon that there are no translation differences between upper and lower case text.
    simple_1337_mapping = {
        '4': 'a',
        '3': 'e',
        '6': 'g',
        '9': 'g',
        '1': 'l',
        '!': 'i',
        '0': 'o',
        '5': 's',
        '$': 's',
        '7': 't',
        '2': 'z',
    }
    for p in punctuation:
        if p not in simple_1337_mapping:
            simple_1337_mapping[p] = ''
    return "".maketrans(simple_1337_mapping)


translation_1337 = create_1337_translation()


@create_rule("obfuscated word in {}", max_rep=50, stripcodeblocks=True)
def obfuscated_word(s, site):
    for word in regex.split(r'[-\s_]+', s):
        # prevent FP on stuff like 'I have this "number": 1111'
        word = word.strip(punctuation).lower()
        translated = word.translate(translation_1337)
        if translated != word and translated in obfuscation_keywords:
            return True, "%r is obfuscated %r" % (word, translated)
    return False, ""


# Category: Trolling
# Offensive title: titles are more sensitive
create_rule("offensive {} detected",
            r"(?i)\bfuck|(?<!brain)fuck(ers?|ing)?\b",
            body=False, max_rep=101, max_score=5,
            rule_id="offensive detected: fuck")
# Numbers-only title
create_rule("numbers-only title",
            r"^(?=.*[0-9])[^\pL]*$",
            sites=["math.stackexchange.com"],
            body=False, max_rep=52, max_score=5)
# Two or more emoji or Unicode symbols in title
create_rule("several emoji in title",
            r"\p{So}\P{So}{0,15}\p{So}",
            body=False, max_rep=52)
# Parenting troll
# This rule is currently broken and detects nothing. It appears it was supposed to be for usernames.
create_rule("bad keyword in {}",
            r"(?i)\b(erica|jeff|er1ca|spam|moderator)\b",
            all=False, sites=["parenting.stackexchange.com"],
            title=False, body_summary=True, max_rep=52,
            rule_id="bad keywords: erica, jeff, er1ca, etc., bodies, parenting")
# Code Review troll
create_rule("bad keyword in {}",
            r"JAMAL",
            all=False, sites=["codereview.stackexchange.com"],
            username=True, body_summary=True,
            rule_id="bad keywords: JAMAL, usernames, bodies, titles, codereview")
# Eggplant emoji
create_rule("potentially bad keyword in {}",
            r"\U0001F346",  # Unicode value for the eggplant emoji
            sites=["es.stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "ja.stackoverflow.com",
                   "rus.stackexchange.com"],
            max_rep=5000, max_score=3,
            rule_id="Potentialy bad keywords: eggplant emoji, not not localized SO, rus")
# Academia kangaroos
create_rule("bad keyword in {}"
            r"(?i)kangaroos",
            all=False, sites=["academia.stackexchange.com"],
            rule_id="bad keywords: kangaroos, academia")
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
            body=False, max_rep=52)
# Title starts and ends with a forward slash
create_rule("title starts and ends with a forward slash",
            r"^\/.*\/$",
            body=False)

# Category: other
create_rule("blacklisted username",
            r'^[A-Z][a-z]{3,7}(19\d{2})$',
            all=False, sites=["drupal.stackexchange.com"],
            title=False, body=False, username=True,
            rule_id="blacklisted username: short w19dd, drupal")
create_rule("blacklisted username",
            r"(?i)^jeff$",
            all=False, sites=["parenting.stackexchange.com"],
            title=False, body=False, username=True,
            rule_id="blacklisted username: jeff, parenting")
create_rule("blacklisted username",
            r"(?i)^keshav$",
            all=False, sites=["judaism.stackexchange.com"],
            title=False, body=False, username=True,
            rule_id="blacklisted username: keshav, judaism")
# Judaism etc troll, 2018-04-18 (see also disabled watch above); disabled 2022-04-02, as there's no TP in 4 years.
create_rule("blacklisted username", r'(?i)^john$', disabled=True,
            all=False,
            sites=['hinduism.stackexchange.com', 'judaism.stackexchange.com', 'islam.stackexchange.com'],
            title=False, body=False, username=True,
            rule_id="blacklisted username: john, hinduism, judaism, islam")
# Workplace troll, 2020-03-28
create_rule("blacklisted username",
            r"(?i)(?:"
            r"raise(?!oul(?<=^samuraiseoul)$)(?!r(?<=^indofraiser)$)(?!lvan(?<=^Santhosh Thamaraiselvan)$)"
            r"|^kilisi$|(?-i:KKK)|darkcygnus|JewsKilledOurLord|(?i:suck(?!s(?<=AgileSucks|ScrumSucks)))"
            r"Matthew Gaiser"
            r")",
            all=False, sites=["workplace.stackexchange.com", "workplace.meta.stackexchange.com"],
            title=False, body=False, username=True,
            max_rep=100, max_score=1,
            rule_id="blacklisted username: troll on workplace")
create_rule("bad keyword in {}",
            r"(?is)(?:^|\b|(?w:\b))"
            r"(?:"  # Begin group of bookended regexes
            r"n[i1]gg+[aeu][rh]?s?|negr[o0]s?|fag+(?:[oe]t)?s?|semen|mindless[\W_]*+morons?"
            r"|meets?[\W_]*+(?:the[\W_]*+)?quality[\W_]*+standards?"
            r"|foreskins?|behead(?:ing|er|ed)"
            r")"
            r"(?:\b|(?w:\b)|$)",
            all=False, sites=["workplace.stackexchange.com", "workplace.meta.stackexchange.com"],
            username=True, body_summary=True,
            max_rep=100, max_score=1,
            rule_id="bad keywords: various bad words, some overlap, workplace")
# Watch poo+p?(?:y|ie)?s? on The Workplace, due to a persistent spammer
create_rule("potentially bad keyword in {}",
            r"(?:"
            r"(?is)(?:^|\b|(?w:\b))"  # Beging bookending
            r"(?:poo+p?(?:y|ie|ed|er)?s?|piss+|pee+"
            r"|(?:smash|slash|behead)(?:ing|ed)?|vandali[sz](ing|ed?)?)"
            r"(?:\b|(?w:\b)|$)"  # End bookending
            r")",
            all=False, sites=["workplace.stackexchange.com", "workplace.meta.stackexchange.com"],
            username=True, body_summary=True,
            max_rep=100, max_score=1,
            rule_id="Potentialy bad keywords: poop, smash, slash, behead, workplace")
# Non-bookended watch for TWP of all-caps posts (currently without any other formatting than <p>).
# This is a separate rule, because it will consume up to 100 characters, which, if not separate,
# will tend to mask other watch matches which we want to show up separately in the why data.
create_rule("potentially bad keyword in {}",
            r"(?:"
            r"(?-i:^(?:<p>[\sA-Z\d.,]{0,100}+)(?=[\sA-Z\d.,]*+<\/p>(?:\s*+<p>[\sA-Z\d.,]*+<\/p>)*$))"
            r")",
            all=False, sites=["workplace.stackexchange.com", "workplace.meta.stackexchange.com"],
            username=True, body_summary=True,
            max_rep=100, max_score=1,
            rule_id="Potentialy bad keywords: only upercase and numbers, workplace")
# TWP: Watch for the re-use of the usernames of the top 100 users by reputation.
create_rule("potentially bad keyword in {}",
            r"(?:"
            r"Joe Strazzere|Kilisi|HLGEM|gnasher729|Kate Gregory|enderland"
            r"|(?-i:^Neo$)"  # Too short/common, but the troll has used it.
            r"|motosubatsu|bethlakshmi"
            r"|Vietnhi Phuvan|nvoigt|Philip Kendall|Lilienthal|DarkCygnus|Wesley Long|DJClayworth|mhoran_psprep"
            # r"|Monica Cellio"  # Too common
            r"|AndreiROM|IDrinkandIKnowThings|Hilmar|Jane S|keshlam|dwizum|Chris E|Sourav Ghosh|Justin Cave"
            r"|thursdaysgeek|sf02|paparazzo|Telastyn|The Wandering Dev Manager|berry120"
            # r"|Myles"  # Too short/common
            # r"|Erik"  # Too short/common
            r"|Dan Pichelman|David K|Philipp|Stephan Branczyk"
            # r"|rath"  # Too short/common
            r"|Patricia Shanahan|Xavier J|O\. Jones|HorusKol|Magisch|PeteCon|NotMe|jcmeloni|mcknz"
            # r"|Oded"  # Too short/common
            r"|Kent A\.|blankip"
            # r"|jmac"  # Too short/common
            r"|GreenMatt|Gregory Currie|pdr|joeqwerty|maple_shaft|Matthew Gaiser"
            # r"|Daniel"  # Too short/common
            r"|Twyxz|BigMadAndy|teego1967|Ertai87|user1666620|Julia Hayward|alroc|Player One|kevin cline|Ben Barden"
            # r"|Kevin"  # Too short/common
            r"|virolino|solarflare|Fattie|Thomas Owens|sevensevens|jcmack|JB King"
            # r"|Dan"  # Too short/common
            r"|PagMax|bharal|SaggingRufus|Karl Bielefeldt|JohnHC|Ed Heal|Jim G\.|cdkMoose"
            # r"|Peter"  # Too short/common
            r"|MrFox|Bill Leeper|SZCZERZO KŁY|Tymoteusz Paul|mxyzplk - SE stop being evil|Sascha|Dawny33"
            r"|A\. I\. Breveleri|Borgh|FrustratedWithFormsDesigner|Dukeling|jimm101"
            r")",
            all=False, sites=["workplace.stackexchange.com", "workplace.meta.stackexchange.com"],
            username=True, body_summary=False, body=False, title=False,
            max_rep=93, max_score=1,
            rule_id="Potentialy bad keywords: high rep user's usernames, workplace")
# Link at beginning of post; pulled from watchlist
create_rule("link at beginning of {}",
            r'(?is)^\s*<p>\s*(?:</?\w+/?>\s*)*<a href="(?!(?:[a-z]+:)?//(?:[^" >/.]*\.)*(?:(?:'
            '' r'quora|medium|googleusercontent|youtube|microsoft|unity3d|'
            '' r'wso|merriam-webster|oracle|magento|example|apple|google|'
            '' r'github|imgur|'
            '' r'stackexchange|stackoverflow|serverfault|superuser|askubuntu)\.com|'
            r'(?:(?:lvcharts|php|jsfiddle|mathoverflow)\.net)|'
            r'github\.io|youtu\.be|edu|'
            r'(?:(?:arxiv|drupal|python|isc|khronos|mongodb|open-std|dartlang|'
            '' r'apache|pydata|gnu|js|wordpress|wikipedia)\.org))'
            r'[/\"])[^"]*+"(?![\W\w]*?</(?:code|blockquote)>)',
            title=False, username=False, body=True,
            max_rep=32, max_score=1)
# MSE: Watch for usernames
create_rule("potentially bad keyword in {}",
            r"^no one$",
            all=False, sites=["meta.stackexchange.com"],
            username=True, body_summary=False, body=False, title=False,
            max_rep=33, max_score=1,
            rule_id="Potentialy bad keywords: username: no one, MSE")
# Non-bookended watch for usernames
create_rule("potentially bad keyword in {}",
            r"(?i)(?:"
            r"(?:it\W*(?:'?s|is))?\W*(?:\\_?/\W*|w)+[\.\W]*(?:[eé3_ëêẽ]+\W*"
            r"(?:[s5]\W*[l1]\W*|[l1]\W*[s5]\W*)+[eé3_ëêẽ]\W*.?)\W*"
            r"(?:.*[a@]t?(?:\\_?/\W*|w)*\W*[0oøuüôöõ]{2}\W*d)"
            r")",
            all=True,
            username=True, body_summary=False, body=False, title=False,
            max_rep=33, max_score=1,
            rule_id="Potentialy bad keywords: usernames: Wesley")
# Politics: specific content; requested by mods
create_rule("potentially bad keyword in {}",
            r"،",
            all=False, sites=["politics.stackexchange.com", "politics.meta.stackexchange.com"],
            username=True, body_summary=True, body=True, title=True,
            max_rep=93, max_score=21,
            rule_id="Potentialy bad keywords: specific Unicode character, politics")
# Worldbuilding: specific content
create_rule("potentially bad keyword in {}",
            r"(?i)(?:\bl[\W_]*+dut?ch\b|/a/214453\b)",
            all=False, sites=["worldbuilding.stackexchange.com", "worldbuilding.meta.stackexchange.com"],
            username=False, body_summary=True, body=True, title=False,
            max_rep=93, max_score=21,
            rule_id="Potentialy bad keywords: l dutch, answer 214453, worldbuilding")
# japanese.se: specific content in usernames
create_rule("potentially bad keyword in {}",
            r"(?i)(?:kukel|ricebag)",
            all=False, sites=["japanese.stackexchange.com", "japanese.meta.stackexchange.com"],
            username=True, body_summary=False, body=False, title=False,
            max_rep=93, max_score=21,
            rule_id="Potentialy bad keywords: usernames: kukel on japanese.se")

FindSpam.reload_blacklists()
