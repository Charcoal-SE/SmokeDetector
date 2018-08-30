#!/usr/bin/env python3

from glob import glob
from helpers import only_blacklists_changed, blacklist_integrity_check


def test_blacklist_integrity():
    errors = blacklist_integrity_check()

    if len(errors) == 1:
        raise ValueError(errors[0])
    elif len(errors) > 1:
        raise ValueError("\n\t".join(["Multiple errors has occurred."] + errors))


def test_blacklist_pull_diff():
    only_blacklists_diff = """watched_keywords.txt
                              bad_keywords.txt
                              blacklisted_websites.txt"""
    assert only_blacklists_changed(only_blacklists_diff)
    mixed_files_diff = """helpers.py
                          test/test_blacklists.py
                          blacklisted_usernames.txt"""
    assert not only_blacklists_changed(mixed_files_diff)
