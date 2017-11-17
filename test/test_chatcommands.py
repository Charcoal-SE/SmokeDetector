# noinspection PyUnresolvedReferences
import chatcommunicate  # coverage
import chatcommands
from globalvars import GlobalVars
import regex
from unittest.mock import *
import pytest
import os


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

    owner = Mock(name="El'endia Starman", id=1, is_moderator=False)
    room = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg = Mock(owner=owner, room=room)
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2713 You are a privileged user."

    msg.owner.id = 2
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2573 " + GlobalVars.not_privileged_warning

    msg.owner.is_moderator = True
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2713 You are a privileged user."


def test_report():
    owner = Mock(name="El'endia Starman", id=1)
    room = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg = Mock(owner=owner, room=room)

    assert chatcommands.report("test", original_msg=msg) == "Post 1: That does not look like a valid post URL."

    assert chatcommands.report("one two three four five plus-an-extra", original_msg=msg) == (
        "To avoid SmokeDetector reporting posts too slowly, you can report at most 5 posts at a time. This is to avoid "
        "SmokeDetector's chat messages getting rate-limited too much, which would slow down reports."
    )

    assert chatcommands.report('http://stackoverflow.com/q/1', original_msg=msg) == \
        "Post 1: Could not find data for this post in the API. It may already have been deleted."

    # Valid post
#    assert chatcommands.report('http://stackoverflow.com/a/1732454', original_msg=msg) is None

    # Don't re-report
#    assert chatcommands.report('http://stackoverflow.com/a/1732454', original_msg=msg) == "Post 1: Already recently " \
#                                                                                          "reported"

    # Can use report command multiple times in 30s if only one URL was used
#    assert chatcommands.report('http://stackoverflow.com/q/1732348', original_msg=msg) is None


def test_allspam():
    owner = Mock(name="El'endia Starman", id=1)
    room = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg = Mock(owner=owner, room=room)

    assert chatcommands.allspam("test", original_msg=msg) == "That doesn't look like a valid user URL."

    # If this code lasts long enough to fail, I'll be happy
    assert chatcommands.allspam("http://stackexchange.com/users/10000000000", original_msg=msg) == \
        "The specified user does not appear to exist."

    assert chatcommands.allspam("http://stackexchange.com/users/5869449", original_msg=msg) == (
        "The specified user has an abnormally high number of accounts. Please consider flagging for moderator "
        "attention, otherwise use !!/report on the user's posts individually."
    )

    assert chatcommands.allspam("http://stackexchange.com/users/11683", original_msg=msg) == (
        "The specified user's reputation is abnormally high. Please consider flagging for moderator attention, "
        "otherwise use !!/report on the posts individually."
    )

    assert chatcommands.allspam("http://stackoverflow.com/users/22656", original_msg=msg) == (
        "The specified user's reputation is abnormally high. Please consider flagging for moderator attention, "
        "otherwise use !!/report on the posts individually."
    )

    assert chatcommands.allspam("http://stackexchange.com/users/12108751", original_msg=msg) == \
        "The specified user hasn't posted anything."

    assert chatcommands.allspam("http://stackoverflow.com/users/8846458", original_msg=msg) == \
        "The specified user has no posts on this site."

    # This test is for users with <100rep but >15 posts
    # If this breaks in the future because the below user eventually gets 100 rep (highly unlikely), use the following
    # data.SE query to find a new target. Alternatively, get a sock to post 16 answers in the sandbox.
    # https://stackoverflow.com/users/7052649/vibin (look for low rep but >1rep users, 1rep users are usually suspended)
    assert chatcommands.allspam("http://stackoverflow.com/users/7052649", original_msg=msg) == (
        "The specified user has an abnormally high number of spam posts. Please consider flagging for moderator "
        "attention, otherwise use !!/report on the posts individually."
    )

    # Valid user for allspam command
#    assert chatcommands.allspam("http://stackexchange.com/users/12108974", original_msg=msg) is None
#    assert chatcommands.allspam("http://meta.stackexchange.com/users/373807", original_msg=msg) is None

    GlobalVars.blacklisted_users = []


