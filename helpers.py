import os
from collections import namedtuple
from helpers import Response
from apigetpost import api_get_post
from parsing import get_user_from_url
from spamhandling import handle_spam

Response = namedtuple('Response', 'command_status message')


# Allows use of `environ_or_none("foo") or "default"` shorthand
def environ_or_none(key):
    try:
        return os.environ[key]
    except:
        return None


def report_post(urls, message_url, where_from, reported_by, ev_user_id=None, wrap2=None):
    output = []
    index = 0
    for url in urls:
        index += 1
        post_data = api_get_post(url)
        if post_data is None:
            output.append("Post {}: That does not look like a valid post URL.".format(index))
            continue
        if post_data is False:
            output.append("Post {}: Could not find data for this post in the API. "
                          "It may already have been deleted.".format(index))
            continue
        if has_already_been_posted(post_data.site, post_data.post_id, post_data.title) and not is_false_positive((post_data.post_id, post_data.site)):
            # Don't re-report if the post wasn't marked as a false positive. If it was marked as a false positive,
            # this re-report might be attempting to correct that/fix a mistake/etc.
            output.append("Post {}: Already recently reported".format(index))
            continue
        user = get_user_from_url(post_data.owner_url)
        if user is not None:
            add_blacklisted_user(user, message_url, post_data.post_url)
        why = u"Post manually reported by user *{}* from *{}*.\n".format(reported_by,
                                                                         where_from.decode('utf8'))
        batch = ""
        if len(urls) > 1:
            batch = " (batch report: post {} out of {})".format(index, len(urls))
        handle_spam(title=post_data.title,
                    body=post_data.body,
                    poster=post_data.owner_name,
                    site=post_data.site,
                    post_url=post_data.post_url,
                    poster_url=post_data.owner_url,
                    post_id=post_data.post_id,
                    reasons=["Manually reported " + post_data.post_type + batch],
                    is_answer=post_data.post_type == "answer",
                    why=why,
                    owner_rep=post_data.owner_rep,
                    post_score=post_data.score,
                    up_vote_count=post_data.up_vote_count,
                    down_vote_count=post_data.down_vote_count,
                    question_id=post_data.question_id)
    if 1 < len(urls) > len(output) and where_from != 'metasmoke':
        add_or_update_multiple_reporter(ev_user_id, wrap2.host, time.time())
    if len(output) > 0:
        return Response(command_status=True, message=os.linesep.join(output))
    return Response(command_status=True, message=None)
