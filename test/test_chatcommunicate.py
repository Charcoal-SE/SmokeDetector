import chatcommunicate
import chatcommands
from globalvars import GlobalVars

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
        assert str(e) == "Failed to log into stackexchange.com"
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

    thread.assert_called_once_with(name="pickle ---rick--- runner", target=chatcommunicate.pickle_last_messages, daemon=True)

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

    thread.assert_called_once_with(name="pickle ---rick--- runner", target=chatcommunicate.pickle_last_messages, daemon=True)

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
        os.remove("messageData.p")


@patch("chatcommunicate._pickle_run")
def test_on_msg(pickle_rick):
    client = Fake({
        "_br": {
            "user_id": 1337
        },

        "host": "stackexchange.com"
    })

    room_data = chatcommunicate.RoomData(Mock(), Mock(), -1, (), False)
    chatcommunicate._rooms[("stackexchange.com", 11540)] = room_data

    assert chatcommunicate.on_msg(Fake({}, spec=chatcommunicate.events.MessageStarred), None) is None  # don't reply to events we don't care about

    msg1 = Fake({
        "message": {
            "owner": {
                "id": 1,
            },

            "parent": None,
            "content": "shoutouts to simpleflips"
        }
    }, spec=chatcommunicate.events.MessagePosted)

    assert chatcommunicate.on_msg(msg1, client) is None

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

    room_data.last_report_data = "did you hear about what happened to pluto"

    assert chatcommunicate.on_msg(msg2, client) is None

    assert chatcommunicate._last_messages.messages[("stackexchange.com", 11540)] == collections.deque((999,))
    assert chatcommunicate._last_messages.reports == collections.OrderedDict({("stackexchange.com", 999): "did you hear about what happened to pluto"})
    assert room_data.last_report_data == ()

    pickle_rick.set.assert_called_once()
    room_data.lock.set.assert_called_once()

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
            "reply": Mock(),
            "content": "!!/a_command"
        }
    }, spec=chatcommunicate.events.MessagePosted)

    mock_command = Mock(side_effect=lambda **kwargs: "hi" if not kwargs["quiet_action"] else "")
    chatcommunicate._commands["prefix"]["a_command"] = (mock_command, (0, 0))

    chatcommunicate.on_msg(msg3, client)

    msg3.message.reply.assert_called_once_with("hi", length_check=False)
    mock_command.assert_called_once_with(original_msg=msg3.message, alias_used="a_command", quiet_action=False)
    msg3.message.reply.reset_mock()
    mock_command.reset_mock()

    msg3.message.content = "!!/a_command-"
    chatcommunicate.on_msg(msg3, client)

    msg3.message.reply.assert_not_called()
    mock_command.assert_called_once_with(original_msg=msg3.message, alias_used="a_command", quiet_action=True)
