# coding=utf-8
import shlex
import subprocess as sp
import platform
from helpers import log

if 'windows' not in platform.platform().lower():
    raise NotImplementedError("Use the `sh` module's `git` from PyPI instead!")


GitError = sp.CalledProcessError


def _call_process(execcmd, _ok_code=None, return_data=True, return_tuple=False):
    execcmd = ('git',) + execcmd
    log('debug', 'Windows Git:', execcmd, '::  _ok_code:', _ok_code, '::  return_data', return_data, '::  return_tuple', return_tuple)
    proc = sp.Popen(execcmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    (stdout, stderr) = proc.communicate()
    retcode = proc.returncode
    if retcode != 0:
        if _ok_code and retcode in _ok_code:
            pass
        else:
            log('error', 'Error: Windows Git:', execcmd, '::  retcode:', retcode, '::  stdout:', stdout, '::  stderr:', stderr)
            raise GitError(retcode, execcmd, stdout, stderr)
    if return_tuple:
        to_return = (stdout, stderr, retcode)
        log('debug', 'Windows Git:', execcmd, '::  returning tuple:', to_return)
        return to_return
    if return_data:
        to_return = stdout.decode("utf-8")
        log('debug', 'Windows Git:', execcmd, '::  returning data:', to_return)
        return to_return


class Git(object):
    # git
    def __init__(self, *args):
        if len(args) > 0:
            _call_process(args)

    def __getattribute__(self, name):
        def interceptor(*args, **kwargs):
            adjusted_name = name.replace('_', '-')
            return _call_process((adjusted_name,) + args, **kwargs)
        try:
            method_in_class = object.__getattribute__(self, name)
        except AttributeError:
            return interceptor
        else:
            return method_in_class

    # git
    @staticmethod
    def __call__(*args, **kwargs):
        _call_process(args, **kwargs)

    # remote.update
    class remote:  # noqa: N801
        @staticmethod
        def update(*args, **kwargs):
            _call_process(('remote', 'update',) + args, **kwargs)

    # status with colours stripped
    @staticmethod
    def status_stripped(*args, **kwargs):
        return _call_process(('-c', 'color.status=false', 'status',) + args, **kwargs)

    # diff with colours stripped, filenames only
    @staticmethod
    def diff_filenames(*args, **kwargs):
        return _call_process(('-c', 'color.diff=false', 'diff', '--name-only',) + args, **kwargs)


git = Git()
git_version = git.version(return_data=True).strip()
if ('indows' not in git_version):
    log('error', 'Error: Windows Git: git is not a Windows version: ', git_version)
    raise NotImplementedError('The git program being used, ' + git_version + ', is not a Windows based version. Be sure you installed Git for Windows and that it is in your path before any other versions (e.g. before Cygwin).')
