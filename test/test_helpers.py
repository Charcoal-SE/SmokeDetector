# coding=utf-8
import os
import pytest
import helpers


@pytest.mark.skipif("CHINA" in os.environ, reason="")
@pytest.mark.parametrize('shortened, original', [
    # FIXME: disabled for now
    # See bug report https://github.com/Charcoal-SE/SmokeDetector/issues/11151
    # ('https://t.ly/AqjA', 'https://charcoal-se.org/smokey/'),
    ('https://bit.ly/2jhMbxn', 'https://charcoal-se.org/'),
])
def test_unshorten_link(shortened, original):
    assert helpers.unshorten_link(shortened) == original
