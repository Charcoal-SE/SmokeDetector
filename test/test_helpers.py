import pytest
import helpers


@pytest.mark.parametrize('shortened, original', [
    ('https://goo.gl/kAb9rz', 'https://charcoal-se.org/'),
    ('https://bit.ly/2jhMbxn', 'https://charcoal-se.org/'),
    ('https://tinyurl.com/y7ba4pth', 'https://charcoal-se.org/'),
    ('https://tiny.cc/gsbbpy', 'https://charcoal-se.org/'),
    ('http://ea84eef0.ngrok.io/api/v2.0/posts/search.atom?key=abcdef012345&site=stackoverflow.com',
     'http://ea84eef0.ngrok.io/api/v2.0/posts/search.atom?key=abcdef012345&site=stackoverflow.com')
])
def test_unshorten_link(shortened, original):
    assert helpers.unshorten_link(shortened) == original
