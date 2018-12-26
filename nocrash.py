#!/usr/bin/env python3

# This script replaces the original nocrash.sh functionality with a pure Python approach.

import platform
import os
import subprocess as sp
from time import sleep
import logging
import sys
from getpass import getpass
on_windows = 'windows' in platform.platform().lower()

if on_windows:
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
    logging.warning('[NoCrash] {}'.format(message))


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

    try:
        ecode = sp.call(command + persistent_arguments, env=os.environ.copy())
    except sp.SubprocessError:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("subprocess.call() error {0}: {1}".format(exc_type.__name__, exc_obj))
    except (KeyboardInterrupt, SystemExit):
        sys.exit()

    with open("exit.txt", "r") as f:
        exit_info = [s.strip() for s in f]
    exit_info = [s for s in exit_info if s]  # Filter empty strings
    os.remove("exit.txt")

    log('Exit information: [{}] {}'.format(ecode, ", ".join(exit_info)))

    if 'no_standby' in exit_info and 'standby' in persistent_arguments:
        persistent_arguments.remove('standby')
    elif 'standby' in exit_info and 'standby' not in persistent_arguments:
        persistent_arguments.append('standby')

    if 'pull_update' in exit_info:
        log('Pull in new updates')
        if not on_windows:
            git.checkout('deploy')
            git.pull()
        else:
            warn('Not pulling updates; we are on Windows')

        count = 0
        crashcount = 0

    elif 'early_exception' in exit_info:
        count += 1
        log('Incremented crash count: {}; sleeping before restart'.format(count))
        sleep(5)

        if crashcount == 2:
            log('Crash count triggered reverted state')
            if not on_windows:
                git.checkout('HEAD~1')
            else:
                warn('Not reverting; we are on Windows')

            count = 0
            crashcount = 0

        else:
            crashcount += 1

    elif 'reboot' in exit_info:
        log('Rebooting')
        count = 0

    elif ecode < 0 or 'shutdown' in exit_info:
        log('Stopping')
        stoprunning = True

    elif 'checkout_deploy' in exit_info:
        log('Checkout deploy')
        # print "[NoCrash] Checkout Deploy"
        if not on_windows:
            git.checkout('deploy')
        else:
            warn('Not checking out deploy branch; we are on Windows')

        count = 0
        crashcount = 0

    elif 'socket_failure' in exit_info:
        warn('Socket failure, sleeping to hopefully let network recover')
        sleep(5)
        count = 0

    elif 'standby' in exit_info or 'no_standby' in exit_info:
        pass  # skip the 'else' block below

    else:
        error('Died for unknown reason -- check logs.  Sleeping before restart')
        sleep(5)
        count += 1
