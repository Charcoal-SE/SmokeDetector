import chatcommunicate
import chatcommands
from globalvars import GlobalVars

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

    thread.assert_called_once_with(name="pickle ---rick--- runner", target=chatcommunicate.pickle_last_messages)

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

    thread.assert_called_once_with(name="pickle ---rick--- runner", target=chatcommunicate.pickle_last_messages)

    client.login.side_effect = None
    client.login.reset_mock()
    client_constructor.reset_mock()
    thread.reset_mock()
