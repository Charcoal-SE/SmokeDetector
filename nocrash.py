#!/usr/bin/python

from sh import git
import os
import subprocess as sp
from time import sleep
import sys

# Get environment variables
ChatExchangeU = os.environ.get('ChatExchangeU')
ChatExchangeP = os.environ.get('ChatExchangeP')

if ChatExchangeU is None:
    ChatExchangeU = str(input("Username: ")).strip('\r\n')

os.environ['CEU'] = "h"

if ChatExchangeP is None:
    ChatExchangeP = str(input("Password: ")).strip('\r\n')

count = 0
crashcount = 0
stoprunning = False
switch_to_standby = False
ecode = None  # Define this to prevent errors

while stoprunning is False:
    if count == 0:
        if (len(sys.argv) > 1) and ("standby" in sys.argv):
            command = 'python ws.py standby'.split()
        else:
            command = 'python ws.py first_start'.split()
    else:
        if not switch_to_standby:
            command = 'python ws.py'.split()
        else:
            switch_to_standby = False
            command = 'python ws.py standby'.split()

    try:
        ecode = sp.call(command)
    except KeyboardInterrupt:
        # We are OK accepting a KeyboardInterrupt here. We don't want ctrl+c on ws.py to
        # bounce back to nocrash.py.  Though, we ideally would, this way we have the same
        # process as we had previously with nocrash.sh where two ctrl+c is needed.
        pass
    except Exception as e:
        raise e

    if ecode == 3:
        git.checkout('deploy')
        git.pull()
        git.submodule('update')
        count = 0
        crashcount = 0

    elif ecode == 4:
        count += 1
        sleep(5)

        if crashcount == 2:
            git.checkout('HEAD~1')
            count = 0
            crashcount = 0

        else:
            crashcount += 1

    elif ecode == 5:
        count = 0

    elif ecode == 6:
        stoprunning = True

    elif ecode == 7:
        switch_to_standby = True

    elif ecode == 8:
        git.checkout('deploy')
        count = 0
        crashcount = 0

    elif ecode == 10:
        sleep(5)
        count = 0

    else:
        sleep(5)
        count += 1
