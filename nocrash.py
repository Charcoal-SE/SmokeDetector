#!/usr/bin/env python3

# This script replaces the original nocrash.sh functionality with a pure Python approach.

import platform
import os
import subprocess as sp
from time import sleep
import logging
import sys
from getpass import getpass
if 'windows' in str(platform.platform()).lower():
    # noinspection PyPep8Naming
    from classes import Git as git
else:
    from sh.contrib import git

# Set the Python Executable based on this being stored - we refer to this later on for subprocess calls.
PY_EXECUTABLE = sys.executable

# Log to errorlog.txt so that !!/errorlogs shows us restarts
logging.basicConfig(
    filename='errorlog.txt',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s')

options = {"standby", "charcoal-hq-only", "no-chat", "no-git-user-check"}
persistent_arguments = sys.argv

count = 0
crashcount = 0
stoprunning = False
ecode = None  # Define this to prevent errors


def log(message):
    logging.info('[NoCrash] {}'.format(message))


def warn(message):
    logging.warn('[NoCrash] {}'.format(message))


def error(message):
    logging.error('[NoCrash] {}'.format(message))


# if 'no-git-user-check' in persistent_arguments:
#     persistent_arguments.remove('no-git-user-check')
# else:
#     git_name = git.config('--get', 'user.name', _ok_code=[0, 1])
#     if git_name != "SmokeDetector":
#         logging.error('git config user.name "{0}" is wrong; '
#                       'use no-git-user-check to ignore'.format(git_name))
#         exit(122)
#     git_mail = git.config('--get', 'user.email', _ok_code=[0, 1])
#     if git_mail != "smokey@erwaysoftware.com":
#         logging.error('git config user.email "{0}" is wrong'.format(git_mail))
#         exit(121)


while not stoprunning:
    log('Starting with persistent_arguments {!r}'.format(persistent_arguments))

    if count == 0:
        if 'standby' in persistent_arguments:
            command = [PY_EXECUTABLE, 'ws.py', 'standby']
        else:
            command = [PY_EXECUTABLE, 'ws.py', 'first_start']
    else:
        if 'standby' not in persistent_arguments:
            command = [PY_EXECUTABLE, 'ws.py']
        else:
            command = [PY_EXECUTABLE, 'ws.py', 'standby']

    if 'standby' in persistent_arguments:
        persistent_arguments.remove('standby')

    try:
        ecode = sp.call(command + persistent_arguments, env=os.environ.copy())
    except sp.SubprocessError:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("subprocess.call() error {0}: {1}".format(exc_type.__name__, exc_obj))
    except (KeyboardInterrupt, SystemExit):
        ecode = 6

    log('Exited with ecode {}'.format(ecode))

    if ecode == 3:
        log('Pull in new updates')
        if 'windows' not in str(platform.platform()).lower():
            git.checkout('deploy')
            git.pull()
        else:
            warn('Not pulling updates; we are on Windows')

        count = 0
        crashcount = 0

    elif ecode == 4:
        count += 1
        log('Incremented crash count: {}; sleeping before restart'.format(count))
        sleep(5)

        if crashcount == 2:
            log('Crash count triggered reverted state')
            if 'windows' not in str(platform.platform()).lower():
                git.checkout('HEAD~1')
            else:
                warn('Not reverting; we are on Windows')

            count = 0
            crashcount = 0

        else:
            crashcount += 1

    elif ecode == 5:
        log('Rebooting')
        count = 0

    elif ecode == 6:
        log('Stopping')
        stoprunning = True

    elif ecode == 7:
        log('Adding "standby" to persistent arguments')
        persistent_arguments.append("standby")

    elif ecode == 8:
        log('Checkout deploy')
        # print "[NoCrash] Checkout Deploy"
        if 'windows' not in str(platform.platform()).lower():
            git.checkout('deploy')
        else:
            warn('Not checking out deploy branch; we are on Windows')

        count = 0
        crashcount = 0

    elif ecode == 10:
        warn('Socket failure, sleeping to hopefully let network recover')
        sleep(5)
        count = 0

    else:
        error('Died for unknown reason -- check logs.  Sleeping before restart')
        sleep(5)
        count += 1