@pytest.mark.skipif(os.path.isfile("blacklistedUsers.p"), reason="shouldn't overwrite file")
def test_blacklisted_users():
    owner = Mock(name="El'endia Starman", id=1)
    room = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg = Mock(owner=owner, room=room)

    # Format: !!/*blu profileurl
    assert chatcommands.isblu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is not blacklisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.addblu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User blacklisted (`4622463` on `stackoverflow.com`)."
    # TODO: Edit command to check and not blacklist again, add test
    assert chatcommands.isblu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is blacklisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmblu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User removed from blacklist (`4622463` on `stackoverflow.com`)."
    assert chatcommands.isblu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is not blacklisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmblu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is not blacklisted."

    # Format: !!/*blu userid sitename
    assert chatcommands.isblu("4622463 stackoverflow", original_msg=msg) == \
        "User is not blacklisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.addblu("4622463 stackoverflow", original_msg=msg) == \
        "User blacklisted (`4622463` on `stackoverflow.com`)."
    # TODO: Add test here as well
    assert chatcommands.isblu("4622463 stackoverflow", original_msg=msg) == \
        "User is blacklisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmblu("4622463 stackoverflow", original_msg=msg) == \
        "User removed from blacklist (`4622463` on `stackoverflow.com`)."
    assert chatcommands.isblu("4622463 stackoverflow", original_msg=msg) == \
        "User is not blacklisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmblu("4622463 stackoverflow", original_msg=msg) == \
        "User is not blacklisted."

    # Invalid input
    assert chatcommands.addblu("http://meta.stackexchange.com/users", original_msg=msg) == \
        "Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`."
    assert chatcommands.rmblu("http://meta.stackexchange.com/", original_msg=msg) == \
        "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."
    assert chatcommands.isblu("msklkldsklaskd", original_msg=msg) == \
        "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."

    # Cleanup
    os.remove("blacklistedUsers.p")


