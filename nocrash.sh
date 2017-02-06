#!/bin/bash

echo "WARNING: The 'nocrash.sh' script is deprecated in favor of 'nocrash.py' instead."
echo ""

# Execute nocrash.py instead with the same arguments passed through to it.
python nocrash.py ${@:1}