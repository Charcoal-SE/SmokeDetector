# -*- coding: utf-8 -*-

from datahandling import append_pings


# noinspection PyMissingTypeHints
def test_append_pings():
    assert append_pings("foo", ["user1", "some user"]) == "foo (@user1 @someuser)"
    assert append_pings("foo", [u"Doorknob 冰"]) == u"foo (@Doorknob冰)"
