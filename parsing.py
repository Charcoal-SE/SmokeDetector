# coding=utf-8
# noinspection PyCompatibility
import regex
import globalvars
import datahandling


# noinspection PyMissingTypeHints
def rebuild_str(s):
    return s.replace("\u200B", "").replace("\u200C", "")


# noinspection PyBroadException,PyMissingTypeHints
def get_user_from_url(url):
    if url is None:
        return None
    match = regex.compile(r"(?:https?:)?//([\w.]+)/u(?:sers)?/(\d+)(/(?:.+/?)?)?").search(url)
    if match is None:
        return None
    try:
        site = match.group(1)
        user_id = match.group(2)
        return user_id, site
    except IndexError:
        return None


# noinspection PyBroadException,PyMissingTypeHints
def get_api_sitename_from_url(url):
    match = regex.compile(r"(?:https?:)?(?://)?([\w.]+)/?").search(url)
    if match is None:
        return None
    try:
        domain = match.group(1)
        return domain.replace('.stackexchange.com', '').replace('.com', '')
    except IndexError:
        return None


# noinspection PyMissingTypeHints
def api_parameter_from_link(link):
    match = regex.compile(
        r'((?:meta\.)?(?:(?:(?:math|(?:\w{2}\.)?stack)overflow|askubuntu|superuser|serverfault)|\w+)'
        r'(?:\.meta)?)\.(?:stackexchange\.com|com|net)').search(link)
    exceptions = {
        'meta.superuser': 'meta.superuser',
        'meta.serverfault': 'meta.serverfault',
        'meta.askubuntu': 'meta.askubuntu',
        'mathoverflow': 'mathoverflow.net',
        'meta.mathoverflow': 'meta.mathoverflow.net',
        'meta.stackexchange': 'meta'
    }
    if match:
        if match[1] in exceptions:
            return exceptions[match[1]]
        elif 'meta.' in match[1] and 'stackoverflow' not in match[1]:
            return '.'.join(match[1].split('.')[::-1])
        else:
            return match[1]
    else:
        return None


# noinspection PyMissingTypeHints
def post_id_from_link(link):
    match = regex.compile(r'(?:https?:)?//[^/]+/\w+/(\d+)').search(link)
    if match:
        return match[1]
    else:
        return None


# noinspection PyMissingTypeHints
def to_metasmoke_link(post_url, protocol=True):
    return "{}//m.erwaysoftware.com/posts/uid/{}/{}".format(
        "https:" if protocol else "", api_parameter_from_link(post_url),
        post_id_from_link(post_url))


# Use (?P<name>) so we're not in the danger of messing up numeric groups
msg_parser_regex = (
    r"^\[ \[SmokeDetector\]\([^)]*\)(?: \| \[.+\]\(.+\))? \] [\w\s,:+\(\)*-]+: "
    r"(?P<post>\[(?P<title>.+)]\((?P<post_url>(?:https?:)"
    r"?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:https?:)?\/\/[\w.]+\/[qa]\/\d+/?)\).{0,3})"
    r" by (?:\[.+\]\((?P<owner_url>.+)\)|[\w ]*) on `[\w.]+`(?: \((?:@\S+\s?)+\))?"
    r"(?: \[.+\]\(.+\))?$"
)
msg_parser = regex.compile(msg_parser_regex)


# noinspection PyBroadException,PyMissingTypeHints
def fetch_post_url_from_msg_content(content):
    match = msg_parser.search(content)
    if match is None:
        return None
    try:
        return match.group("post_url")
    except IndexError:
        return None


# noinspection PyBroadException,PyUnusedLocal,PyRedundantParentheses,PyMissingTypeHints
def fetch_post_id_and_site_from_url(url):
    if url is None:
        return None
    trimmed_url = rebuild_str(url)
    post_type_regex = r"(?:\/\d+)?#\d+$"
    post_type = ""
    search_regex = ""
    if regex.compile(post_type_regex).search(trimmed_url):
        post_type = "answer"
        search_regex = r"^(?:https?:)?\/\/([\w.]+)\/questions\/\d+\/.+[/#](\d+)(?:#\d+)?$"
    else:
        post_type = "question"
        search_regex = r"^(?:https?:)?\/\/([\w.]+)/(?:questions|staging-ground)/(\d+)(?:/.*)?$"
    found = regex.compile(search_regex).search(trimmed_url)
    if found is not None:
        try:
            post_id = found.group(2)
            post_site = found.group(1)
            return (post_id, post_site, post_type)
        except IndexError:
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
    except IndexError:
        return None


# noinspection PyMissingTypeHints
def fetch_post_id_and_site_from_msg_content(content):
    url = fetch_post_url_from_msg_content(content)
    return fetch_post_id_and_site_from_url(url)


# noinspection PyBroadException,PyMissingTypeHints
def fetch_owner_url_from_msg_content(content):
    match = msg_parser.search(content)
    if match is None:
        return None
    try:
        owner_url = match.group("owner_url")
        return owner_url
    except IndexError:
        return None


# noinspection PyBroadException,PyMissingTypeHints
def fetch_title_from_msg_content(content):
    match = msg_parser.search(content)
    if match is None:
        return None
    try:
        return match.group("title")
    except IndexError:
        return None


# noinspection PyBroadException,PyMissingTypeHints
def edited_message_after_postgone_command(content):
    match = msg_parser.search(content)
    if match is None:
        return None
    try:
        link = match.group("post")
        return content.replace(link, "*(gone)*")
    except IndexError:
        return None


# noinspection PyMissingTypeHints
def unescape_title(title_escaped):
    return globalvars.GlobalVars.parser.unescape(title_escaped).strip()


# noinspection PyMissingTypeHints
def escape_markdown(s):
    return regex.sub(r"([_*`\[\]])", r"\\\1", s)


# noinspection PyMissingTypeHints
def sanitize_title(title_unescaped):
    return regex.sub('(https?://|\n)', '', escape_markdown(title_unescaped).replace('\n', u'\u23CE'))


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
        return None
    if id_and_site[2] == "question":
        return "https://{}/questions/{}".format(id_and_site[1], id_and_site[0])
        # We're using "/questions" and not "/q" here because when the URL
        # is made protocol-relative, /q would redirect to http even if the
        # shortlink is https. Same for /a. But there we still use /a because
        # there is no /answers or something like that.
    else:
        return "https://{}/a/{}".format(id_and_site[1], id_and_site[0])


# noinspection PyMissingTypeHints
def user_url_to_shortlink(url):
    user_id_and_site = get_user_from_url(url)
    if user_id_and_site is None:
        return url
    return "https://{}/users/{}".format(user_id_and_site[1], user_id_and_site[0])


# noinspection PyMissingTypeHints
def to_protocol_relative(url):
    if url.startswith("http://"):
        return url[5:]
    elif url.startswith("https://"):
        return url[6:]
    else:
        return url
