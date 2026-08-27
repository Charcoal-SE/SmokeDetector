#!/bin/sh

# Abusing the shell no-op (colon) for outputting
set -x

: Lint code
ruff check

: Pytest
python3 -W default::Warning -m pytest test
