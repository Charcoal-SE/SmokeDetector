#!/bin/bash

git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector
git submodule init
git submodule update
sudo pip install -r requirements.txt --upgrade
