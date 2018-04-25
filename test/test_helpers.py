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


@pytest.mark.parametrize('link, param', [
    ('stackoverflow.com', 'stackoverflow'),
    ('//stackoverflow.com', 'stackoverflow'),
    ('https://stackoverflow.com', 'stackoverflow'),
    ('https://stackoverflow.com/', 'stackoverflow'),
    ('//stackoverflow.com/questions/12345678', 'stackoverflow'),
    ('//stackoverflow.com/a/12345678', 'stackoverflow'),
    ('mathoverflow.net', 'mathoverflow'),
    ('superuser.com', 'superuser'),
    ('serverfault.com', 'serverfault'),
    ('askubuntu.com', 'askubuntu'),
    ('3dprinting.stackexchange.com', '3dprinting'),
    ('blender.stackexchange.com', 'blender'),
    ('//blender.stackexchange.com', 'blender'),
    ('https://blender.stackexchange.com', 'blender'),
    ('https://blender.stackexchange.com/', 'blender'),
    ('//blender.stackexchange.com/questions/123456', 'blender'),
    ('//blender.stackexchange.com/a/123456', 'blender')
])
def test_api_parameter_from_link(link, param):
    assert helpers.api_parameter_from_link(link) == param
