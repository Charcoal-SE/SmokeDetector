#!/usr/bin/env python3

import pytest

from glob import glob
from helpers import files_changed, blacklist_integrity_check


def test_blacklist_integrity():
    errors = blacklist_integrity_check()

    if len(errors) == 1:
        pytest.fail(errors[0])
    elif len(errors) > 1:
        pytest.fail("\n\t".join(["{} errors has occurred:".format(len(errors))] + errors))


def test_remote_diff():
    file_set = set("abcdefg")
    true_diff = "a c k p"
    false_diff = "h j q t"
    assert files_changed(true_diff, file_set)
    assert not files_changed(false_diff, file_set)
