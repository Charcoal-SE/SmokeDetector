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


def fetch_post_url_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\((http:\/\/[\w.]+\/questions\/\d+\/.+)\) by \[.+\]\((?:.+)\) on `[\w.]+`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        url = m.group(1)
        return url
    except:
        return None


def fetch_post_id_and_site_from_msg_content(content):
    url = fetch_post_url_from_msg_content(content)
    if url is None:
        return None
    post_type_regex = r"\/\d+#\d+$"
    post_type = ""
    search_regex = ""
    if re.compile(post_type_regex).search(url):
        post_type = "answer"
        search_regex = r"^https?:\/\/([\w.]+)/questions/\d+/.+/(\d+)#\d+$"
    else:
        post_type = "question"
        search_regex = r"^https?:\/\/([\w.]+)/questions/(\d+)/.+$"
    found = re.compile(search_regex).search(url)
    if found is None:
        return None
    try:
        post_id = found.group(2)
        post_site = found.group(1)
        return (post_id, post_site, post_type)
    except:
        return None


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
