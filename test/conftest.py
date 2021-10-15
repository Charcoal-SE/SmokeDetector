from unittest.mock import MagicMock
import os
import sys


def raise_system_exit(code):
    raise SystemExit(code)


os._exit = MagicMock(
    spec=os._exit, wraps=None, side_effect=raise_system_exit
)  # Prevent exit from os._exit()
sys.exit = MagicMock(
    spec=sys.exit, wraps=None, side_effect=raise_system_exit
)  # Prevent exit from sys.exit()
