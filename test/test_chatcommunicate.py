# -*- coding: utf-8 -*-
from ChatExchange.chatexchange import events, client
from chatcommunicate import *
from datahandling import is_false_positive, is_ignored_post
import pytest

GlobalVars.metasmoke_host = None

reply_value = ""
messages = {}

# methods to mock parts of SmokeDetector


def mock_reply(text, length_check=True):
    global reply_value
    reply_value = text


def mock_get_message(msg_id):
    if msg_id in messages:
        return mock_event(messages[msg_id], 1, 11540, "Charcoal HQ", 120914, u"SmokeDetector").message
    return None


def mock_event(content, event_type, room_id, room_name, user_id, user_name, id=28258802, message_id=15249005, time_stamp=1398822427):
    global reply_value

    reply_value = ""
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


def mock_previous_messages(messages_with_ids):
    global messages
    messages = messages_with_ids


def mock_client_get_message(client):
    client.get_message = mock_get_message
    return client


# Helper methods


def is_user_currently_whitelisted(link, site, id):
    event = mock_event("!!/iswlu {}".format(link), 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    if reply_value == "User is whitelisted (`{}` on `{}`).".format(site, id):
        return True
    if reply_value == "User is not whitelisted (`{}` on `{}`).".format(site, id):
        return False
    return -1


def is_user_currently_blacklisted(link, site, id):
    event = mock_event("!!/isblu {}".format(link), 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    if reply_value == "User is blacklisted (`{}` on `{}`).".format(site, id):
        return True
    if reply_value == "User is not blacklisted (`{}` on `{}`).".format(site, id):
        return False
    return -1


# Now starts the tests


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
    assert is_user_currently_blacklisted("http://meta.stackexchange.com/users/237685/hichris123", "237685", "meta.stackexchange.com") is False

    event = mock_event("!!/rmblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not blacklisted."

    event = mock_event("!!/addblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User blacklisted (`237685` on `meta.stackexchange.com`)."
    assert is_user_currently_blacklisted("http://meta.stackexchange.com/users/237685/hichris123", "237685", "meta.stackexchange.com")

    event = mock_event("!!/rmblu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from blacklist (`237685` on `meta.stackexchange.com`)."
    assert is_user_currently_blacklisted("http://meta.stackexchange.com/users/237685/hichris123", "237685", "meta.stackexchange.com") is False

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
    assert is_user_currently_whitelisted("http://meta.stackexchange.com/users/237685/hichris123", "237685", "meta.stackexchange.com") is False

    event = mock_event("!!/rmwlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User is not whitelisted."

    event = mock_event("!!/addwlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User whitelisted (`237685` on `meta.stackexchange.com`)."
    assert is_user_currently_whitelisted("http://meta.stackexchange.com/users/237685/hichris123", "237685", "meta.stackexchange.com")

    event = mock_event("!!/rmwlu http://meta.stackexchange.com/users/237685/hichris123", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from whitelist (`237685` on `meta.stackexchange.com`)."
    assert is_user_currently_whitelisted("http://meta.stackexchange.com/users/237685/hichris123", "237685", "meta.stackexchange.com") is False

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
    assert reply_value == "You'll now get pings from me if I report a post on `meta.stackexchange.com`, in room `11540` on `chat.stackexchange.com`"

    event = mock_event("!!/willibenotified 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "Yes, you will be notified for that site in that room."

    event = mock_event("!!/notify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "That notification configuration is already registered."

    event = mock_event("!!/unnotify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "I will no longer ping you if I report a post on `meta.stackexchange.com`, in room `11540` on `chat.stackexchange.com`"

    event = mock_event("!!/unnotify 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "That configuration doesn't exist."

    event = mock_event("!!/notify 11540 meta.stackexchange.com-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == ""

    event = mock_event("!!/unnotify 11540 meta.stackexchange.com-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == ""

    event = mock_event("!!/willibenotified 11540 meta.stackexchange.com", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "No, you won't be notified for that site in that room."

    # cleanup
    os.remove("notifications.txt")


def test_messages_not_sent():
    event = mock_event("test message", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    # If this fails, you have utterly broken something. Do *not* even think of pulling because people will scream and it will be ugly. Bad things will happen, and the world will fall into anarchy. So please, please, please... don't break this test.
    assert reply_value == ""


@pytest.mark.skipif(os.path.isfile("blacklistedUsers.txt"),
                    reason="shouldn't overwrite file")
def test_true_positive():
    mocked_client = mock_client_get_message(client.Client())

    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    event = mock_event(":1234 tp", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Recorded question as true positive in metasmoke. Use `tpu` or `trueu` if you want to blacklist a user."

    event = mock_event(":1234 tp-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""

    event = mock_event(":1234 tpu", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Blacklisted user and registered question as true positive."
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")

    event = mock_event(":1234 tpu-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")

    event = mock_event("!!/rmblu http://stackoverflow.com/users/1", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from blacklist (`1` on `stackoverflow.com`)."
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    event = mock_event(":1234 tpu-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: 'Not a report yay for bots'})
    watcher(event, mocked_client)
    assert reply_value == "That message is not a report."

    event = mock_event(":1234 tp", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Recorded answer as true positive in metasmoke. If you want to blacklist the poster of the answer, use `trueu` or `tpu`."

    event = mock_event(":1234 tp-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""

    event = mock_event(":1234 tpu", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Blacklisted user."
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")

    event = mock_event(":1234 tpu-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")

    event = mock_event("!!/rmblu http://stackoverflow.com/users/1", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from blacklist (`1` on `stackoverflow.com`)."
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    # cleanup
    os.remove("blacklistedUsers.txt")


@pytest.mark.skipif(os.path.isfile("whitelistedUsers.txt") or os.path.isfile("falsePositives.txt"),
                    reason="shouldn't overwrite file")
def test_false_positive():
    mocked_client = mock_client_get_message(client.Client())

    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    event = mock_event(":1234 fp", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Registered question as false positive."
    assert is_false_positive(("1000", "stackoverflow.com"))

    GlobalVars.false_positives = []
    assert not is_false_positive(("1000", "stackoverflow.com"))
    event = mock_event(":1234 fp-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_false_positive(("1000", "stackoverflow.com"))

    GlobalVars.false_positives = []
    assert not is_false_positive(("1000", "stackoverflow.com"))
    event = mock_event(":1234 fpu", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Registered question as false positive and whitelisted user."
    assert is_false_positive(("1000", "stackoverflow.com"))
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")
    event = mock_event("!!/rmwlu http://stackoverflow.com/users/1", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from whitelist (`1` on `stackoverflow.com`)."
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    GlobalVars.false_positives = []
    assert not is_false_positive(("1000", "stackoverflow.com"))
    event = mock_event(":1234 fpu-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_false_positive(("1000", "stackoverflow.com"))
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")
    event = mock_event("!!/rmwlu http://stackoverflow.com/users/1", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from whitelist (`1` on `stackoverflow.com`)."
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    event = mock_event(":1234 fp", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Registered answer as false positive."
    assert is_false_positive(("1000", "stackoverflow.com"))

    GlobalVars.false_positives = []
    assert not is_false_positive(("1000", "stackoverflow.com"))
    event = mock_event(":1234 fp-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_false_positive(("1000", "stackoverflow.com"))

    GlobalVars.false_positives = []
    assert not is_false_positive(("1000", "stackoverflow.com"))
    event = mock_event(":1234 fpu", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Registered answer as false positive and whitelisted user."
    assert is_false_positive(("1000", "stackoverflow.com"))
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")
    event = mock_event("!!/rmwlu http://stackoverflow.com/users/1", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from whitelist (`1` on `stackoverflow.com`)."
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    GlobalVars.false_positives = []
    assert not is_false_positive(("1000", "stackoverflow.com"))
    event = mock_event(":1234 fpu-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Bad keyword in answer: [TEST](//stackoverflow.com/a/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_false_positive(("1000", "stackoverflow.com"))
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com")
    event = mock_event("!!/rmwlu http://stackoverflow.com/users/1", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(event, client.Client())
    assert reply_value == "User removed from whitelist (`1` on `stackoverflow.com`)."
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    event = mock_event(":1234 fpu-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: 'Not a report yay for bots'})
    watcher(event, mocked_client)
    assert reply_value == "That message is not a report."

    # cleanup
    os.remove("whitelistedUsers.txt")
    os.remove("falsePositives.txt")


@pytest.mark.skipif(os.path.isfile("ignoredPosts.txt"),
                    reason="shouldn't overwrite file")
def test_ignore():
    mocked_client = mock_client_get_message(client.Client())

    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False

    assert not is_ignored_post(("1000", "stackoverflow.com"))
    event = mock_event(":1234 ignore", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == "Post ignored; alerts about it will no longer be posted."
    assert is_ignored_post(("1000", "stackoverflow.com"))
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False
    GlobalVars.ignored_posts = []

    assert not is_ignored_post(("1000", "stackoverflow.com"))
    event = mock_event(":1234 ignore-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: '[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] All-caps title: [TEST](//stackoverflow.com/questions/1000) by [Community](//stackoverflow.com/users/1) on `stackoverflow.com`'})
    watcher(event, mocked_client)
    assert reply_value == ""
    assert is_ignored_post(("1000", "stackoverflow.com"))
    assert is_user_currently_whitelisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False
    assert is_user_currently_blacklisted("http://stackoverflow.com/users/1", "1", "stackoverflow.com") is False
    GlobalVars.ignored_posts = []

    event = mock_event(":1234 ignore-", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    mock_previous_messages({1234: 'Not a report yay for bots'})
    watcher(event, mocked_client)
    assert reply_value == "That message is not a report."

    # cleanup
    os.remove("ignoredPosts.txt")
