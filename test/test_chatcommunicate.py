# -*- coding: utf-8 -*-
from ChatExchange.chatexchange import events, client
from chatcommunicate import *

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
    blame_event = mock_event("!!/coffee", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(blame_event, client.Client())
    assert u"for @Doorknob冰" in reply_value


def test_tea():
    # Get a suitable message
    blame_event = mock_event("!!/coffee", 1, 11540, "Charcoal HQ", 59776, u"Doorknob 冰")
    watcher(blame_event, client.Client())
    assert u"for @Doorknob冰" in reply_value
