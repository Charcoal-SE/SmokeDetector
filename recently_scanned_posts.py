# coding=utf-8
import time
from tasks import Tasks
from globalvars import GlobalVars
from helpers import log


POST_STRAIGHT_COPY_KEYS = [
    'response_timestamp',
    'last_edit_date',
    'title',
    'body_markdown',
]
POSTS_EXPIRE_INTERVAL = 10 * 60  # 10 minutes


def get_key_for_post(post):
    if 'is_recently_scanned_post' in post:
        return post.get('post_key', None)
    site = post.get('site', None)
    post_id = post.get('question_id', None)
    if post_id is None:
        post_id = post.get('answer_id', None)
    if site is None or post_id is None:
        log('warn', 'Unable to determine site or post_id for recently scanned post:'
                    ' site:{}:: post_id: {}:: post:{}'.format(site, post_id, post))
        return None
    return "{}/{}".format(site, post_id)


def add_post(post, is_spam=None, reasons=None, why=None, have_lock=None):
    if 'is_recently_scanned_post' not in post:
        post = get_recently_scanned_post_from_post(post)
    new_key = post['post_key']
    if new_key is None:
        raise KeyError('post key is None')
    new_record = {'post': post, 'scan_timestamp': time.time(),
                  'is_spam': is_spam, 'reasons': reasons, 'why': why}
    if have_lock:
        GlobalVars.recently_scanned_posts[new_key] = new_record
    else:
        with GlobalVars.recently_scanned_posts_lock:
            GlobalVars.recently_scanned_posts[new_key] = new_record


def apply_timestamps_to_entry_from_post_and_time_if_newer(post, scanned_entry):
    scanned_post = scanned_entry['post']
    scanned_post_reponse_timestamp = scanned_post.get('response_timestamp', 0)
    post_reponse_timestamp = post.get('response_timestamp', 0)
    if post_reponse_timestamp > scanned_post_reponse_timestamp:
        scanned_entry['scan_timestamp'] = time.time()
        scanned_entry['post']['response_timestamp'] = post.get('response_timestamp', None)


def update_entry_timestamp_if_newer(post, have_lock=None):
    key = get_key_for_post(post)
    if key is None:
        raise KeyError('post key is None')
    try:
        if have_lock:
            rs_entry = GlobalVars.recently_scanned_posts[key]
            apply_timestamps_to_entry_from_post_and_time_if_newer(post, rs_entry)
        else:
            with GlobalVars.recently_scanned_posts_lock:
                rs_entry = GlobalVars.recently_scanned_posts[key]
                apply_timestamps_to_entry_from_post_and_time_if_newer(post, rs_entry)
    except KeyError:
        # If the record doesn't exist, we add it.
        add_post(post, have_lock)


def get_check_equality_data(post):
    return (
        post.get('last_edit_date', None),
        post.get('title', None),
        post.get('owner_name', None),
        post.get('body_markdown', None),
    )


def compare_posts(post, scanned_post):
    result = {}
    post_resonse_timestamp = post.get('response_timestamp', 0)
    scanned_post_resonse_timestamp = scanned_post.get('response_timestamp', 0)
    post_is_older = post_resonse_timestamp < scanned_post_resonse_timestamp
    result['is_older'] = post_is_older
    if post_is_older:
        result['is_older_or_unchanged'] = True
        return result
    scanned_equality_data = get_check_equality_data(scanned_post)
    post_equality_data = get_check_equality_data(post)
    scanned_equality_data = get_check_equality_data(scanned_post)
    is_unchanged = post_equality_data == scanned_equality_data
    result['is_unchanged'] = is_unchanged
    result['is_older_or_unchanged'] = is_unchanged or post_is_older
    result['is_grace_edit'] = False
    if not is_unchanged and post_equality_data[0] == scanned_equality_data[0]:
        # This should be a grace period edit
        what_changed = [post_equality_data[count] == scanned_equality_data[count]
                        for count in range(len(post_equality_data))]
        post_key = post.get('post_key', None)
        log('debug', 'GRACE period edit: {}::  matching(ED,T,U,MD):{}::  '.format(post_key, what_changed))
        result['is_grace_edit'] = True
    return result


def get_recently_scanned_post_from_post(post):
    if 'is_recently_scanned_post' in post:
        # It's already a RS post
        return post
    rs_post = {key: post.get(key, None) for key in POST_STRAIGHT_COPY_KEYS}
    rs_post['is_recently_scanned_post'] = True
    owner_dict = post.get('owner', {})
    owner_name = owner_dict.get('display_name', None)
    rs_post['owner_name'] = owner_name
    rs_post['post_key'] = get_key_for_post(post)
    return rs_post


def atomic_compare_update_and_get_spam_data(post):
    with GlobalVars.recently_scanned_posts_lock:
        if 'is_recently_scanned_post' not in post:
            post = get_recently_scanned_post_from_post(post)
        post_key = post.get('post_key', None)
        if post_key is None:
            # Without a post_key, we can't check or store.
            raise KeyError('post key is None')
        scanned_entry = GlobalVars.recently_scanned_posts.get(post_key, None)
        if scanned_entry is None:
            add_post(post, have_lock=True)
            return {'is_older_or_unchanged': False, 'no_scanned_entry': True}
        scanned_post = scanned_entry['post']
        compare_info = compare_posts(post, scanned_post)
        apply_timestamps_to_entry_from_post_and_time_if_newer(post, scanned_entry)
        for key in ['is_spam', 'reasons', 'why']:
            compare_info[key] = scanned_entry.get(key, None)
        return compare_info


def expire_posts():
    min_retained_timestamp = time.time() - GlobalVars.recently_scanned_posts_retention_time
    with GlobalVars.recently_scanned_posts_lock:
        # A dict comprehension can be used to do this:
        #   GlobalVars.recently_scanned_posts = {key: value for key, value in GlobalVars.recently_scanned_posts.items()
        #                                        if value['scan_timestamp'] > min_retained_timestamp}
        # But, that has a notably higher memory requirement than deleting the entries.
        # Where the right trade-off wrt. higher memory use vs. maybe more time for del/pop isn't clear and will depend
        # on the size of the dict and memory/CPU available for the particular SD instance.
        rs_posts = GlobalVars.recently_scanned_posts
        original_length = len(rs_posts)
        keys_to_delete = [key for key, value in rs_posts.items() if value['scan_timestamp'] < min_retained_timestamp]
        for key in keys_to_delete:
            rs_posts.pop(key, None)
        new_length = len(rs_posts)
        log('debug', 'Expire recently scanned posts: start: '
                     '{}::  now: {}:: expired: {}'.format(original_length, new_length, original_length - new_length))


Tasks.periodic(expire_posts, interval=POSTS_EXPIRE_INTERVAL)
