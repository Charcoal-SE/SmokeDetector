import os
import pytest
import helpers


@pytest.mark.skipif("CHINA" in os.environ, reason="")
@pytest.mark.parametrize('shortened, original', [
    ('https://git.io/vyDZv', 'https://charcoal-se.org/smokey/'),
    ('https://bit.ly/2jhMbxn', 'https://charcoal-se.org/'),
    ('https://tinyurl.com/y7ba4pth', 'https://charcoal-se.org/'),
    ('https://tiny.cc/gsbbpy', 'https://charcoal-se.org/')
])
def test_unshorten_link(shortened, original):
    assert helpers.unshorten_link(shortened) == original
