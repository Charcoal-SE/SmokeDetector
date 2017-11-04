import chatcommunicate
import chatcommands


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
