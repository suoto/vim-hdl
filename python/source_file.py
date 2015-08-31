# This file is part of hdl-check-o-matic.
#
# hdl-check-o-matic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# hdl-check-o-matic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hdl-check-o-matic.  If not, see <http://www.gnu.org/licenses/>.

import re, os

_RE_IS_PACKAGE = re.compile(
    r"^\s*package\s+\w+\s+is\b|^\s*package\s+body\s+\w+\s+is\b",
    flags=re.I)

_RE_IS_ENTITY = re.compile(
    r"^\s*entity\s+\w+\s+is\b",
    flags=re.I)

_RE_LIBRARY_DECLARATION = re.compile(r"^\s*library\s.*", flags=re.I)
_RE_LIBRARY_EXTRACT = re.compile(r"^\s*library\s+|\s*;.*", flags=re.I)

_RE_USE_CLAUSE = re.compile(r"^\s*use\s+[\w\.]+.*", flags=re.I)
_RE_USE_EXTRACT = re.compile(r"^\s*use\s+|\s*;.*", flags=re.I)

_RE_ENTITY_CLAUSE = re.compile(r"^\s*\w+\s*:\s*entity\s+\w+\.\w+.*", flags=re.I)
_RE_ENTITY_EXTRACT = re.compile(r"^\s*\w+\s*:\s*entity\s+|\s*$", flags=re.I)

# FIXME: Built-in libraries should be defined via Vim configuration interface
# and thus be in a specific Python package from which we should import
BUILTIN_LIBRARIES = ('ieee', 'std', 'altera', 'modelsim_lib', 'unisim',
                     'xilinxcorelib', 'synplify', 'synopsis', 'altera_mf')

class VhdlSourceFile(object):
    def __init__(self, filename):
        self.filename = filename
        self._is_package = None
        self._is_entity = None
        self._design_unit_name = None
        self._deps = None

    def __getattr__(self, attr):
        if hasattr(str, attr):
            return getattr(self.filename, attr)
        raise AttributeError()

    def _parse(self):
        deps = {}
        for line in open(self.filename, 'r').read().split('\n'):
            line = re.sub(r"\s*--.*", "", line).lower()
            if re.match(r"^\s*$", line):
                continue
            if _RE_LIBRARY_DECLARATION.match(line):
                lib = _RE_LIBRARY_EXTRACT.sub("", line)
                if lib not in BUILTIN_LIBRARIES and lib not in deps.keys():
                    deps[lib] = []
            if _RE_USE_CLAUSE.match(line):
                lib, package = \
                        _RE_USE_EXTRACT.sub("", line).lower().split('.')[:2]
                if package == 'all':
                    if lib not in BUILTIN_LIBRARIES and lib not in deps.keys():
                        deps[lib] = []
                else:
                    if lib not in BUILTIN_LIBRARIES:
                        if lib not in deps.keys():
                            deps[lib] = []
                        deps[lib].append(package)
            if _RE_ENTITY_CLAUSE.match(line):
                lib, package = \
                        _RE_ENTITY_EXTRACT.sub("", line).lower().split('.')[:2]
                if lib not in deps.keys():
                    deps[lib] = []
                deps[lib].append(package)

            if self._design_unit_name is None:
                if _RE_IS_PACKAGE.match(line):
                    self._is_package = True
                    self._design_unit_name = \
                            re.sub(r"^\s*package\s+|\s+is.*$", "", line)
                if _RE_IS_ENTITY.match(line):
                    self._is_entity = True
                    self._design_unit_name = \
                            re.sub(r"^\s*entity\s+|\s+is.*$", "", line)

        self._deps = zip(deps.keys(), deps.values())

    def isPackage(self):
        if self._is_package is None:
            self._parse()
        return self._is_package

    def getUnitName(self):
        if self._design_unit_name is None:
            self._parse()
        return self._design_unit_name

    def getDependencies(self):
        if self._deps is None:
            self._parse()
        return self._deps

    def __str__(self):
        return str(self.filename)

    def getmtime(self):
        return os.path.getmtime(self.filename)

    def abspath(self):
        return os.path.abspath(self.filename)

