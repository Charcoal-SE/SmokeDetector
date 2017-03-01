#!/usr/bin/python

# This script replaces the original nocrash.sh functionality with a pure Python approach.

import platform
if 'windows' in str(platform.platform()).lower():
    print "Git support not available in Windows."
else:
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

persistent_arguments = list({"standby", "charcoal-hq-only"} & set(sys.argv))

count = 0
crashcount = 0
stoprunning = False
ecode = None  # Define this to prevent errors

# Make a clean copy of existing environment variables, to pass down to subprocess.
environ = os.environ.copy()

while stoprunning is False:
    # print "[NoCrash] Switch to Standby? %s" % switch_to_standby

    if count == 0:
        if 'standby' in persistent_arguments:
            switch_to_standby = False  # Necessary for the while loop
            command = 'python ws.py standby'.split()
        else:
            command = 'python ws.py first_start'.split()
    else:
        if not ('standby' in persistent_arguments):
            command = 'python ws.py'.split()
        else:
            command = 'python ws.py standby'.split()

    # noinspection PyBroadException
    try:
        persistent_arguments.remove('standby')
    except:
        pass  # We're OK if the argument isn't in the list.

    try:
        ecode = sp.call(command + persistent_arguments, env=environ)
    except KeyboardInterrupt:
        # print "[NoCrash] KeyBoard Interrupt received.."
        ecode = 6

    if ecode == 3:
        # print "[NoCrash] Pull in new updates."
        if 'windows' not in str(platform.platform()).lower():
            git.checkout('deploy')
            git.pull()
            git.submodule('update')

        count = 0
        crashcount = 0

    elif ecode == 4:
        # print "[NoCrash] Crashed."
        count += 1
        sleep(5)

        if crashcount == 2:
            # print "[NoCrash] Going to reverted state."
            if 'windows' not in str(platform.platform()).lower():
                git.checkout('HEAD~1')

            count = 0
            crashcount = 0

        else:
            crashcount += 1

    elif ecode == 5:
        # print "[NoCrash] Rebooting."
        count = 0

    elif ecode == 6:
        # print "[NoCrash] Stopping"
        stoprunning = True

    elif ecode == 7:
        # print "[NoCrash] Go to Standby Restart Called"
        persistent_arguments.append("standby")

    elif ecode == 8:
        # print "[NoCrash] Checkout Deploy"
        if 'windows' not in str(platform.platform()).lower():
            git.checkout('deploy')

        count = 0
        crashcount = 0

    elif ecode == 10:
        # print "[NoCrash] Socket failure, let network settle before restart."
        sleep(5)
        count = 0

    else:
        # print "[NoCrash] Died by unknown reason, check logs; restarting in 5 seconds."
        sleep(5)
        count += 1
