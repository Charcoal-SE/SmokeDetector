import chatcommunicate
import chatcommands
from globalvars import GlobalVars
from datahandling import _remove_pickle

import collections
import io
import os
import os.path
import pytest
import threading
import time

from fake import Fake
from unittest.mock import Mock, patch


def test_parse_room_config():
    chatcommunicate.parse_room_config("test/test_rooms.yml")

    assert ("stackexchange.com", 11540) in chatcommunicate._command_rooms
    assert ("stackexchange.com", 30332) in chatcommunicate._command_rooms
    assert ("stackoverflow.com", 111347) in chatcommunicate._command_rooms

    assert ("stackexchange.com", 3) not in chatcommunicate._command_rooms
    assert ("stackexchange.com", 54445) not in chatcommunicate._command_rooms
    assert ("meta.stackexchange.com", 89) not in chatcommunicate._command_rooms

    assert ("stackexchange.com", 11540) in chatcommunicate._watcher_rooms
    assert ("stackexchange.com", 3) in chatcommunicate._watcher_rooms
    assert ("meta.stackexchange.com", 89) in chatcommunicate._watcher_rooms

    assert ("stackexchange.com", 30332) not in chatcommunicate._watcher_rooms
    assert ("stackexchange.com", 54445) not in chatcommunicate._watcher_rooms
    assert ("stackoverflow.com", 111347) not in chatcommunicate._watcher_rooms

    assert chatcommunicate._privileges[("stackexchange.com", 11540)] == {1, 16070}
    assert chatcommunicate._privileges[("stackexchange.com", 30332)] == set()
    assert chatcommunicate._privileges[("stackexchange.com", 3)] == set()
    assert chatcommunicate._privileges[("stackexchange.com", 54445)] == set()
    assert chatcommunicate._privileges[("meta.stackexchange.com", 89)] == {42}
    assert chatcommunicate._privileges[("stackoverflow.com", 111347)] == {1337, 256, 4766556}

    assert len(chatcommunicate._room_roles) == 5
    assert chatcommunicate._room_roles["debug"] == {("stackexchange.com", 11540)}
    assert chatcommunicate._room_roles["all"] == {("stackexchange.com", 11540),
                                                  ("stackexchange.com", 54445),
                                                  ("stackoverflow.com", 111347)}
    assert chatcommunicate._room_roles["metatavern"] == {("meta.stackexchange.com", 89)}
    assert chatcommunicate._room_roles["delay"] == {("meta.stackexchange.com", 89)}
    assert chatcommunicate._room_roles["no-all-caps title"] == {("meta.stackexchange.com", 89)}


@patch("chatcommunicate.threading.Thread")
@patch("chatcommunicate.Client")
@patch("chatcommunicate.parse_room_config")
def test_init(room_config, client_constructor, thread):
    client = Mock()
    client_constructor.return_value = client

    client.login.side_effect = Exception()
    threw_exception = False

    try:
        chatcommunicate.init("shoutouts", "to simpleflips")
    except Exception as e:
        assert str(e) == "Failed to log into " + next(iter(chatcommunicate._clients)) + ", max retries exceeded"
        threw_exception = True

    assert threw_exception

    client.login.side_effect = None
    client.login.reset_mock()
    client_constructor.reset_mock()

    room_config.side_effect = lambda _: room_config.get_original()("test/test_rooms.yml")
    GlobalVars.standby_mode = True
    chatcommunicate.init("shoutouts", "to simpleflips")

    assert len(chatcommunicate._rooms) == 0
    assert client.login.call_count == 3

    assert client_constructor.call_count == 3
    client_constructor.assert_any_call("stackexchange.com")
    client_constructor.assert_any_call("stackoverflow.com")
    client_constructor.assert_any_call("meta.stackexchange.com")

    assert thread.call_count == 2
    thread.assert_any_call(name="pickle ---rick--- runner", target=chatcommunicate.pickle_last_messages, daemon=True)
    thread.assert_any_call(name="message sender", target=chatcommunicate.send_messages, daemon=True)

    client.login.reset_mock()
    client_constructor.reset_mock()
    thread.reset_mock()

    GlobalVars.standby_mode = False

    counter = 0

    def throw_every_other(*_):
        nonlocal counter

        counter += 1
        if counter & 1:
            raise Exception()

    client.login.side_effect = throw_every_other
    chatcommunicate.init("shoutouts", "to simpleflips")

    assert client.login.call_count == 6
    assert counter == 6

    assert client_constructor.call_count == 3
    client_constructor.assert_any_call("stackexchange.com")
    client_constructor.assert_any_call("stackoverflow.com")
    client_constructor.assert_any_call("meta.stackexchange.com")

    assert thread.call_count == 2
    thread.assert_any_call(name="pickle ---rick--- runner", target=chatcommunicate.pickle_last_messages, daemon=True)
    thread.assert_any_call(name="message sender", target=chatcommunicate.send_messages, daemon=True)

    assert len(chatcommunicate._rooms) == 3
    assert chatcommunicate._rooms[("stackexchange.com", 11540)].deletion_watcher is True
    assert chatcommunicate._rooms[("stackexchange.com", 30332)].deletion_watcher is False
    assert chatcommunicate._rooms[("stackoverflow.com", 111347)].deletion_watcher is False