@pytest.mark.skipif(os.path.isfile("whitelistedUsers.p"), reason="shouldn't overwrite file")
def test_whitelisted_users():
    owner = Mock(name="El'endia Starman", id=1)
    room = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg = Mock(owner=owner, room=room)

    # Format: !!/*wlu profileurl
    assert chatcommands.iswlu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is not whitelisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.addwlu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User whitelisted (`4622463` on `stackoverflow.com`)."
    # TODO: Add test here as well
    assert chatcommands.iswlu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is whitelisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmwlu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User removed from whitelist (`4622463` on `stackoverflow.com`)."
    assert chatcommands.iswlu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is not whitelisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmwlu("http://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
        "User is not whitelisted."

    # Format: !!/*wlu userid sitename
    assert chatcommands.iswlu("4622463 stackoverflow", original_msg=msg) == \
        "User is not whitelisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.addwlu("4622463 stackoverflow", original_msg=msg) == \
        "User whitelisted (`4622463` on `stackoverflow.com`)."
    # TODO: Add test here as well
    assert chatcommands.iswlu("4622463 stackoverflow", original_msg=msg) == \
        "User is whitelisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmwlu("4622463 stackoverflow", original_msg=msg) == \
        "User removed from whitelist (`4622463` on `stackoverflow.com`)."
    assert chatcommands.iswlu("4622463 stackoverflow", original_msg=msg) == \
        "User is not whitelisted (`4622463` on `stackoverflow.com`)."
    assert chatcommands.rmwlu("4622463 stackoverflow", original_msg=msg) == \
        "User is not whitelisted."

    # Invalid input
    assert chatcommands.addwlu("http://meta.stackexchange.com/users", original_msg=msg) == \
        "Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`."
    assert chatcommands.rmwlu("http://meta.stackexchange.com/", original_msg=msg) == \
        "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."
    assert chatcommands.iswlu("msklkldsklaskd", original_msg=msg) == \
        "Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`."

    # Cleanup
    os.remove("whitelistedUsers.p")


@pytest.mark.skipif(os.path.isfile("notifications.p"), reason="shouldn't overwrite file")
def test_notifications():
    owner1 = Mock(name="El'endia Starman", id=1)
    room1 = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg1 = Mock(owner=owner1, room=room1)

    owner2 = Mock(name="angussidney", id=145827)
    room2 = Mock(_client=Mock(host="stackexchange.com"), id=11540)
    msg2 = Mock(owner=owner2, room=room2)

    # User 1
    assert chatcommands.allnotificationsites("11540", original_msg=msg1) == \
        "You won't get notified for any sites in that room."
    assert chatcommands.willbenotified("11540 gaming", original_msg=msg1) == \
        "No, you won't be notified for that site in that room."
    assert chatcommands.notify("11540 gaming", original_msg=msg1) == \
        "You'll now get pings from me if I report a post on `gaming`, in room `11540` on `chat.stackexchange.com`"
    assert chatcommands.notify("11540 codegolf.stackexchange.com", original_msg=msg1) == \
        "You'll now get pings from me if I report a post on `codegolf.stackexchange.com`, in room `11540` on " \
        "`chat.stackexchange.com`"
    assert chatcommands.willbenotified("11540 gaming.stackexchange.com", original_msg=msg1) == \
        "Yes, you will be notified for that site in that room."
    assert chatcommands.willbenotified("11540 codegolf", original_msg=msg1) == \
        "Yes, you will be notified for that site in that room."

    # User 2
    assert chatcommands.allnotificationsites("11540", original_msg=msg2) == \
        "You won't get notified for any sites in that room."
    assert chatcommands.willbenotified("11540 raspberrypi", original_msg=msg2) == \
        "No, you won't be notified for that site in that room."
    assert chatcommands.notify("11540 raspberrypi", original_msg=msg2) == \
        "You'll now get pings from me if I report a post on `raspberrypi`, in room `11540` on `chat.stackexchange.com`"
    assert chatcommands.notify("11540 raspberrypi", original_msg=msg2) == \
        "That notification configuration is already registered."
    assert chatcommands.willbenotified("11540 raspberrypi.stackexchange.com", original_msg=msg2) == \
        "Yes, you will be notified for that site in that room."

    # Check for no interaction
    assert chatcommands.allnotificationsites("11540", original_msg=msg1) == \
        "You will get notified for these sites:\r\ngaming.stackexchange.com, codegolf.stackexchange.com"
    assert chatcommands.allnotificationsites("11540", original_msg=msg2) == \
        "You will get notified for these sites:\r\nraspberrypi.stackexchange.com"

    # Remove all notifications and check
    assert chatcommands.unnotify("11540 gaming.stackexchange.com", original_msg=msg1) == \
        "I will no longer ping you if I report a post on `gaming.stackexchange.com`, in room `11540` on " \
        "`chat.stackexchange.com`"
    assert chatcommands.unnotify("11540 codegolf", original_msg=msg1) == \
        "I will no longer ping you if I report a post on `codegolf`, in room `11540` on `chat.stackexchange.com`"
    assert chatcommands.unnotify("11540 raspberrypi", original_msg=msg2) == \
        "I will no longer ping you if I report a post on `raspberrypi`, in room `11540` on `chat.stackexchange.com`"
    assert chatcommands.unnotify("11540 raspberrypi", original_msg=msg2) == \
        "That configuration doesn't exist."
    assert chatcommands.allnotificationsites("11540", original_msg=msg1) == \
        "You won't get notified for any sites in that room."
    assert chatcommands.willbenotified("11540 raspberrypi", original_msg=msg2) == \
        "No, you won't be notified for that site in that room."

    assert chatcommands.allnotificationsites("asdf", original_msg=msg1) == "Invalid input type given for an argument"
    assert chatcommands.notify("11540", "charcoalspam.stackexchange.com") == "The given SE site does not exist."

    # Cleanup
    os.remove("notifications.p")
