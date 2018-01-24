# coding=utf-8
# noinspection PyCompatibility
import regex
from globalvars import GlobalVars
import datahandling


# noinspection PyBroadException,PyMissingTypeHints
def get_user_from_url(url):
    match = regex.compile(r"(?:https?:)?//([\w.]+)/u(?:sers)?/(\d+)(/(?:.+/?)?)?").search(url)
    if match is None:
        return None
    try:
        site = match.group(1)
        user_id = match.group(2)
        return user_id, site
    except:
        return None


# noinspection PyBroadException
def get_api_sitename_from_url(url):
    match = regex.compile(r"(?:https?:)?(?://)?([\w.]+)/?").search(url)
    if match is None:
        return None
    try:
        if match.group(1) == 'mathoverflow.net':
            return 'mathoverflow.net'
        else:
            return match.group(1).split('.')[0]
    except:
        return None


# noinspection PyBroadException,PyMissingTypeHints
def fetch_post_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\)(?: \| \[.+\]\(.+\))? \] [\w\s,:+\(\)-]+: \[.+]\(((?:http:)" \
                   r"?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)(?:\?smokeypost=true)?\)" \
                   r" by \[?.*\]?\(?(?:.*)\)? on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    match = regex.compile(search_regex).search(content)
    if match is None:
        return None
    try:
        url = match.group(1)
        return url
    except:
        return None


# noinspection PyBroadException,PyUnusedLocal,PyRedundantParentheses,PyMissingTypeHints
def fetch_post_id_and_site_from_url(url):
    if url is None:
        return None
    trimmed_url = url.replace("&zwnj;&#8203;", "")
    post_type_regex = r"\/\d+(&zwnj;&#8203;\d+)?#\d+$"
    post_type = ""
    search_regex = ""
    if regex.compile(post_type_regex).search(trimmed_url):
        post_type = "answer"
        search_regex = r"^(?:https?:)?\/\/([\w.]+)\/questions\/\d+\/.+\/(\d+(&zwnj;&#8203;\d+)?)#\d+$"
    else:
        post_type = "question"
        search_regex = r"^(?:https?:)?\/\/([\w.]+)/questions/(\d+)(?:/.*)?$"
    found = regex.compile(search_regex).search(trimmed_url)
    if found is not None:
        try:
            post_id = found.group(2)
            post_site = found.group(1)
            return (post_id, post_site, post_type)
        except:
            return None
    search_regex = r"^(?:https?:)?\/\/([\w.]+)/(q|a)/(\d+)(?:/\d+)?/?"
    found = regex.compile(search_regex).search(trimmed_url)
    if found is None:
        return None
    try:
        post_id = found.group(3)
        post_site = found.group(1)
        post_type = "question" if found.group(2) == "q" else "answer"
        return (post_id, post_site, post_type)
    except:
        return None


# noinspection PyMissingTypeHints
def fetch_post_id_and_site_from_msg_content(content):
    url = fetch_post_url_from_msg_content(content)
    return fetch_post_id_and_site_from_url(url)


# noinspection PyBroadException,PyMissingTypeHints
def fetch_owner_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\)(?: \| \[.+\]\(.+\))? \] [\w\s,:+\(\)-]+: \[.+]\((?:(?:http:)" \
                   r"?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\) by \[.+\]\((.+)\)" \
                   r" on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    match = regex.compile(search_regex).search(content)
    if match is None:
        return None
    try:
        owner_url = match.group(1)
        return owner_url
    except:
        return None


# noinspection PyBroadException,PyMissingTypeHints
def fetch_title_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\)(?: \| \[.+\]\(.+\))? \] [\w\s,:+\(\)-]+: \[(.+)]\((?:(?:http:)" \
                   r"?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\) by \[?.*\]?\(?.*\)?" \
                   r" on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    match = regex.compile(search_regex).search(content)
    if match is None:
        return None
    try:
        title = match.group(1)
        return title
    except:
        return None


# noinspection PyBroadException,PyMissingTypeHints
def edited_message_after_postgone_command(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\)(?: \| \[.+\]\(.+\))? \] [\w\s,:+\(\)-]+: (\[.+]\((?:(?:http:)" \
                   r"?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\)) by \[?.*\]?\(?.*\)?" \
                   r" on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    match = regex.compile(search_regex).search(content)
    if match is None:
        return None
    try:
        link = match.group(1)
        return content.replace(link, "*(gone)*")
    except:
        return None


# noinspection PyMissingTypeHints
def unescape_title(title_escaped):
    return GlobalVars.parser.unescape(title_escaped).strip()


# noinspection PyMissingTypeHints
def escape_special_chars_in_title(title_unescaped):
    return regex.sub(r"([_*\\`\[\]])", r"\\\1", title_unescaped)


# noinspection PyMissingTypeHints
def get_user_from_list_command(cmd):  # for example, !!/addblu is a list command
    cmd_merged_spaces = regex.sub("\\s+", " ", cmd)
    cmd_parts = cmd_merged_spaces.split(" ")

    uid = -1
    site = ""

    if len(cmd_parts) == 1:
        uid_site = get_user_from_url(cmd_parts[0])
        if uid_site is not None:
            uid, site = uid_site
    elif len(cmd_parts) == 2:
        uid = cmd_parts[0]
        site = cmd_parts[1]
        digit_re = regex.compile("^[0-9]+$")
        site_re = regex.compile(r"^(\w+\.stackexchange\.com|\w+\.(com|net))$")
        if not digit_re.match(uid):
            uid = -1
            site = ""
        elif not site_re.match(site):
            exists, name = datahandling.check_site_and_get_full_name(site)
            if exists:
                return uid, name
            else:
                return -2, name
    return uid, site


# noinspection PyMissingTypeHints
def url_to_shortlink(url):
    id_and_site = fetch_post_id_and_site_from_url(url)
    if id_and_site is None:
        return url
    if id_and_site[2] == "question":
        return "http://{}/questions/{}".format(id_and_site[1], id_and_site[0])
        # We're using "/questions" and not "/q" here because when the URL
        # is made protocol-relative, /q would redirect to http even if the
        # shortlink is https. Same for /a. But there we still use /a because
        # there is no /answers or something like that.
    else:
        return "http://{}/a/{}".format(id_and_site[1], id_and_site[0])


# noinspection PyMissingTypeHints
def user_url_to_shortlink(url):
    user_id_and_site = get_user_from_url(url)
    if user_id_and_site is None:
        return url
    return "http://{}/users/{}".format(user_id_and_site[1], user_id_and_site[0])


# noinspection PyMissingTypeHints
def to_protocol_relative(url):
    if url.startswith("http://"):
        return url[5:]
    elif url.startswith("https://"):
        return url[6:]
    else:
        return url
