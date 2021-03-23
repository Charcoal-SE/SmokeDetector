#!/usr/bin/env python3
# coding=utf-8

# This script replaces the original nocrash.sh functionality with a pure Python approach.

import platform
import os
import subprocess as sp
from time import sleep, gmtime
import logging
import sys

on_windows = 'windows' in platform.platform().lower()

if on_windows:
    # noinspection PyPep8Naming
    from _Git_Windows import git
else:
    from sh.contrib import git

if tuple(int(x) for x in platform.python_version_tuple()) < (3, 5, 0):
    raise RuntimeError("Requires Python version 3.5 or newer.")

# Set the Python Executable based on this being stored - we refer to this later
# on for subprocess calls.
PY_EXECUTABLE = sys.executable

# Log to errorLog.txt so that the file shows reboots
logging_format_string = '%(asctime)s:%(levelname)s:%(message)s'
logging.basicConfig(
    filename='errorLog.txt',
    level=logging.INFO,
    format=logging_format_string)
logging.Formatter.converter = gmtime
# Also log to the console, so SD runners can look at consolidated output in the console.
console_logger = logging.StreamHandler()
console_logger.setLevel(logging.DEBUG)
console_logger.setFormatter(logging.Formatter(logging_format_string))
logging.getLogger().addHandler(console_logger)

# options = {"standby", "--loglevel", "no_se_activity_scan", "no_deletion_watcher", "no-git-user-check"}
options = {"standby", "--loglevel", "no_se_activity_scan", "no_deletion_watcher"}
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

    try:
        with open("exit.txt", "r", encoding="utf-8") as f:
            exit_info = [s.strip() for s in f]
        exit_info = [s for s in exit_info if s]  # Filter empty strings
        os.remove("exit.txt")
    except FileNotFoundError:
        # Assume something wrong has happened
        exit_info = []

    log('Exit information: [{}] {}'.format(ecode, ", ".join(exit_info) or "None"))

    if 'no_standby' in exit_info and 'standby' in persistent_arguments:
        persistent_arguments.remove('standby')
    elif 'standby' in exit_info and 'standby' not in persistent_arguments:
        persistent_arguments.append('standby')

    if 'pull_update' in exit_info:
        log("Re-checkout, but don't pull in new updates, as this is the MS instance.")
        git.checkout('deploy')
        # git.pull()
        git.checkout('master')
        # git.merge('@{u}')
        git.checkout('deploy')

        count = 0
        crashcount = 0

    elif 'early_exception' in exit_info:
        count += 1
        log('Incremented crash count: {}; sleeping before restart'.format(count))
        sleep(5)

        if crashcount == 2:
            log('Crash count should trigger reverted state, but not for the MS instance.')
            # git.checkout('HEAD~1')

            count = 0
            crashcount = 0

        else:
            crashcount += 1

    elif 'reboot' in exit_info or 'restart' in exit_info:
        log('Rebooting')
        count = 0

    elif ecode == -1 or 'shutdown' in exit_info:
        log('Stopping')
        stoprunning = True

    elif 'checkout_deploy' in exit_info:
        log('Checkout deploy')
        # print "[NoCrash] Checkout Deploy"
        git.checkout('deploy')

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
