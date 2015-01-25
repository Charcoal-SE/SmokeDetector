# Runs all srccheck scripts.

import sys
import subprocess
from srccheckbase import *

def check_all():
    srccheck_root = "./"
    # The relative path to the directory of srccheck scripts depends on the directory from which you run checkall.py
    if os.path.isfile("./srccheckbase.py"):
        pass  # srccheck_root says the same
    elif os.path.isdir("srccheck") and os.path.isfile("srccheck/srccheckbase.py"):
        srccheck_root = "./srccheck/"
    else:
        print("ERROR: srccheck files not found.")
        sys.exit(1)
    py_files = list_python_files(srccheck_root)
    srccheck_files = []
    for filename in py_files:
        if not filename.endswith("srccheckbase.py") and not filename.endswith("checkall.py"):
            srccheck_files.append(filename)
    for filename in srccheck_files:
        sp = subprocess.Popen([sys.executable, filename], stdout=subprocess.PIPE)
        data = sp.communicate()
        returncode = sp.returncode
        print(data[0])
        if returncode != 0:
            sys.exit(returncode)

check_all()