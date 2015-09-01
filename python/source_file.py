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

_RE_IS_PACKAGE = re.compile(r"^\s*package\s+\w+\s+is\b", flags=re.I)
_RE_PACKAGE_EXTRACT = re.compile(r"^\s*package\s+|\s+is.*$", flags=re.I)

_RE_IS_PACKAGE_BODY = re.compile(r"^\s*package\s+body\s+\w+\s+is\b", flags=re.I)
_RE_PACKAGE_BODY_EXTRACT = re.compile(r"^\s*package\s+body\s+|\s+is.*$", flags=re.I)

_RE_IS_ENTITY = re.compile(r"^\s*entity\s+\w+\s+is\b", flags=re.I)
_RE_ENTITY_UNIT_EXTRACT = re.compile(r"^\s*entity\s+|\s+is.*$", flags=re.I)

_RE_LIBRARY_DECLARATION = re.compile(r"^\s*library\s.*", flags=re.I)
_RE_LIBRARY_EXTRACT = re.compile(r"^\s*library\s+|\s*;.*", flags=re.I)

_RE_USE_CLAUSE = re.compile(r"^\s*use\s+[\w\.]+.*", flags=re.I)
_RE_USE_EXTRACT = re.compile(r"^\s*use\s+|\..*", flags=re.I)

_RE_LIB_DOT_UNIT = re.compile(r"\b\w+\.\w+\b")

_RE_VALID_NAME_CHECK = re.compile(r"^[a-z]\w*$", flags=re.I)
_RE_LINE_PREPARE = re.compile(r"^\s*|\s*$|\s*--.*")

# FIXME: Built-in libraries should be defined via Vim configuration interface
# and thus be in a specific Python package from which we should import
BUILTIN_LIBRARIES = ('ieee', 'std', 'altera', 'modelsim_lib', 'unisim',
                     'xilinxcorelib', 'synplify', 'synopsis', 'altera_mf',
                     'maxii', 'family_support',)

class VhdlSourceFile(object):
    def __init__(self, filename):
        self.filename = os.path.normpath(filename)
        self._is_package = None
        self._is_entity = None
        self._design_units = []
        self._deps = None

        self._parse()

    def _parse(self):
        deps = {}

        lib_units = []

        for line in open(self.filename, 'r').read().split('\n'):
            line = _RE_LINE_PREPARE.sub('', line).lower()
            if line == '':
                continue

            lib = ''
            if _RE_LIBRARY_DECLARATION.match(line):
                lib = _RE_LIBRARY_EXTRACT.sub("", line)
            elif _RE_USE_CLAUSE.match(line):
                lib = _RE_USE_EXTRACT.sub("", line)

            if lib:
                if lib not in BUILTIN_LIBRARIES and lib not in deps.keys():
                    deps[lib] = []

                    lib_units.append(r"\b%s\.\w+" % lib)

                    lib_units_regex = re.compile('|'.join(lib_units),
                                                 flags=re.I)

            if lib_units and lib_units_regex.findall(line):
                for lib_unit in _RE_LIB_DOT_UNIT.findall(line):
                    lib, unit = lib_unit.split('.')
                    #  if unit != 'all':
                    deps[lib].append(unit)

            design_unit = ''
            if _RE_IS_PACKAGE.match(line):
                self._is_package = True
                design_unit = _RE_PACKAGE_EXTRACT.sub("", line)
            elif _RE_IS_PACKAGE_BODY.match(line):
                self._is_package = True
                design_unit = _RE_PACKAGE_BODY_EXTRACT.sub("", line)
            elif _RE_IS_ENTITY.match(line):
                self._is_entity = True
                design_unit = _RE_ENTITY_UNIT_EXTRACT.sub("", line)

            if design_unit and design_unit not in self._design_units:
                self._design_units.append(design_unit)


        assert self._design_units, \
            "Unable to find design unit name in source %s" % self.filename

        #  self._deps = []
        #  for k, v in deps.iteritems():
        #      if v:
        #          self._deps.append((k, v))
        self._deps = zip(deps.keys(), deps.values())

    def isPackage(self):
        if self._is_package is None:
            self._parse()
        return self._is_package

    def getDesignUnits(self):
        if self._design_units is None:
            self._parse()
            for unit in self._design_units:
                if not _RE_VALID_NAME_CHECK.match(unit):
                    raise RuntimeError("Unit name %s is invalid" % unit)
        return self._design_units

    def getDependencies(self):
        if self._deps is None:
            self._parse()
            for dep_lib, dep_units in self._deps:
                if not _RE_VALID_NAME_CHECK.match(dep_lib):
                    raise RuntimeError("Dependency library %s is invalid" % dep_lib)
                if not len(dep_lib):
                    raise RuntimeError("Dependency library %s is invalid" % dep_lib)
                for dep_unit in dep_units:
                    if not _RE_VALID_NAME_CHECK.match(dep_unit):
                        raise RuntimeError("Dependency unit %s is invalid" % dep_unit)
                    if not len(dep_unit):
                        raise RuntimeError("Dependency unit %s is invalid" % dep_unit)

        return self._deps

    def __str__(self):
        return str(self.filename)

    def getmtime(self):
        return os.path.getmtime(self.filename)

    def abspath(self):
        return os.path.abspath(self.filename)

