#!/usr/bin/env python3
# coding=utf-8
import os


# Pickle files should be .p file extensions, not .txt.  This script handles moving the file extensions
# to the correct names.

def fix_extension_on_pickles():
    pickles = ['falsePositives.txt', 'whitelistedUsers.txt', 'blacklistedUsers.txt', 'ignoredPosts.txt',
               'autoIgnoredPosts.txt', 'users.txt', 'notifications.txt', 'whyData.txt', 'whyDataAllspam.txt',
               'latestMessages.txt', 'apiCalls.txt', 'bodyfetcherQueue.txt', 'bodyfetcherMaxIds.txt']

    # Check if each of these is a file, and if it exists, rename it to .p extension.
    for txt in pickles:
        try:
            if os.path.isfile(txt):
                os.rename(txt, (txt[:-4] + '.p'))
        except OSError as e:
            raise RuntimeError("Could not migrate Pickle file from .txt extension to .p extension.") from e


if __name__ == "__main__":
    fix_extension_on_pickles()
