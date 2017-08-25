# coding=utf-8
import os


# noinspection PyMissingTypeHints
def list_python_files(root_dir):
    all_files = os.listdir(root_dir)
    py_files = []
    for f in all_files:
        f = root_dir + f
        if os.path.isfile(f) and f.endswith(".py"):
            py_files.append(f)
    return py_files


# noinspection PyMissingTypeHints
def get_smokedetector_root():
    smokedetector_root = "./"
    # The relative path to the directory containing SmokeDetector's files depends on the directory
    # from which you are running srccheck.
    if os.path.isfile("./ws.py"):
        pass  # SmokeDetector's root directory should stay the same
    elif os.path.isfile("../ws.py"):
        smokedetector_root = "../"
    else:
        return False, ""
    return True, smokedetector_root
