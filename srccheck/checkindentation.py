# SmokeDetector uses spaces as indentation in all files.
# This tool checks whether there are tabs as indentation in some files, and shows a warning if that's the case,
# because mixed indentation might break SmokeDetector.

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
                if "\t" in line:
                    print(("INDENTATION CHECK FAILED: found tab in %s at line %s. Please use spaces as indentation, " +
                          "using tabs is inconsistent with the rest of the indentation and might break SmokeDetector.")
                          % (filename[len(smokedetector_root):], current_line))
                    sys.exit(1)
    print("INDENTATION CHECK PASSED.")

check_indentation()