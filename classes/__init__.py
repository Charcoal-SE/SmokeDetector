# coding=utf-8
# noinspection PyUnresolvedReferences
import platform
from ._Post import Post, PostParseError
if 'windows' in platform.platform().lower():
    # Only make our Git module available if we're on Windows.
    from ._Git_Windows import Git
