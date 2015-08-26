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
from multiprocessing.pool import ThreadPool

class ProjectBuilder(object):
    MAX_ITERATIONS_UNTIL_STABLE = 20
    BUILD_WORKERS = 5

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
    def _buildUntilStable(self, f, args=(), kwargs={}):
        failed_builds = []
        previous_failed_builds = None
        for iterations in range(self.MAX_ITERATIONS_UNTIL_STABLE):
            r = []
            for lib_name, source, errors, warnings in f(*args, **kwargs):
                if errors:
                    failed_builds.append((lib_name, source, errors, warnings))
                if errors or warnings:
                    r.append((lib_name, source, errors, warnings))

            if failed_builds == previous_failed_builds:
                self._logger.info("'%s' is stable in %d after %d iterations", f.func_name, len(failed_builds), iterations + 1)
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
    def buildPackagesAsync(self, workers=None, forced=False):
        if workers is None:
            workers = self.BUILD_WORKERS

        self._logger.info("Building packages with %d workers", workers)
        pool = ThreadPool(workers)

        f_args = []
        for lib_name, lib in self._libraries.iteritems():
            f_args.append((lib_name, lib, 'buildPackages', forced, ))

        r = pool.map_async(runAsync, f_args)
        r.ready()
        r = r.get()

        for _r in r:
            for lib_name, source, errors, warnings in _r:
                yield lib_name, source, errors, warnings
    def buildAllButPackages(self, forced=False):
        for lib_name, lib in self._libraries.iteritems():
            for source, errors, warnings in lib.buildAllButPackages(forced):
                yield lib_name, source, errors, warnings
    def buildAllButPackagesAsync(self, workers=None, forced=False):
        if workers is None:
            workers = self.BUILD_WORKERS
        pool = ThreadPool(workers)

        self._logger.info("Building all but packages with %d workers", workers)

        f_args = []
        for lib_name, lib in self._libraries.iteritems():
            f_args.append((lib_name, lib, 'buildAllButPackages', forced, ))

        r = pool.map_async(runAsync, f_args)
        pool.close()
        pool.join()
        r.ready()
        r = r.get()

        for _r in r:
            for lib_name, source, errors, warnings in _r:
                if errors or warnings:
                    self._logger.info("Messages for %s %s", lib_name, source)
                if errors:
                    self._logger.error("\n".join(errors))
                if warnings:
                    self._logger.warning("\n".join(warnings))
                yield lib_name, source, errors, warnings
    def buildAll(self, forced=False):
        for lib_name, lib in self._libraries.iteritems():
            for source, errors, warnings in lib.buildAll(forced):
                yield lib_name, source, errors, warnings
    def build(self, forced=False):
        for lib in self._libraries.itervalues():
            lib.createOrMapLibrary()
        r = self._buildUntilStable(self.buildPackages, args=[forced,])
        r += self._buildUntilStable(self.buildAllButPackages, args=[forced,])

        for lib_name, source, errors, warnings in r:
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)
    def buildAsync(self, workers=None, forced=False):
        if workers is None:
            workers = self.BUILD_WORKERS
        for lib in self._libraries.itervalues():
            lib.createOrMapLibrary()

        for lib_name, source, errors, warnings in self._buildUntilStable(self.buildPackagesAsync, kwargs={'workers': workers, 'forced' : forced}):
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)

        for lib_name, source, errors, warnings in self._buildUntilStable(self.buildAllButPackagesAsync, kwargs={'workers': workers, 'forced' : forced}):
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)

def runAsync(args):
    lib_name = args[0]
    lib_obj = args[1]
    meth = args[2]
    f_args = args[3:]
    r = []
    for _r in getattr(lib_obj, meth)(*f_args):
        r.append([lib_name] + _r)

    return r
