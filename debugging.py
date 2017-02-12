import os

# noinspection PyClassHasNoInit,PyDeprecation
class Debugging:
    enabled = None
    pydev_host = None
    pydev_port = None
    environ_str = None
    environ_args = None

    _envpydev = str(os.environ.get('PYDEVD')).lower()

    if not _envpydev:
        enabled = False
    elif _envpydev.__contains__('true') or _envpydev.__contains__('enable') or _envpydev.__contains__('yes'):
        enabled = True

        environ_str = "PYDEVD='%s'" % 'True'

        host = os.environ.get('PYDEVD_HOST')
        if not host:
            pydev_host = 'localhost'
        else:
            pydev_host = str(host)

        if pydev_host != 'localhost':
            environ_str += " PYDEVD_HOST='%s'" % pydev_host

        port = os.environ.get('PYDEVD_PORT')
        if not port:
            pydev_port = 20500
        else:
            pydev_port = int(port)

        if pydev_port != 20500:
            environ_str += " PYDEVD_PORT='%s'" % pydev_port

        environ_args = environ_str.split()
        environ_str += " "
        environ_dict = {'PYDEVD': enabled, 'PYDEVD_HOST': pydev_host, 'PYDEVD_PORT': pydev_port}

    else:
        enabled = False
