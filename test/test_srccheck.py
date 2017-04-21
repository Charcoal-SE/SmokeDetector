# coding=utf-8
# SmokeDetector uses snake_case for all function names.
# This tool checks for inconsistency: if it notices that there are capitalized letters in a function name,
# it throws an error.

from srccheckbase import get_smokedetector_root, list_python_files
import pytest


def fail_with_message(message):
    pytest.fail(message)


# noinspection PyMissingTypeHints
def test_check_function_names():
    found, smokedetector_root = get_smokedetector_root()
    if not found:
        fail_with_message("ERROR: could not find directory containing SmokeDetector's files -- failed to find ws.py.")
    py_files = list_python_files(smokedetector_root)
    for filename in py_files:
        with open(filename, "r", encoding='utf-8') as f:
            lines = f.readlines()
            current_line = 0
            for line in lines:
                current_line += 1
                line = line.strip()
                if line.startswith("def "):
                    function_name = line[4:].split("(")[0]
                    if function_name.lower() != function_name:
                        fail_with_message(("FUNCTION NAME CHECK FAILED in {} at line {}. SmokeDetector uses " +
                                           "snake_case (and lowercase) function names. This tool detected a function " +
                                           "name that has a capitalized letter, which is inconsistent with the other " +
                                           "function names.").format(filename[len(smokedetector_root):], current_line))


# noinspection PyMissingTypeHints
def test_check_indentation():
    found, smokedetector_root = get_smokedetector_root()
    if not found:
        fail_with_message("ERROR: could not find directory containing SmokeDetector's files -- failed to find ws.py.")
    py_files = list_python_files(smokedetector_root)
    for filename in py_files:
        with open(filename, "r", encoding='utf-8') as f:
            lines = f.readlines()
            current_line = 0
            for line in lines:
                current_line += 1
                if "\t" in line:
                    fail_with_message(("INDENTATION CHECK FAILED: " +
                                       "found tab in {} at line {}. Please use spaces as indentation, " +
                                       "using tabs is inconsistent with the rest of the indentation and might break " +
                                       "SmokeDetector.").format(filename[len(smokedetector_root):], current_line))
