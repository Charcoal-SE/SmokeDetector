# SmokeDetector uses snake_case for all function names.
# This tool checks for inconsistency: if it notices that there are capitalized letters in a function name,
# it throws an error.

import sys
from srccheckbase import *


def check_indentation():
    found, smokedetector_root = get_smokedetector_root()
    if not found:
        print("ERROR: could not find directory containing SmokeDetector's files -- failed to find ws.py.")
        sys.exit(1)
    py_files = list_python_files(smokedetector_root)
    for filename in py_files:
        with open(filename, "r") as f:
            lines = f.readlines()
            current_line = 0
            for line in lines:
                current_line += 1
                line = line.strip()
                if line.startswith("def "):
                    function_name = line[4:].split("(")[0]
                    if function_name.lower() != function_name:
                        print(("FUNCTION NAME CHECK FAILED in %s at line %s. " +
                               "SmokeDetector uses snake_case (and lowercase) function names. This tool detected " +
                               "a function name that has a capitalized letter, which is inconsistent with the " +
                               "other function names") % (filename[len(smokedetector_root):], current_line))
                        sys.exit(1)
    print("FUNCTION NAME CHECK PASSED.")

check_indentation()