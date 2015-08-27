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

_RE_IS_PACKAGE = re.compile(
    r"^\s*package\s+\w+\s+is\b|^\s*package\s+body\s+\w+\s+is\b",
    flags=re.I)

_RE_LIBRARY_DECLARATION = re.compile(r"^\s*library\s.*", flags=re.I)
_RE_LIBRARY_EXTRACT = re.compile(r"^\s*library\s+|\s*;.*", flags=re.I)

_RE_USE_CLAUSE = re.compile(r"^\s*use\s+[\w\.]+.*", flags=re.I)
_RE_USE_EXTRACT = re.compile(r"^\s*use\s+|\s*;.*", flags=re.I)

# FIXME: Built-in libraries should be defined via Vim configuration interface
# and thus be in a specific Python package from which we should import
BUILTIN_LIBRARIES = ('ieee', 'std', 'altera', 'modelsim_lib', 'unisim',
                     'xilinxcorelib', 'synplify', 'synopsis', 'altera_mf')

class VhdlSourceFile(object):
    def __init__(self, filename):
        self.filename = filename
        self._is_package = None
        self._package_name = None

    def __getattr__(self, attr):
        if hasattr(str, attr):
            return getattr(self.filename, attr)
        raise AttributeError()

    def isPackage(self):
        if self._is_package is None:
            self._is_package = False
            for l in open(self.filename, 'r').read().split('\n'):
                if _RE_IS_PACKAGE.match(l):
                    self._is_package = True
                    break
        return self._is_package

    def getPackageName(self):
        if self._package_name is None:
            for l in open(self.filename, 'r').read().split('\n'):
                if _RE_IS_PACKAGE.match(l):
                    self._package_name = \
                            re.sub(r"^\s*package\s+|\s+is.*$", "", l)
                    break
        return self._package_name

    def getDependencies(self):
        libs = []
        packages = []
        for l in open(self.filename, 'r').read().split('\n'):
            l = re.sub(r"\s*--.*", "", l)
            if _RE_LIBRARY_DECLARATION.match(l):
                lib = _RE_LIBRARY_EXTRACT.sub("", l)
                if lib not in BUILTIN_LIBRARIES:
                    libs.append(lib)
            if _RE_USE_CLAUSE.match(l):
                lib, package = _RE_USE_EXTRACT.sub("", l).split('.')[:2]
                if lib not in BUILTIN_LIBRARIES:
                    packages.append((lib, package))
        return libs, packages

    def __str__(self):
        return str(self.filename)

    def getmtime(self):
        return os.path.getmtime(self.filename)

    def abspath(self):
        return os.path.abspath(self.filename)

