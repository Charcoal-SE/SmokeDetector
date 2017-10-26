# noinspection PyUnresolvedReferences
import chatcommunicate  # coverage
import chatcommands
from globalvars import GlobalVars
import regex
from unittest.mock import *


# TODO: Test notifications, blacklisted and whitelisted users


def test_coffee():
    owner = Mock(name="El'endia Starman")
    owner.name.replace = "El'endia Starman".replace

    msg = Mock(owner=owner)

    assert chatcommands.coffee(None, original_msg=msg) == "*brews coffee for @El'endiaStarman*"
    assert chatcommands.coffee("angussidney") == "*brews coffee for @angussidney*"


def test_tea():
    owner = Mock(name="El'endia Starman")
    owner.name.replace = "El'endia Starman".replace

    msg = Mock(owner=owner)

    teas = "\*brews a cup of ({}) tea for ".format("|".join(chatcommands.TEAS))
    assert regex.match(teas + "@El'endiaStarman\*", chatcommands.tea(None, original_msg=msg))
    assert regex.match(teas + "@angussidney\*", chatcommands.tea("angussidney"))


def test_lick():
    assert chatcommands.lick() == "*licks ice cream cone*"


def test_brownie():
    assert chatcommands.brownie() == "Brown!"


def test_wut():
    assert chatcommands.wut() == "Whaddya mean, 'wut'? Humans..."


def test_alive():
    assert chatcommands.alive() in ['Yup', 'You doubt me?', 'Of course', '... did I miss something?',
                                    'plz send teh coffee', 'Kinda sorta',
                                    'Watching this endless list of new questions *never* gets boring']


def test_location():
    assert chatcommands.location() == GlobalVars.location


def test_privileged():
    chatcommunicate.parse_room_config("test/test_rooms.yml")

    owner = Mock(name="El'endia Starman", id=1)
    room = Mock(_client=Mock(host="chat.stackexchange.com"), id=11540)
    msg = Mock(owner=owner, room=room)
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2713 You are a privileged user."

    msg.owner.id = 2
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2573 " + GlobalVars.not_privileged_warning

    msg.owner.is_moderator = True
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2713 You are a privileged user."
