#!/bin/sh

git config user.name SmokeDetector
git config user.email "smokey@erwaysoftware.com"
git config remote.origin.fetch "+refs/heads/master:refs/remotes/origin/master"
git config --add remote.origin.fetch "+refs/heads/deploy:refs/remotes/origin/deploy"
git fetch origin --depth=3
git checkout --track origin/deploy
git checkout master
