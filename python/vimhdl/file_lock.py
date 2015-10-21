# This file is part of vim-hdl.
#
# vim-hdl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# vim-hdl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.

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
        self.lock_owner = None

    def isLocked(self):
        if not os.path.exists(self.filename):
            return False
        try:
            self.lock_owner = int(open(self.filename, 'r').read())
            if isPidAlive(self.lock_owner):
                return True
        except ValueError:
            return False

    def __enter__(self):
        if self.isLocked():
            raise RuntimeError("Lock %s is locked by %d" % (self.filename, self.lock_owner))
        open(self.filename, 'w').write(str(os.getpid()))

    def __exit__(self, _type, value, tb):
        os.remove(self.filename)


