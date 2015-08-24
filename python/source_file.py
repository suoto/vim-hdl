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

class VhdlSourceFile(str):
    def __init__(self, filename):
        self.filename = filename
        super(VhdlSourceFile, self).__init__(filename)

    def isPackage(self):
        r = False
        for l in open(self.filename, 'r').read().split('\n'):
            if RE_IS_PACKAGE.match(l):
                r = True
                break
        return r

    def __str__(self):
        return str(self.filename)

    def getmtime(self):
        return os.path.getmtime(self.filename)
    def abspath(self):
        return os.path.abspath(self.filename)

