import os


# Allows use of `environ_or_none("foo") or "default"` shorthand
def environ_or_none(key):
    try:
        return os.environ[key]
    except:
        return None
