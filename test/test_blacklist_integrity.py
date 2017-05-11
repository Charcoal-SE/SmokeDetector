#!/usr/bin/env python3

from glob import glob


def test_blacklist_integrity():
    for bl_file in glob('bad_*.txt') + glob('blacklisted_*.txt'):
        with open(bl_file, 'r') as lines:
            seen = dict()
            for lineno, line in enumerate(lines, 1):
                if line.endswith('\r\n'):
                    raise(ValueError('{0}:{1}:DOS line ending'.format(bl_file, lineno)))
                if not line.endswith('\n'):
                    raise(ValueError('{0}:{1}:No newline'.format(bl_file, lineno)))
                if line == '\n':
                    raise(ValueError('{0}:{1}:Empty line'.format(bl_file, lineno)))
                if line in seen:
                    raise(ValueError('{0}:{1}:Duplicate entry {2} (also on line {3})'.format(
                        bl_file, lineno, line.rstrip('\n'), seen[line])))
                seen[line] = lineno
