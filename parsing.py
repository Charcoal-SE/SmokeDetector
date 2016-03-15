import regex
from globalvars import GlobalVars
from datahandling import check_site_and_get_full_name


def get_user_from_url(url):
    m = regex.compile(r"(?:https?:)?//([\w.]+)/u(?:sers)?/(\d+)(/(?:.+/?)?)?").search(url)
    if m is None:
        return None
    try:
        site = m.group(1)
        user_id = m.group(2)
        return user_id, site
    except:
        return None


def fetch_post_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\) \] [\w\s,:\(\)-]+: \[.+]\(((?:http:)?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\) by \[?.*\]?\(?(?:.*)\)? on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
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
        search_regex = r"^(?:https?:)?\/\/([\w.]+)/questions/\d+/.+/(\d+)#\d+$"
    else:
        post_type = "question"
        search_regex = r"^(?:https?:)?\/\/([\w.]+)/questions/(\d+)(?:/.*)?$"
    found = regex.compile(search_regex).search(url)
    if found is not None:
        try:
            post_id = found.group(2)
            post_site = found.group(1)
            return (post_id, post_site, post_type)
        except:
            return None
    search_regex = r"^(?:https?:)?\/\/([\w.]+)/(q|a)/(\d+)(?:/\d+)?/?"
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
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\) \] [\w\s,:\(\)-]+: \[.+]\((?:(?:http:)?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\) by \[.+\]\((.+)\) on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        owner_url = m.group(1)
        return owner_url
    except:
        return None


def fetch_title_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\) \] [\w\s,:\(\)-]+: \[(.+)]\((?:(?:http:)?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\) by \[?.*\]?\(?.*\)? on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        title = m.group(1)
        return title
    except:
        return None


def fetch_user_from_allspam_report(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\) \] All of this user's posts are spam: \[user \d+ on [\w\.]+\]\((//[\w\.]+/users/\d+\D*)\)(?: \[.+\]\(.+\))?$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        user_link = m.group(1)
        return get_user_from_url(user_link)
    except:
        return None


def edited_message_after_postgone_command(content):
    search_regex = r"^\[ \[SmokeDetector\]\([^)]*\) \] [\w\s,:\(\)-]+: (\[.+]\((?:(?:http:)?\/\/[\w.]+\/questions\/\d+(?:\/.*)?|(?:http:)?\/\/[\w.]+\/[qa]\/\d+/?)\)) by \[?.*\]?\(?.*\)? on `[\w.]+`(?: \(@.+\))?(?: \[.+\]\(.+\))?$"
    m = regex.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        link = m.group(1)
        return content.replace(link, "*(gone)*")
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
        return "http://{}/questions/{}".format(id_and_site[1], id_and_site[0])
        # We're using "/questions" and not "/q" here because when the URL
        # is made protocol-relative, /q would redirect to http even if the
        # shortlink is https. Same for /a. But there we still use /a because
        # there is no /answers or something like that.
    else:
        return "http://{}/a/{}".format(id_and_site[1], id_and_site[0])


def user_url_to_shortlink(url):
    user_id_and_site = get_user_from_url(url)
    if user_id_and_site is None:
        return url
    return "http://{}/u/{}".format(user_id_and_site[1], user_id_and_site[0])


def to_protocol_relative(url):
    if url.startswith("http://"):
        return url[5:]
    elif url.startswith("https://"):
        return url[6:]
    else:
        return url


def preprocess_shortcut_command(cmd):
    cmd = regex.sub(r"(\d)\s+", r"\1", cmd)
    parts = cmd.split(" ")
    new_cmd = ["sd"]
    for i in xrange(1, len(parts)):
        curr = parts[i]
        if curr == "":
            continue
        if not curr[0].isdigit():
            new_cmd.append(curr)
        else:
            match = regex.search(r"^\d+", curr)
            t = int(match.group())
            if t > 100:
                # If someone made an unreasonable request, limit the # of commands (so we don't
                # have any overflows) but do one more than the max messages we keep so it errors out
                t = 101
            for j in xrange(0, t):
                new_cmd.append(curr[match.end():])
    return " ".join(new_cmd)
