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

import re
import os
import logging
from utils import memoid

_RE_VALID_NAME_CHECK = re.compile(r"^[a-z]\w*$", flags=re.I)

_RE_DESIGN_UNITS = re.compile('|'.join([
    r"(?<=entity)\s+\w+\s+(?=is\b)",
    r"(?<=package)\s+\w+\s+(?=is\b)",
    r"(?<=package)\s+(?<=body)\s+\w+\s+(?=is\b)",
    ]), flags=re.I)

_RE_LIBRARIES = re.compile(r"(?<=library)\s+\w+\b", flags=re.I)
_RE_USE_CLAUSES = re.compile(r"(?<=use)\s+\w+\.\w+\b", flags=re.I)

_RE_WHITESPACES = re.compile(r"^\s*|\s*$")

_RE_PRE_PROC = re.compile(r"\s*--[^\n]*\n|\s+")

# FIXME: Built-in libraries should be defined via Vim configuration interface
# and thus be in a specific Python package from which we should import
BUILTIN_LIBRARIES = ('ieee', 'std', 'unisim', 'xilinxcorelib', 'synplify',
                     'synopsis', 'maxii', 'family_support')

_logger = logging.getLogger(__name__)

import threading

class VhdlSourceFile(object):
    def __init__(self, filename):
        self.filename = os.path.normpath(filename)
        self._design_units = None
        self._deps = None
        self._mtime = 0

        self._lock = threading.Lock()
        threading.Thread(target=self._doParse).start()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_lock']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = threading.Lock()

    def _parse(self):
        "Wraps self._doParse with lock acquire/release"
        # If we need to parse, acquire the lock
        try:
            self._lock.acquire()
            self._doParse()
            self._mtime = self.getmtime()
        finally:
            self._lock.release()

    def changed(self):
        return self._mtime >= self.getmtime()

    def _doParse(self):
        "Parses the source file to find design units and dependencies"
        # Check if we really need to parse

        _logger.debug("Parsing %s", str(self))

        # Replace everything from comment ('--') until a line break and
        # converts to lowercase
        text = _RE_PRE_PROC.sub(" ", open(self.filename, 'r').read()).lower()

        # Search for design units. We should get things like entities
        # and packages
        self._design_units = []
        for unit in _RE_DESIGN_UNITS.findall(text):
            self._design_units.append(_RE_WHITESPACES.sub("", unit))

        # Gets libraries referred
        libs = [_RE_WHITESPACES.sub("", x) for x in _RE_LIBRARIES.findall(text)]

        # If there are no libraries, we won't search for units
        # instantiated using the format 'lib.unit'
        dependencies = []
        if libs:
            _re_deps = re.compile(r'|'.join([r"%s\.\w+" % x for x in libs]), flags=re.I)

            for dep in [_RE_WHITESPACES.sub("", x) for x in _re_deps.findall(text)]:
                dep = dep.split('.')
                if dep not in dependencies:
                    dependencies.append(dep)

        # Search for occurrences of use lib.unit
        for use_clause in [_RE_WHITESPACES.sub("", x) \
                for x in _RE_USE_CLAUSES.findall(text)]:
            dep = use_clause.split('.')
            if dep not in dependencies:
                dependencies.append(dep)

        # Finally, remove built-in libraries from the list we found
        self._deps = []
        for dep in dependencies:
            if dep[0] not in BUILTIN_LIBRARIES and dep not in self._deps:
                self._deps.append(dep)

        self._sanityCheckNames()

    def _sanityCheckNames(self):
        """Sanity check on the names we found to catch errors we
        haven't covered"""
        for unit in self._design_units:
            if not _RE_VALID_NAME_CHECK.match(unit):
                raise RuntimeError("Unit name %s is invalid" % unit)

        for dep_lib, dep_unit in self._deps:
            if not _RE_VALID_NAME_CHECK.match(dep_lib):
                raise RuntimeError("Dependency library %s is invalid" % dep_lib)
            if not len(dep_lib):
                raise RuntimeError("Dependency library %s is invalid" % dep_lib)
            if not _RE_VALID_NAME_CHECK.match(dep_unit):
                raise RuntimeError("Dependency unit %s is invalid" % dep_unit)
            if not len(dep_unit):
                raise RuntimeError("Dependency unit %s is invalid" % dep_unit)

    def getDesignUnits(self):
        if self.changed():
            self._parse()
        return self._design_units

    def getDependencies(self):
        if self.changed():
            self._parse()
        return self._deps

    def __repr__(self):
        return "VhdlSourceFile('%s')" % self.abspath()

    def __str__(self):
        return str(self.filename)

    def getmtime(self):
        return os.path.getmtime(self.filename)

    @memoid
    def abspath(self):
        return os.path.abspath(self.filename)

