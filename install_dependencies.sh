#!/bin/bash

# Install system-wide Python library dependencies
sudo -H python -m pip install -r requirements.txt --upgrade

# Some dependencies need to be installed in user space.
python -m pip install --user -r user_requirements.txt --upgrade