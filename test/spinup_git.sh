#!/bin/sh

# This script is called in .travis.yml with
#   before_script:
#     - sh test/spinup_git.sh
# It runs after the commands in install:, but before
# the testing specified in script:.

git rev-parse HEAD
gitCurrentCommit=`git rev-parse HEAD`
git config user.name SmokeDetector
git config user.email "smokey@erwaysoftware.com"
git config remote.origin.fetch "+refs/heads/master:refs/remotes/origin/master"
git config --add remote.origin.fetch "+refs/heads/deploy:refs/remotes/origin/deploy"
# A depth of 50 is the default on Travis
git fetch origin --depth=50
# Some of SD's git operations rely on the master and/or deploy branch being the one that SD
# is operating on.  So, we force both of those branches to have their HEAD at the commit
# which we are going to test.
git checkout master
git reset --hard $gitCurrentCommit
# SD normally runs on the deploy branch
git checkout --track origin/deploy
git reset --hard $gitCurrentCommit
git rev-parse HEAD