@pytest.mark.skipif(os.path.isfile("messageData.p"), reason="shouldn't overwrite file")
@patch("chatcommunicate.pickle.dump")
def test_pickle_rick(dump):
    try:
        threading.Thread(target=chatcommunicate.pickle_last_messages, daemon=True).start()

        chatcommunicate._pickle_run.set()

        # Yield to the pickling thread until it acquires the lock again
        while len(chatcommunicate._pickle_run._cond._waiters) == 0:
            time.sleep(0)

        assert dump.call_count == 1

        call, _ = dump.call_args_list[0]
        assert isinstance(call[0], chatcommunicate.LastMessages)
        assert isinstance(call[1], io.IOBase) and call[1].name == "messageData.p"
    finally:
        _remove_pickle("messageData.p")


@patch("chatcommunicate._pickle_run")
def test_message_sender(pickle_rick):
    chatcommunicate._last_messages = chatcommunicate.LastMessages({}, collections.OrderedDict())

    threading.Thread(target=chatcommunicate.send_messages, daemon=True).start()

    room = chatcommunicate.RoomData(Mock(), -1, False)

    room.room.id = 11540
    room.room._client.host = "stackexchange.com"

    room.room._client._do_action_despite_throttling.return_value = Fake({"json": lambda: {"id": 1}})
    chatcommunicate._msg_queue.put((room, "test", None))

    while not chatcommunicate._msg_queue.empty():
        time.sleep(0)

    room.room._client._do_action_despite_throttling.assert_called_once_with(("send", 11540, "test"))
    room.room.reset_mock()
    assert chatcommunicate._last_messages.messages[("stackexchange.com", 11540)] == collections.deque((1,))

    room.room.id = 30332
    room.room._client._do_action_despite_throttling.return_value = Fake({"json": lambda: {"id": 2}})
    chatcommunicate._msg_queue.put((room, "test", "did you hear about what happened to pluto"))

    while not chatcommunicate._msg_queue.empty():
        time.sleep(0)

    room.room._client._do_action_despite_throttling.assert_called_once_with(("send", 30332, "test"))
    assert chatcommunicate._last_messages.messages[("stackexchange.com", 11540)] == collections.deque((1,))
    assert chatcommunicate._last_messages.reports == collections.OrderedDict({("stackexchange.com", 2): "did you hear about what happened to pluto"})


