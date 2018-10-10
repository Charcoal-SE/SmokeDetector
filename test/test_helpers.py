import pytest
import helpers


@pytest.mark.parametrize('shortened, original', [
    ('https://goo.gl/kAb9rz', 'https://charcoal-se.org/'),
    ('https://bit.ly/2jhMbxn', 'https://charcoal-se.org/'),
    ('https://tinyurl.com/y7ba4pth', 'https://charcoal-se.org/'),
    ('https://tiny.cc/gsbbpy', 'https://charcoal-se.org/')
])
def test_unshorten_link(shortened, original):
    assert helpers.unshorten_link(shortened) == original
