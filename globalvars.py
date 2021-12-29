# -*- coding: utf-8 -*-

import sys
import os
from collections import namedtuple
from datetime import datetime
from html.parser import HTMLParser
from html import unescape
from hashlib import md5
from configparser import NoOptionError, ConfigParser
import threading
import subprocess as sp
import platform
import copy

# noinspection PyCompatibility
import regex
if 'windows' in platform.platform().lower():
    # noinspection PyPep8Naming
    from _Git_Windows import git, GitError
else:
    # noinspection PyUnresolvedReferences
    from sh.contrib import git


CommitInfo = namedtuple('CommitInfo', ['id', 'id_full', 'author', 'message'])

git_url = git.config("--get", "remote.origin.url").strip()
git_url_split = git_url.split("/")
git_user_repo = "Charcoal-SE/SmokeDetector"
if git_url[0:19] == "https://github.com/":
    git_user_repo = "{}/{}".format(git_url_split[3], git_url_split[4][0:-4])


def git_commit_info():
    try:
        data = sp.check_output(['git', 'rev-list', '-1', '--pretty=%h%n%H%n%an%n%s', 'HEAD'],
                               stderr=sp.STDOUT).decode('utf-8')
    except sp.CalledProcessError as e:
        raise OSError("Git error:\n" + e.output) from e
    _, abbrev_id, full_id, author, message = data.strip().split("\n")
    return CommitInfo(id=abbrev_id, id_full=full_id, author=author, message=message)


def git_ref():
    git_cp = sp.run(['git', 'symbolic-ref', '--short', '-q', 'HEAD'], stdout=sp.PIPE)
    return git_cp.stdout.decode("utf-8").strip()  # not on branch = empty output


# We don't need strip_escape_chars() anymore, see commit message
# of 1931d30804a675df07887ce0466e558167feae57


