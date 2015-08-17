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

import logging
from library import Library

class ProjectBuilder(object):
    def __init__(self, builder):
        self.builder = builder
        self._libraries = {}
        self._logger = logging.getLogger(__name__)

    def addLibrary(self, library_name, sources):
        self._libraries[library_name] = Library(builder=self.builder, sources=sources, name=library_name)

    def addBuildFlags(self, library, flags):
        self._libraries[library].addBuildFlags(flags)

    def build(self):
        for lib_name, lib in self._libraries.iteritems():
            self._logger.debug("Building library %s", lib_name)
            lib.build()








