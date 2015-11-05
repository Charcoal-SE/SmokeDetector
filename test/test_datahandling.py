from datahandling import append_pings


def test_append_pings():
    assert append_pings("foo", ["user1", "some user"]) == "foo (@user1 @someuser)"
