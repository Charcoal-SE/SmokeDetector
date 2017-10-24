import chatcommunicate # coverage
import chatcommands
import regex
from unittest.mock import *


def test_coffee():
    owner = Mock(name="El'endia Starman")
    owner.name.replace = Mock(return_value="El'endiaStarman")

    msg = Mock(owner=owner)

    assert chatcommands.coffee(None, original_msg=msg) == "*brews coffee for @El'endiaStarman*"
    assert chatcommands.coffee("angussidney") == "*brews coffee for @angussidney*"


def test_tea():
    owner = Mock(name="El'endia Starman")
    owner.name.replace = Mock(return_value="El'endiaStarman")

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
