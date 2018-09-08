# coding=utf-8
from datetime import datetime
import os
import traceback
import threading
import sys
# noinspection PyPackageRequirements
from websocket import WebSocketConnectionClosedException
import requests
from helpers import log, log_exception
from globalvars import GlobalVars


# noinspection PyProtectedMember
def uncaught_exception(exctype, value, tb):
    delta = datetime.utcnow() - GlobalVars.startup_utc_date
    log_exception(exctype, value, tb)
    if delta.total_seconds() < 180 and exctype not in \
            {KeyboardInterrupt, SystemExit, requests.ConnectionError, WebSocketConnectionClosedException}:
        os._exit(4)
    else:
        os._exit(1)


def install_thread_excepthook():
    """
    Workaround for sys.excepthook thread bug
    From
    http://spyced.blogspot.com/2007/06/workaround-for-sysexcepthook-bug.html
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psyco.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    init_old = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run

        # noinspection PyBroadException,PyShadowingNames
        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except Exception:  # Broad exception makes sense here
                sys.excepthook(*sys.exc_info())
            except BaseException:  # KeyboardInterrupt and SystemExit
                raise
        self.run = run_with_except_hook
    threading.Thread.__init__ = init
