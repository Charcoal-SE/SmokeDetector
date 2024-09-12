#!/bin/sh

# Abusing the shell no-op (colon) for outputting
set -x

: Lint tests
python3 -m flake8 --config=tox_tests.ini ./test/

: Lint classes
python3 -m flake8 --config=tox_classes.ini ./classes/

: Lint code
python3 -m flake8 ./*.py

: Pytest
python3 -W default::Warning -m pytest test
