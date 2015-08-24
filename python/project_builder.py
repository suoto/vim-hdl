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
    MAX_ITERATIONS_UNTIL_STABLE = 20
    def __init__(self, builder):
        self.builder = builder
        self._libraries = {}
        self._logger = logging.getLogger(__name__)
    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state
    def __setstate__(self, d):
        self._logger = logging.getLogger(d['_logger'])
        del d['_logger']
        self.__dict__.update(d)
    def _buildUntilStable(self, f, *args, **kwargs):
        failed_builds = []
        previous_failed_builds = None
        for iterations in range(self.MAX_ITERATIONS_UNTIL_STABLE):
            r = []
            for lib_name, source, errors, warnings in f(*args, **kwargs):
                if errors:
                    failed_builds.append((lib_name, source, errors))
                if errors or warnings:
                    r.append((lib_name, source, errors, warnings))

            if failed_builds == previous_failed_builds:
                self._logger.info("'%s' is stable in %d after %d iterations", f.func_name, len(failed_builds), iterations)
                break

            previous_failed_builds = failed_builds
            failed_builds = []

            if iterations == self.MAX_ITERATIONS_UNTIL_STABLE - 1:
                self._logger.error("Iteration limit of %d reached", self.MAX_ITERATIONS_UNTIL_STABLE)
        return r
    def addLibrary(self, library_name, sources):
        self._libraries[library_name] = Library(builder=self.builder, sources=sources, name=library_name)
    def addBuildFlags(self, library, flags):
        self._libraries[library].addBuildFlags(flags)
    def buildPackages(self, forced=False):
        for lib_name, lib in self._libraries.iteritems():
            for source, errors, warnings in lib.buildPackages(forced):
                yield lib_name, source, errors, warnings
    def buildAllButPackages(self, forced=False):
        for lib_name, lib in self._libraries.iteritems():
            for source, errors, warnings in lib.buildAllButPackages(forced):
                yield lib_name, source, errors, warnings
    def buildAll(self):
        for lib_name, lib in self._libraries.iteritems():
            self._logger.debug("Building library %s", lib_name)
            for source, errors, warnings in lib.build():
                if errors:
                    self._logger.info("%s (%s) error messages", source, lib_name)
                    for error in errors:
                        self._logger.info(" - " + error)
                if warnings:
                    self._logger.info("%s (%s) warning messages", source, lib_name)
                    for warning in warnings:
                        self._logger.info(" - " + warning)
    def build(self, forced=False):
        r = self._buildUntilStable(self.buildPackages, forced)
        r += self._buildUntilStable(self.buildAllButPackages, forced)
        for lib_name, source, errors, warnings in r:
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)


