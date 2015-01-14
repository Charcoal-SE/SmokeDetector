import re
from globalvars import GlobalVars


def get_user_from_url(url):
    m = re.compile(r"https?://([\w.]+)/users/(\d+)/.+/?").search(url)
    if m is None:
        return None
    try:
        site = m.group(1)
        user_id = m.group(2)
        return (user_id, site)
    except:
        return None


def fetch_post_id_and_site_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\(http:\/\/[\w.]+\/questions\/(\d+)\/.+\) by \[.+\]\((?:.+)\) on `([\w.]+)`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        post_id = m.group(1)
        site_name = m.group(2)
        return (post_id, site_name)
    except:
        return None # message is not a report


def fetch_owner_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\(http:\/\/[\w.]+\/questions\/\d+\/.+\) by \[.+\]\((.+)\) on `[\w.]+`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        owner_url = m.group(1)
        return owner_url
    except:
        return None


def fetch_title_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[(.+)]\(http:\/\/[\w.]+\/questions\/\d+\/.+\) by \[.+\]\(.+\) on `[\w.]+`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        title = m.group(1)
        return title
    except:
        return None


def fetch_unescaped_title_from_encoded(title_encoded):
    return GlobalVars.parser.unescape(re.sub(r"([_*\\`\[\]])", r"\\\1", title_encoded)).strip()