@patch("chatcommunicate._msg_queue.put")
@patch("chatcommunicate.get_last_messages")
def test_on_msg(get_last_messages, post_msg):
    client = Fake({
        "_br": {
            "user_id": 1337
        },

        "host": "stackexchange.com"
    })

    room_data = chatcommunicate.RoomData(Mock(), -1, False)
    chatcommunicate._rooms[("stackexchange.com", 11540)] = room_data

    chatcommunicate.on_msg(Fake({}, spec=chatcommunicate.events.MessageStarred), None)  # don't reply to events we don't care about

    msg1 = Fake({
        "message": {
            "room": {
                "id": 11540,
            },

            "owner": {
                "id": 1,
            },

            "parent": None,
            "content": "shoutouts to simpleflips"
        }
    }, spec=chatcommunicate.events.MessagePosted)

    chatcommunicate.on_msg(msg1, client)

    msg2 = Fake({
        "message": {
            "room": {
                "id": 11540
            },

            "owner": {
                "id": 1337
            },

            "id": 999,
            "parent": None,
            "content": "!!/not_actually_a_command"
        }
    }, spec=chatcommunicate.events.MessagePosted)

    chatcommunicate.on_msg(msg2, client)

    msg3 = Fake({
        "message": {
            "room": {
                "id": 11540,
            },

            "owner": {
                "id": 1
            },

            "id": 999,
            "parent": None,
            "content": "!!/a_command"
        }
    }, spec=chatcommunicate.events.MessagePosted)

    mock_command = Mock(side_effect=lambda *_, **kwargs: "hi" if not kwargs["quiet_action"] else "")
    chatcommunicate._prefix_commands["a_command"] = (mock_command, (0, 0))

    chatcommunicate.on_msg(msg3, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":999 hi"
    mock_command.assert_called_once_with(original_msg=msg3.message, alias_used="a_command", quiet_action=False)

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg3.message.content = "!!/a_command-"
    chatcommunicate.on_msg(msg3, client)

    post_msg.assert_not_called()
    mock_command.assert_called_once_with(original_msg=msg3.message, alias_used="a_command", quiet_action=True)

    post_msg.reset_mock()
    mock_command.reset_mock()

    chatcommunicate._prefix_commands["a_command"] = (mock_command, (0, 1))
    chatcommunicate.on_msg(msg3, client)

    post_msg.assert_not_called()
    mock_command.assert_called_once_with(None, original_msg=msg3.message, alias_used="a_command", quiet_action=True)

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg3.message.content = "!!/a_command 1 2 3"
    chatcommunicate.on_msg(msg3, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":999 hi"
    mock_command.assert_called_once_with("1 2 3", original_msg=msg3.message, alias_used="a_command", quiet_action=False)

    post_msg.reset_mock()
    mock_command.reset_mock()

    chatcommunicate._prefix_commands["a_command"] = (mock_command, (1, 2))

    msg3.message.content = "!!/a_command"
    chatcommunicate.on_msg(msg3, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":999 Too few arguments."
    mock_command.assert_not_called()

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg3.message.content = "!!/a_command 1 2 oatmeal"
    chatcommunicate.on_msg(msg3, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":999 Too many arguments."
    mock_command.assert_not_called()

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg3.message.content = "!!/a_command- 1 2"
    chatcommunicate.on_msg(msg3, client)

    post_msg.assert_not_called()
    mock_command.assert_called_once_with("1", "2", original_msg=msg3.message, alias_used="a_command", quiet_action=True)

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg3.message.content = "!!/a_command 3"
    chatcommunicate.on_msg(msg3, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":999 hi"
    mock_command.assert_called_once_with("3", None, original_msg=msg3.message, alias_used="a_command", quiet_action=False)

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg4 = Fake({
        "message": {
            "room": {
                "id": 11540,
            },

            "owner": {
                "id": 1
            },

            "parent": {
                "owner": {
                    "id": 2
                }
            },

            "id": 1000,
            "content": "asdf"
        }
    }, spec=chatcommunicate.events.MessageEdited)

    chatcommunicate.on_msg(msg4, client)

    msg5 = Fake({
        "message": {
            "room": {
                "id": 11540,
            },

            "owner": {
                "id": 1
            },

            "parent": {
                "owner": {
                    "id": 1337
                }
            },

            "id": 1000,
            "content": "@SmokeDetector why   "
        }
    }, spec=chatcommunicate.events.MessageEdited)

    chatcommunicate._reply_commands["why"] = (mock_command, (0, 0))

    threw_exception = False

    try:
        chatcommunicate.on_msg(msg5, client)
    except AssertionError:
        threw_exception = True

    assert threw_exception
    mock_command.assert_not_called()
    post_msg.assert_not_called()

    chatcommunicate._reply_commands["why"] = (mock_command, (1, 1))
    chatcommunicate.on_msg(msg5, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":1000 hi"
    mock_command.assert_called_once_with(msg5.message.parent, original_msg=msg5.message, alias_used="why", quiet_action=False)

    post_msg.reset_mock()
    mock_command.reset_mock()

    msg5.message.content = "@SmokeDetector why@!@#-"
    chatcommunicate.on_msg(msg5, client)

    post_msg.assert_not_called()
    mock_command.assert_called_once_with(msg5.message.parent, original_msg=msg5.message, alias_used="why", quiet_action=True)

    msg6 = Fake({
        "message": {
            "room": {
                "id": 11540,
            },

            "owner": {
                "id": 1
            },

            "id": 1000,
            "parent": None,
            "content": "sd why - 2why 2why- 2- why- "
        }
    }, spec=chatcommunicate.events.MessageEdited)

    get_last_messages.side_effect = lambda _, num: (Fake({"id": i}) for i in range(num))
    chatcommunicate.on_msg(msg6, client)

    assert post_msg.call_count == 1
    assert post_msg.call_args_list[0][0][0][1] == ":1000 [:0] hi\n[:1] <skipped>\n[:2] hi\n[:3] hi\n[:4] <processed without return value>\n[:5] <processed without return value>\n[:6] <skipped>\n[:7] <skipped>\n[:8] <processed without return value>"


def test_message_type():
    fake1 = Fake({}, spec=chatcommunicate.Message)
    assert chatcommands.message(fake1) == fake1

    fake2 = Fake({})
    threw_exception = False

    try:
        chatcommands.message(fake2)
    except AssertionError:
        threw_exception = True

    assert threw_exception
