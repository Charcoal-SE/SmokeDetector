import os
from datahandling import *


# Allows use of `environ_or_none("foo") or "default"` shorthand
def environ_or_none(key):
    try:
        return os.environ[key]
    except:
        return None


def check_permissions(function):
    def run_command(ev_room, ev_user_id, wrap2, *args, **kwargs):
        if is_privileged(ev_room, ev_user_id, wrap2):
            # DOING THIS HAS AN ISSUE:
            # The passed parameters - room_id and user_id are not passed to function().
            # To get those, we need to either readd them to kwargs or change all
            # function signatures to accept these as named parameters
            kwargs['ev_room'] = ev_room
            kwargs['ev_user_id'] = ev_user_id
            kwargs['wrap2'] = wrap2
            return function(*args, **kwargs)
        else:
            return False

    return run_command
