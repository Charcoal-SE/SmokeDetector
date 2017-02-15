import os

# Pickle files should be .p file extensions, not .txt.  Add a migration script.
def rename_pickles():
    pickles = ['falsePositives.txt', 'whitelistedUsers.txt', 'blacklistedUsers.txt', 'ignoredPosts.txt',
                    'autoIgnoredPosts.txt', 'users.txt', 'notifications.txt', 'whyData.txt', 'whyDataAllspam.txt',
                    'latestMessages.txt', 'apiCalls.txt', 'bodyfetcherQueue.txt', 'bodyfetcherMaxIds.txt']

    # Check if each of these is a file, and if it exists, rename it to .p extension.
    for txt in pickles:
        try:
            if os.path.isfile(txt):
                os.rename(txt, (txt[:-4] + '.p'))
        except:
            raise RuntimeError("Could not migrate Pickle file from .txt extension to .p extension.")