#!/bin/bash

git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector

sudo -H python3 -m pip install -r requirements.txt --upgrade
python3 -m pip install -r user_requirements.txt --upgrade
