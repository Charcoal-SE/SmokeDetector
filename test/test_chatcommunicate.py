# -*- coding: utf-8 -*-
from ChatExchange.chatexchange import events, client
from chatcommunicate import *
import pytest

reply_value = ""


def mock_reply(text, length_check=True):
    global reply_value
    reply_value = text


def mock_event(content, event_type, room_id, room_name, user_id, user_name, id=28258802, message_id=15249005, time_stamp=1398822427):
    event_data = {
        "content": content,
        "event_type": event_type,
        "id": id,
        "message_id": message_id,
        "room_id": room_id,
        "room_name": room_name,
        "time_stamp": time_stamp,
        "user_id": user_id,
        "user_name": user_name
    }

    event = events.make(event_data, client.Client())
    event.message.reply = mock_reply
    event.message.content_source = content
    return event


def test_blame():
    # Get a suitable message
    blame_event = mock_event("!!/blame", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(blame_event, client.Client())
    assert reply_value == u"It's [Doorknob 冰](//chat.stackexchange.com/users/59776)'s fault."


def test_coffee():
    # Get a suitable message
    event = mock_event("!!/coffee", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert u"for @Doorknob冰" in reply_value


def test_tea():
    # Get a suitable message
    event = mock_event("!!/coffee", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert u"for @Doorknob冰" in reply_value


@pytest.mark.skipif(os.path.isfile("blacklistedUsers.txt"),
                    reason="shouldn't overwrite file")
def test_blacklisted_users():
    event = mock_event("!!/isblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not blacklisted. (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/rmblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not blacklisted."

    event = mock_event("!!/addblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User blacklisted (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/isblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is blacklisted. (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/rmblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from blacklist (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/isblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not blacklisted. (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/isblu http://meta.stackexchange.com/", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."

    event = mock_event("!!/addblu http://meta.stackexchange.com/", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`."

    event = mock_event("!!/rmblu http://meta.stackexchange.com/", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."

    # cleanup
    os.remove("blacklistedUsers.txt")


@pytest.mark.skipif(os.path.isfile("whitelistedUsers.txt"),
                    reason="shouldn't overwrite file")
def test_whitelisted_users():
    event = mock_event("!!/iswlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not whitelisted. (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/rmwlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not whitelisted."

    event = mock_event("!!/addwlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User whitelisted (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/iswlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is whitelisted. (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/rmwlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from whitelist (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/iswlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not whitelisted. (`237685` on `meta.stackexchange.com`)."

    event = mock_event("!!/iswlu http://meta.stackexchange.com/", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`."

    event = mock_event("!!/addwlu http://meta.stackexchange.com/", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`."

    event = mock_event("!!/rmwlu http://meta.stackexchange.com/", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."

    # cleanup
    os.remove("whitelistedUsers.txt")


def test_privileged_users():
    event = mock_event("!!/amiprivileged", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Yes, you are a privileged user."

    event = mock_event("!!/amiprivileged", 1, 11540, "Charcoal HQ", -5, u"Some bot")
    watcher(event, client.Client())
    assert reply_value == "No, you are not a privileged user."


def test_test_command():
    event = mock_event("!!/test", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Nothing to test"

    event = mock_event("!!/test my perfectly valid string which shouldn't be caught", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "> Would not be caught for title, body, and username."

    event = mock_event("!!/test 18669786819 gmail customer service number 1866978-6819 gmail support number", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert "in title" in reply_value
    assert "in body" in reply_value
    assert "in username" in reply_value


@pytest.mark.skipif(os.path.isfile("notifications.txt"),
                    reason="shouldn't overwrite file")
def test_notification():
    global reply_value

    event = mock_event("!!/notify", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "2 arguments expected"

    event = mock_event("!!/willibenotified", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "2 arguments expected"

    event = mock_event("!!/unnotify", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "2 arguments expected"

    event = mock_event("!!/notify abcd meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Room ID is invalid."

    event = mock_event("!!/willibenotified abcd meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Room ID is invalid"

    event = mock_event("!!/unnotify abcd meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Room ID is invalid."

    event = mock_event("!!/notify 11540 meat.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "The given SE site does not exist."

    event = mock_event("!!/willibenotified 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "No, you won't be notified for that site in that room."

    event = mock_event("!!/notify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "You'll now get pings from me if I report a post of `meta.stackexchange.com`, in room `11540` on `chat.stackexchange.com`"

    event = mock_event("!!/willibenotified 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Yes, you will be notified for that site in that room."

    event = mock_event("!!/notify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "That notification configuration is already registered."

    event = mock_event("!!/unnotify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "I will no longer ping you if I report a post of `meta.stackexchange.com`, in room `11540` on `chat.stackexchange.com`"

    event = mock_event("!!/unnotify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "That configuration doesn't exist."

    reply_value = ""
    event = mock_event("!!/notify 11540 meta.stackexchange.com-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == ""

    reply_value = ""
    event = mock_event("!!/unnotify 11540 meta.stackexchange.com-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == ""

    event = mock_event("!!/willibenotified 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "No, you won't be notified for that site in that room."

    # cleanup
    os.remove("notifications.txt")


def test_messages_not_sent():
    global reply_value

    reply_value = ''
    event = mock_event("test message", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    # If this fails, you have utterly broken something. Do *not* even think of pulling because people will scream and it will be ugly. Bad things will happen, and the world will fall into anarchy. So please, please, please... don't break this test.
    assert reply_value == ""
