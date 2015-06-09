import regex
from globalvars import GlobalVars
from datahandling import check_site_and_get_full_name


def get_user_from_url(url):
    m = regex.compile(r"https?://([\w.]+)/users/(\d+)/.+/?").search(url)
    if m is None:
        return None
    try:
        site = m.group(1)
        user_id = m.group(2)
        return (user_id, site)
    except:
        return None


def fetch_post_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\((http:\/\/[\w.]+\/questions\/\d+\/.+|http:\/\/[\w.]+\/[qa]\/\d+)\) by \[?.*\]?\(?(?:.*)\)? on `[\w.]+`$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        url = m.group(1)
        return url
    except:
        return None


def fetch_post_id_and_site_from_url(url):
    if url is None:
        return None
    post_type_regex = r"\/\d+#\d+$"
    post_type = ""
    search_regex = ""
    if regex.compile(post_type_regex).search(url):
        post_type = "answer"
        search_regex = r"^https?:\/\/([\w.]+)/questions/\d+/.+/(\d+)#\d+$"
    else:
        post_type = "question"
        search_regex = r"^https?:\/\/([\w.]+)/questions/(\d+)(?:/.+)?$"
    found = regex.compile(search_regex).search(url)
    if found is not None:
        try:
            post_id = found.group(2)
            post_site = found.group(1)
            return (post_id, post_site, post_type)
        except:
            return None
    search_regex = r"^https?:\/\/([\w.]+)/(q|a)/(\d+)(?:/\d+)?"
    found = regex.compile(search_regex).search(url)
    if found is None:
        return None
    try:
        post_id = found.group(3)
        post_site = found.group(1)
        post_type = "question" if found.group(2) == "q" else "answer"
        return (post_id, post_site, post_type)
    except:
        return None


def fetch_post_id_and_site_from_msg_content(content):
    url = fetch_post_url_from_msg_content(content)
    return fetch_post_id_and_site_from_url(url)


def fetch_owner_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\((?:http:\/\/[\w.]+\/questions\/\d+\/.+|http:\/\/[\w.]+\/[qa]\/\d+)\) by \[.+\]\((.+)\) on `[\w.]+`$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        owner_url = m.group(1)
        return owner_url
    except:
        return None


def fetch_title_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[(.+)]\((?:http:\/\/[\w.]+\/questions\/\d+\/.+|http:\/\/[\w.]+\/[qa]\/\d+)\) by \[?.*\]?\(?.*\)? on `[\w.]+`$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        title = m.group(1)
        return title
    except:
        return None


def unescape_title(title_escaped):
    return GlobalVars.parser.unescape(title_escaped).strip()


def escape_special_chars_in_title(title_unescaped):
    return regex.sub(r"([_*\\`\[\]])", r"\\\1", title_unescaped)


def get_user_from_list_command(cmd):  # for example, !!/addblu is a list command
    cmd_parts = cmd.split(" ")
    uid = -1
    site = ""
    if len(cmd_parts) == 2:
        uid_site = get_user_from_url(cmd_parts[1])
        if uid_site is not None:
            uid = uid_site[0]
            site = uid_site[1]
    elif len(cmd_parts) == 3:
        uid = cmd_parts[1]
        site = cmd_parts[2]
        digit_re = regex.compile("^[0-9]+$")
        site_re = regex.compile(r"^(\w+\.stackexchange\.com|\w+\.(com|net))$")
        if not digit_re.match(uid):
            uid = -1
            site = ""
        elif not site_re.match(site):
            exists, name = check_site_and_get_full_name(site)
            if exists:
                return uid, name
            else:
                return -2, name
    return uid, site


def url_to_shortlink(url):
    id_and_site = fetch_post_id_and_site_from_url(url)
    if id_and_site is None:
        return url
    if id_and_site[2] == "question":
        return "http://%s/q/%s" % (id_and_site[1], id_and_site[0])
    else:
        return "http://%s/a/%s" % (id_and_site[1], id_and_site[0])
