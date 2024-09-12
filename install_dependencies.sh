#!/bin/bash

# Install system-wide Python library dependencies
sudo -H python3 -m pip install -r requirements.txt --upgrade

# Some dependencies need to be installed in user space.
python3 -m pip install --user -r user_requirements.txt --upgrade
