import shlex
import subprocess as sp


def _call_process(execstr):
    proc = sp.Popen(shlex.split(execstr), stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    (stdout, stderr) = proc.communicate()
    retcode = proc.returncode
    return stdout, stderr, retcode


class Git:
    def __call__(self, *args, **kwargs):
        execstr = "git " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        return

    # add
    @staticmethod
    def add(*args):
        execstr = "git add " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # branch
    @staticmethod
    def branch(*args):
        execstr = "git branch " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # Checkout
    @staticmethod
    def checkout(*args):
        execstr = "git checkout " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # commit
    @staticmethod
    def commit(*args):
        execstr = "git commit " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # Config
    @staticmethod
    def config(*args, _ok_code=None):
        execstr = "git config " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode not in _ok_code:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # merge
    @staticmethod
    def merge(*args):
        execstr = "git merge " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # push
    @staticmethod
    def push(*args):
        execstr = "git push " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # remote.update
    class remote:
        def __call__(self, *args):
            execstr = "git remote " + " ".join(*args)
            (stdout, stderr, retcode) = _call_process(execstr)
            if retcode != 0:
                raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
            pass

        @staticmethod
        def update(*args):
            execstr = "git remote update " + " ".join(args)
            (stdout, stderr, retcode) = _call_process(execstr)
            if retcode != 0:
                raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
            pass

    # reset
    @staticmethod
    def reset(*args):
        execstr = "git " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # rev-parse
    @staticmethod
    def rev_parse(*args):
        execstr = "git " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass

    # status
    @staticmethod
    def status(*args):
        execstr = "git " + " ".join(args)
        (stdout, stderr, retcode) = _call_process(execstr)
        if retcode != 0:
            raise sp.CalledProcessError(retcode, execstr, stdout, stderr)
        pass
