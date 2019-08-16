#!/bin/bash
echo  name: Lint tests
echo python3 -m flake8 --config=tox_tests.ini ./test/
python3 -m flake8 --config=tox_tests.ini ./test/
echo  name: Lint classes
echo python3 -m flake8 --config=tox_classes.ini ./classes/
python3 -m flake8 --config=tox_classes.ini ./classes/
echo  name: Lint code
echo python3 -m flake8 ./
python3 -m flake8 ./
echo  name: Pytest
echo python3 -W default::Warning -m pytest test
python3 -W default::Warning -m pytest test
