#!/usr/bin/env python3

from glob import glob
from helpers import only_files_changed, blacklist_integrity_check


def test_blacklist_integrity():
    errors = blacklist_integrity_check()

    if len(errors) == 1:
        raise ValueError(errors[0])
    elif len(errors) > 1:
        raise ValueError("\n\t".join(["{} errors has occurred:".format(len(errors))] + errors))


def test_remote_diff():
    file_set = set("abcdefg")
    true_diff = "a c d g"
    false_diff = "a d g q"
    assert only_files_changed(true_diff, file_set)
    assert not only_files_changed(false_diff, file_set)
