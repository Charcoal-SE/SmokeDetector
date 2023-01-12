# coding=utf-8
import os
import pytest
import helpers


@pytest.mark.skipif("CHINA" in os.environ, reason="")
@pytest.mark.parametrize('shortened, original', [
    # Failing as of 2023-01-12
    # ('https://git.io/vyDZv', 'https://charcoal-se.org/smokey/'),
    ('https://t.ly/AqjA', 'https://charcoal-se.org/smokey/'),
    ('https://bit.ly/2jhMbxn', 'https://charcoal-se.org/'),
    # Failing as of 2021-11-18
    # ('https://tinyurl.com/y7ba4pth', 'https://charcoal-se.org/')
    # https://tiny.cc/gsbbpy is not resolving on some hosts.
    # Notably, it does not resolve on CircleCI, but does on Travis CI.
    # It also resolves from Makyen's Windows machine, but not from Makyen's EC2-Linux.
    # ('https://tiny.cc/gsbbpy', 'https://charcoal-se.org/')
])
def test_unshorten_link(shortened, original):
    assert helpers.unshorten_link(shortened) == original
