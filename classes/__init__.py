# coding=utf-8
# noinspection PyUnresolvedReferences
import platform
from .Post import Post, PostParseError
if 'windows' in platform.platform().lower():
    # Only make our Git module available if we're on Windows.
    from .Git import Git