# noinspection PyClassHasNoInit,PyDeprecation,PyUnresolvedReferences
class GlobalVars:
    on_windows = 'windows' in platform.platform().lower()

    false_positives = []
    whitelisted_users = set()
    blacklisted_users = dict()
    blacklisted_usernames = []
    blacklisted_websites = []
    # set() with the processed version of each blacklisted number pattern.
    blacklisted_numbers = None
    # blacklisted_numbers_raw is a list with the raw patterns read from the blacklisted_numbers.txt file.
    blacklisted_numbers_raw = None
    # set() with the processed version of each watched number pattern.
    watched_numbers = None
    # watched_numbers_raw is a dict() with the keys the raw patterns, with properties
    # for the user and time the pattern was added. Insertion order represents the order of the patterns in the
    # watched_numbers.txt
    watched_numbers_raw = None
    # set() with the normalized, including deobfuscated and normalized, versions of the patterns.
    blacklisted_numbers_normalized = None
    watched_numbers_normalized = None
    # The _full versions are a dict() with key=raw pattern, with tuple with processed and normalized for each.
    # Insertion order is the order they are in within the file.
    blacklisted_numbers_full = None
    watched_numbers_full = None
    bad_keywords = []
    watched_keywords = {}
    ignored_posts = []
    auto_ignored_posts = []
    startup_utc_date = datetime.utcnow()
    startup_utc = startup_utc_date.strftime("%H:%M:%S")
    latest_questions = []
    latest_questions_lock = threading.Lock()
    # recently_scanned_posts is not stored upon abnormal exit (exceptions, ctrl-C, etc.).
    recently_scanned_posts = {}
    recently_scanned_posts_lock = threading.Lock()
    recently_scanned_posts_retention_time = 24 * 60 * 60  # 24 hours
    api_backoff_time = 0
    deletion_watcher = None

    not_privileged_warning = \
        "You are not a privileged user. Please see " \
        "[the privileges wiki page](https://charcoal-se.org/smokey/Privileges) for " \
        "information on what privileges are and what is expected of privileged users."

    experimental_reasons = {  # Don't widely report these
        "potentially bad keyword in answer",
        "potentially bad keyword in body",
        "potentially bad keyword in title",
        "potentially bad keyword in username",
        "potentially bad NS for domain in title",
        "potentially bad NS for domain in body",
        "potentially bad NS for domain in answer",
        "potentially bad ASN for hostname in title",
        "potentially bad ASN for hostname in body",
        "potentially bad ASN for hostname in answer",
        "potentially bad IP for hostname in title",
        "potentially bad IP for hostname in body",
        "potentially bad IP for hostname in answer",
        "potentially problematic NS configuration in title",
        "potentially problematic NS configuration in body",
        "potentially problematic NS configuration in answer",
        "toxic body detected",
        "toxic answer detected",
    }

    parser = HTMLParser()
    parser.unescape = unescape

    code_privileged_users = None

    # these are loaded in GlobalVars.reload()
    commit = None
    commit_with_author = None
    on_branch = None

    s = ""
    s_reverted = ""
    s_norestart_blacklists = ""
    s_norestart_findspam = ""
    apiquota = -1
    bodyfetcher = None
    cookies = {}
    se_sites = []
    why_data = []
    notifications = []
    listen_to_these_if_edited = []
    multiple_reporters = []
    api_calls_per_site = {}
    reason_weights = {}
    metasmoke_ids = {}

    standby_message = ""
    standby_mode = False
    no_se_activity_scan = False
    no_deletion_watcher = False
    no_edit_watcher = False

    ignore_no_se_websocket_activity_lock = threading.Lock()
    ignore_no_se_websocket_activity = False

    api_request_lock = threading.Lock()  # Get this lock before making API requests
    apiquota_rw_lock = threading.Lock()  # Get this lock before reading/writing apiquota
    # The following is a filter for the SE API to use on /questions, /answers, and /posts routes, which
    # returns consistent data for all three types of requests, as far as that is possible.
    # However, it should be noted that some of the fields which are available in the /questions and /answers
    # routes are not available when the same post is obtained through the /posts routes.
    # Our primary scanning is done based on responses to the /questions route. In general, data should be
    # obtained from that route when possible. Unfortunately, there isn't a good way to go from just a post_id
    # to both knowing that it's a question or answer and having the posts full data.
    # [Note: URL decoding can't actually be relied upon to determine if a post is a question or answer, because the
    # /a and /q main/meta site routes take a post ID and return whichever of question or answer it is.]
    # The best case is that we know or guess that the post is either a question or answer and we request it
    # accurately from the correct route. However, for scanning posts, we also want the question data associated
    # with an answer.
    se_api_question_answer_post_filter = \
        "!7bj2kejr9-Tmw-wWkT)JQ1T3qUUB9KLZAB0TT-dWOwUFyqxVII1y.BH6Ji(.pwih1odhF-wr29R*Jbti"

    class PostScanStat:
        """ Tracking post scanning data """
        # All stats in a key are reported into chat using the !!/stats command. The report_order_with_defaults
        # variable in the code for that command shows what's expected to be here, but other values could exist.
        # Stats are accumulated unless the stats set is locked.
        # The default stat set is "uptime".

        # Setting up the stats dict with default values isn't needed. If a key/value pair is in the new_stats
        # sent to add(), then it will be automatically added. The list here is merely to document the
        # keys and values which are currently expected.
        default_stats = {
            'scan_time': 0,
            'posts_scanned': 0,
            'grace_period_edits': 0,
            'unchanged_questions': 0,
            'unchanged_answers': 0,
            'no_post_lock': 0,
            'errors': 0,
            'max_scan_time': 0,
            'max_scan_time_post': '',
        }
        # stats is a dict of stat_sets, which use keys as the name of the set of stats. The default keys are
        # 'all', 'uptime', and 'ms'.
        # Each stat set is a dict with keys: 'stats', 'start_timestamp', and optionally 'locked_timestamp'.
        # If the stats set is locked, the optional 'locked_timestamp' key exists and has a datetime value.
        # All of the actual stats are in the dict which is stored in the 'stats' key.
        stats = {}
        rw_lock = threading.Lock()

        @staticmethod
        def add(new_stats):
            """ Add post scanning data """
            with GlobalVars.PostScanStat.rw_lock:
                dict_of_stat_sets = GlobalVars.PostScanStat.stats
                # First, deal with all stats which are not simple accumulators
                new_max_time = new_stats.pop('max_scan_time', 0)
                new_max_time_post = new_stats.pop('max_scan_time_post', '')
                for stat_set in dict_of_stat_sets.values():
                    # MS wants only posts_scanned, scan_time, posts_per_second, but it doesn't hurt to also
                    # keep any additional ones.
                    if not stat_set.get('locked_timestamp', False):
                        these_stats = stat_set['stats']
                        if new_max_time > these_stats.get('max_scan_time', 0):
                            these_stats['max_scan_time'] = new_max_time
                            these_stats['max_scan_time_post'] = new_max_time_post
                        for stat_name, value in new_stats.items():
                            old_value = these_stats.get(stat_name, 0)
                            if type(value) in [int, float]:
                                these_stats[stat_name] = old_value + value
                            else:
                                # There isn't any value currently used here which should be anything other than an int
                                # or float, but, just in case, we directly replace values which aren't int or float.
                                these_stats[stat_name] = value

        @staticmethod
        def get_stats_for_ms(reset=False):
            """ Get post scanning statistics for reporting to MS """
            stats_copy = GlobalVars.PostScanStat.get('ms', reset=reset)
            # MS wants only posts_scanned, scan_time, posts_per_second
            return (stats_copy.get(key, 0) for key in ['posts_scanned', 'scan_time', 'posts_per_second'])

        @staticmethod
        def get(stats_set_key='uptime', reset=False):
            """ Get post scanning statistics from a stat set, including derived data, start and lock timestamps. """
            with GlobalVars.PostScanStat.rw_lock:
                stats_set = copy.deepcopy(GlobalVars.PostScanStat.stats[stats_set_key])
                if reset is True:
                    GlobalVars.PostScanStat._reset(stats_set_key)
            stats_copy = stats_set['stats']
            # Derived values:
            scan_time = stats_copy.get('scan_time', 0)
            posts_scanned = stats_copy.get('posts_scanned', 0)
            if scan_time == 0:
                stats_copy['posts_per_second'] = None
            else:
                stats_copy['posts_per_second'] = posts_scanned / scan_time
            # Stats which are properties of the stat_set
            stats_copy['start_timestamp'] = stats_set['start_timestamp']
            locked_timestamp = stats_set.get('locked_timestamp', None)
            if locked_timestamp:
                stats_copy['locked_timestamp'] = locked_timestamp
            return stats_copy

        @staticmethod
        def _reset(stats_set_key):
            """ Resets/clears/creates post scanning data in a stats set without getting the rw_lock """
            GlobalVars.PostScanStat.stats[stats_set_key] = {}
            GlobalVars.PostScanStat.stats[stats_set_key]['stats'] = GlobalVars.PostScanStat.default_stats.copy()
            GlobalVars.PostScanStat.stats[stats_set_key]['start_timestamp'] = datetime.utcnow()

        @staticmethod
        def reset(stats_set_key):
            """ Resets/clears/creates post scanning data in a stats set """
            with GlobalVars.PostScanStat.rw_lock:
                GlobalVars.PostScanStat._reset(stats_set_key)

        @staticmethod
        def lock(stats_set_key):
            """ Locks post scanning data in a stats set """
            with GlobalVars.PostScanStat.rw_lock:
                GlobalVars.PostScanStat.stats[stats_set_key]['locked_timestamp'] = datetime.utcnow()

        @staticmethod
        def unlock(stats_set_key):
            """ Unlocks post scanning data in a stats set """
            with GlobalVars.PostScanStat.rw_lock:
                GlobalVars.PostScanStat.stats[stats_set_key].pop('locked_timestamp', None)

        @staticmethod
        def delete(stats_set_key):
            """ Deletes a stats set """
            with GlobalVars.PostScanStat.rw_lock:
                GlobalVars.PostScanStat.stats.pop(stats_set_key, None)

        @staticmethod
        def copy(from_type, to_type):
            """ Copies the contents of a stat set to another stat set key """
            with GlobalVars.PostScanStat.rw_lock:
                GlobalVars.PostScanStat.stats[to_type] = copy.deepcopy(GlobalVars.PostScanStat.stats[from_type])

        @staticmethod
        def create(stats_set_key):
            """ Creates a stat set (identical to a reset) """
            GlobalVars.PostScanStat.reset[stats_set_key]

        @staticmethod
        def get_set_keys():
            """ Get a list of the available stat set keys """
            with GlobalVars.PostScanStat.rw_lock:
                keys = list(GlobalVars.PostScanStat.stats.keys())
            return keys

        @staticmethod
        def reset_ms_stats():
            """ Reset post scanning data for MS """
            GlobalVars.PostScanStat.reset('ms')

    config_parser = ConfigParser(interpolation=None)

    if os.path.isfile('config') and "pytest" not in sys.modules:
        config_parser.read('config')
    else:
        config_parser.read('config.ci')

    config = config_parser["Config"]  # It's a collections.OrderedDict now

    site_id_dict = {}
    site_id_dict_by_id = {}
    site_id_dict_timestamp = 0
    site_id_dict_issues_into_chat_timestamp = 0
    site_id_dict_lock = threading.Lock()

    post_site_id_to_question = {}

    location = config.get("location", "Continuous Integration")

    # DNS Configuration
    # Configure resolver based on config options, or System, configure DNS Cache in
    # thread-safe cache as part of dnspython's resolver system as init options,
    # control cleanup interval based on **TIME** like a regular DNS server does.
    #
    # # Explicitly defining fallback= for fallback values in bool and float getters, in order to
    # #    avoid IDE complaints -- tward
    dns_nameservers = config.get("dns_resolver", "system").lower()
    dns_cache_enabled = config.getboolean("dns_cache_enabled", fallback=True)
    dns_cache_interval = config.getfloat("dns_cache_cleanup_interval", fallback=300.0)

    class MSStatus:
        """ Tracking metasmoke status """
        ms_is_up = True
        counter = 0
        rw_lock = threading.Lock()

        @staticmethod
        def set_up():
            """ Set metasmoke status to up """
            # Private to metasmoke.py
            with GlobalVars.MSStatus.rw_lock:
                GlobalVars.MSStatus.ms_is_up = True

        @staticmethod
        def set_down():
            """ Set metasmoke status to down """
            # Private to metasmoke.py
            with GlobalVars.MSStatus.rw_lock:
                GlobalVars.MSStatus.ms_is_up = False

        @staticmethod
        def is_up():
            """ Query if metasmoke status is up """
            with GlobalVars.MSStatus.rw_lock:
                current_ms_status = GlobalVars.MSStatus.ms_is_up
            return current_ms_status

        @staticmethod
        def is_down():
            """ Query if metasmoke status is down """
            return not GlobalVars.MSStatus.is_up()

        # Why implement failed() and succeeded() here, as they will only be called in metasmoke.py?
        # Because get_failure_count() need to be exposed to global, so it is more convenient
        # to implement failed() and succeeded() here.
        @staticmethod
        def failed():
            """ Indicate a metasmoke connection failure """
            with GlobalVars.MSStatus.rw_lock:
                GlobalVars.MSStatus.counter += 1

        @staticmethod
        def succeeded():
            """ Indicate a metasmoke connection success """
            with GlobalVars.MSStatus.rw_lock:
                GlobalVars.MSStatus.counter = 0

        @staticmethod
        def get_failure_count():
            """ Get consecutive metasmoke connection failure count """
            with GlobalVars.MSStatus.rw_lock:
                failure_count = GlobalVars.MSStatus.counter
            return failure_count

        @staticmethod
        def reset_ms_status():
            """ Reset class GlobalVars.MSStatus to default values """
            with GlobalVars.MSStatus.rw_lock:
                GlobalVars.MSStatus.ms_is_up = True
                GlobalVars.MSStatus.counter = 0

    chatexchange_u = config.get("ChatExchangeU")
    chatexchange_p = config.get("ChatExchangeP")

    metasmoke_host = config.get("metasmoke_host")
    metasmoke_key = config.get("metasmoke_key")
    metasmoke_ws_host = config.get("metasmoke_ws_host")

    git_name = config.get("git_username", "SmokeDetector")
    git_email = config.get("git_useremail", "smokey@erwaysoftware.com")

    github_username = config.get("github_username")
    github_password = config.get("github_password")
    github_access_token = config.get("github_access_token")

    perspective_key = config.get("perspective_key")

    flovis_host = config.get("flovis_host")
    flovis = None

    # Miscellaneous
    log_time_format = config.get("log_time_format", "%H:%M:%S")

    # Blacklist privileged users from config
    se_blacklisters = regex.sub(r"[^\d,]", "", config.get("se_blacklisters", "")).split(",")
    mse_blacklisters = regex.sub(r"[^\d,]", "", config.get("mse_blacklisters", "")).split(",")
    so_blacklisters = regex.sub(r"[^\d,]", "", config.get("so_blacklisters", "")).split(",")

    # Create a set of blacklisters equivalent to what's used in code_privileged_users.
    config_blacklisters = set()
    for id in se_blacklisters:
        if id:
            config_blacklisters.add(("stackexchange.com", int(id)))

    for id in mse_blacklisters:
        if id:
            config_blacklisters.add(("meta.stackexchange.com", int(id)))

    for id in so_blacklisters:
        if id:
            config_blacklisters.add(("stackoverflow.com", int(id)))

    # If the config has it, get a list of the detection reasons which are considered valid.
    # The list is semicolon separated.
    valid_detection_reasons = config.get("valid_detection_reasons", None)
    if valid_detection_reasons is not None:
        valid_detection_reasons = valid_detection_reasons.split(";")

    # If the config has it, get a list of the detection IDs which are considered valid.
    # The list is semicolon separated.
    valid_rule_ids = config.get("valid_rule_ids", None)
    if valid_rule_ids is not None:
        valid_rule_ids = valid_rule_ids.split(";")

    # Additional text to send to chat when this instance receives a "failover" from MS:
    # If present at the start and end of the string in the config file, a single ["'] character is stripped from
    # both the start and end of the value. This allows the value in the config file to be enclosed in quotes
    # to preserve leading whitespace, but also permit the string to contain those characters.
    additional_failover_text = regex.sub(r'''^['"](.*)['"]$''', r'\1', config.get("additional_failover_text", ""))

    # environ_or_none replaced by os.environ.get (essentially dict.get)
    bot_name = os.environ.get("SMOKEDETECTOR_NAME", git_name)
    bot_repo_slug = os.environ.get("SMOKEDETECTOR_REPO", git_user_repo)
    bot_repository = "//github.com/{}".format(bot_repo_slug)
    chatmessage_prefix = "[{}]({})".format(bot_name, bot_repository)

    valid_content = """This is a totally valid post that should never be caught. Any blacklist or watchlist item that triggers on this item should be avoided. java.io.BbbCccDddException: nothing wrong found. class Safe { perfect valid code(int float &#%$*v a b c =+ /* - 0 1 2 3 456789.EFGQ} English 中文Français Español Português Italiano Deustch ~@#%*-_/'()?!:;" vvv kkk www sss ttt mmm absolute std::adjacent_find (power).each do |s| bbb end ert zal l gsopsq kdowhs@ xjwk* %_sooqmzb xjwpqpxnf.  Please don't blacklist disk-partition.com, it's a valid domain (though it also gets spammed rather frequently)."""  # noqa: E501

    @classmethod
    def reload(cls):
        cls.commit = commit = git_commit_info()

        cls.commit_with_author = "`{}` ({}: {})".format(
            commit.id, commit.author, commit.message)

        # We don't want to escape `[` and `]` when they are within code.
        split_commit_with_author = cls.commit_with_author.split('`')
        split_length = len(split_commit_with_author)
        for index in range(0, split_length, 2):
            split_commit_with_author[index] = split_commit_with_author[index].replace('[', '\\[').replace(']', '\\]')
        # There's not an even number of ` characters, so the parsing hack failed, but we assume the last one needs
        # escaping.
        if not split_length % 2:
            split_commit_with_author[-1] = split_commit_with_author[-1].replace('[', '\\[').replace(']', '\\]')

        cls.commit_with_author_escaped = '`'.join(split_commit_with_author)

        cls.on_branch = git_ref()
        cls.s = "[ {} ] SmokeDetector started at [rev {}]({}/commit/{}) (running on {}, Python {})".format(
            cls.chatmessage_prefix, cls.commit_with_author_escaped, cls.bot_repository,
            cls.commit.id, cls.location, platform.python_version())
        cls.s_reverted = \
            "[ {} ] SmokeDetector started in [reverted mode](" \
            "https://charcoal-se.org/smokey/SmokeDetector-Statuses#reverted-mode) " \
            "at [rev {}]({}/commit/{}) (running on {})".format(
                cls.chatmessage_prefix, cls.commit_with_author_escaped, cls.bot_repository,
                cls.commit.id, cls.location)
        cls.s_norestart_blacklists = \
            "[ {} ] Blacklists reloaded at [rev {}]({}/commit/{}) (running on {})".format(
                cls.chatmessage_prefix, cls.commit_with_author_escaped, cls.bot_repository,
                cls.commit.id, cls.location)
        cls.s_norestart_findspam = \
            "[ {} ] FindSpam module reloaded at [rev {}]({}/commit/{}) (running on {})".format(
                cls.chatmessage_prefix, cls.commit_with_author_escaped, cls.bot_repository,
                cls.commit.id, cls.location)
        cls.standby_message = \
            "[ {} ] SmokeDetector started in [standby mode](" \
            "https://charcoal-se.org/smokey/SmokeDetector-Statuses#standby-mode) " \
            "at [rev {}]({}/commit/{}) (running on {})".format(
                cls.chatmessage_prefix, cls.commit_with_author_escaped, cls.bot_repository,
                cls.commit.id, cls.location)


for stats_set_key in ['all', 'uptime', 'ms']:
    GlobalVars.PostScanStat.reset(stats_set_key)
GlobalVars.MSStatus.reset_ms_status()
GlobalVars.reload()
