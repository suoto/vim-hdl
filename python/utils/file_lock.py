import os

def isPidAlive(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

class FileLock(object):
    def __init__(self, filename):
        self.filename = filename
        self.pid = None

    def __enter__(self):
        if self.isLocked():
            raise RuntimeError("Lock %s is locked by %d" % (self.filename, self.pid))
        open(self.filename, 'w').write(str(os.getpid()))

    def __exit__(self, _type, value, tb):
        os.remove(self.filename)

    def isLocked(self):
        if not os.path.exists(self.filename):
            return False
        try:
            self.pid = int(open(self.filename, 'r').read())
            if isPidAlive(self.pid):
                return True
        except ValueError:
            return False
    def getOwnerPid(self):
        if self.isLocked():
            return self.pid


