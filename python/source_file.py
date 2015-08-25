# This file is part of hdl-syntax-checker.
#
# hdl-syntax-checker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# hdl-syntax-checker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hdl-syntax-checker.  If not, see <http://www.gnu.org/licenses/>.

import re, os

RE_IS_PACKAGE = re.compile(r"^\s*package\s+\w+\s+is\b|^\s*package\s+body\s+\w+\s+is\b", flags=re.I)

class VhdlSourceFile(object):
    def __init__(self, filename):
        self.filename = filename
        self._isPkg = None

    def __getstate__(self):
        state = {'filename' : self.filename,
                '_isPkg' : self._isPkg}
        return state
    def __setstate__(self, d):
        self.__dict__.update(d)
    def __getattr__(self, attr):
        if hasattr(self.filename, attr):
            return getattr(self.filename, attr)

    def isPackage(self):
        if self._isPkg is None:
        #  if True:
            self._isPkg = False
            for l in open(self.filename, 'r').read().split('\n'):
                if RE_IS_PACKAGE.match(l):
                    self._isPkg = True
                    break
        return self._isPkg

    def __str__(self):
        return str(self.filename)

    def getmtime(self):
        return os.path.getmtime(self.filename)
    def abspath(self):
        return os.path.abspath(self.filename)

