# coding=utf-8
from globalvars import GlobalVars


# noinspection PyMissingTypeHints
def test_globalvars():
    # Changing values in globalvars.py is fine for debugging, but when
    # pushing, there should be made sure that the values are correct.
    # assert GlobalVars.charcoal_room_id == "11540"
    # assert GlobalVars.meta_tavern_room_id == "89"
    # assert GlobalVars.socvr_room_id == "41570"
    # assert GlobalVars.smokeDetector_user_id["11540"] == "120914"
    # assert GlobalVars.smokeDetector_user_id["89"] == "266345"
    # assert GlobalVars.smokeDetector_user_id["41570"] == "3735529"
    # assert len(GlobalVars.privileged_users["11540"]) > 0
    # assert len(GlobalVars.privileged_users["89"]) > 0
    # assert len(GlobalVars.privileged_users["41570"]) > 0
    # assert GlobalVars.blockedTime["all"] == 0
    # assert GlobalVars.blockedTime[GlobalVars.charcoal_room_id] == 0
    # assert GlobalVars.blockedTime[GlobalVars.meta_tavern_room_id] == 0
    # assert GlobalVars.blockedTime[GlobalVars.socvr_room_id] == 0

    # The following lists must be empty in globalvars.py, because
    # they will be filled later.
    with GlobalVars.auto_ignored_posts_lock:
        assert len(GlobalVars.auto_ignored_posts) == 0
    with GlobalVars.ignored_posts_lock:
        assert len(GlobalVars.ignored_posts) == 0
    with GlobalVars.blacklisted_users_lock:
        assert len(GlobalVars.blacklisted_users) == 0
    with GlobalVars.whitelisted_users_lock:
        assert len(GlobalVars.whitelisted_users) == 0
