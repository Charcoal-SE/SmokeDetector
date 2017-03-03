from globalvars import GlobalVars
from time import sleep

# noinspection PyClassHasNoInit
class ChatLogon:
    @staticmethod
    def SE(username, password):
        # chat.stackexchange.com logon/wrapper
        chatlogoncount = 0
        for cl in range(1, 10):
            chatlogoncount += 1
            try:
                GlobalVars.wrap.login(username, password)
                GlobalVars.smokeDetector_user_id[GlobalVars.charcoal_room_id] = str(GlobalVars.wrap.get_me().id)
                break  # If we didn't error out horribly, we can be done with this loop
            except (ValueError, AssertionError):
                sleep(1)
                continue  # If we did error, we need to try this again.
        if chatlogoncount >= 10:  # Handle "too many logon attempts" case to prevent infinite looping
            raise RuntimeError("Could not get Chat.SE logon.")

    @staticmethod
    def MetaSE(username, password):
        # chat.meta.stackexchange.com logon/wrapper
        metalogoncount = 0
        for cml in range(1, 10):
            metalogoncount += 1
            try:
                GlobalVars.wrapm.login(username, password)
                GlobalVars.smokeDetector_user_id[GlobalVars.meta_tavern_room_id] = str(GlobalVars.wrapm.get_me().id)
                break  # If we didn't error out horribly, we can be done with this loop
            except (ValueError, AssertionError):
                sleep(1)
                continue  # If we did error, we need to try this again.
        if metalogoncount >= 10:  # Handle "too many logon attempts" case to prevent infinite looping
                raise RuntimeError("Could not get Chat.Meta.SE logon.")
    
    @staticmethod
    def SO(username, password):
        # chat.stackoverflow.com logon/wrapper
        sologoncount = 0
        for sol in range(1, 10):
            sologoncount += 1
            try:
                GlobalVars.wrapso.login(username, password)
                GlobalVars.smokeDetector_user_id[GlobalVars.socvr_room_id] = str(GlobalVars.wrapso.get_me().id)
                break  # If we didn't error out horribly, we can be done with this loop
            except (ValueError, AssertionError):
                sleep(1)
                continue  # If we did error, we need to try this again.
        if sologoncount >= 10:  # Handle "too many logon attempts" case to prevent infinite looping
            raise RuntimeError("Could not get Chat.SO logon.")
