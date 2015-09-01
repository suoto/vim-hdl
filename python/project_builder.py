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

import logging
from library import Library
from multiprocessing.pool import ThreadPool

# pylint: disable=star-args, missing-docstring

class ProjectBuilder(object):
    "hdl-synchecker project class"
    MAX_ITERATIONS_UNTIL_STABLE = 20
    MAX_BUILD_STEPS = 10
    BUILD_WORKERS = 5

    def __init__(self, builder):
        self.builder = builder
        self._libraries = {}
        self._dependency_rev_map = {}
        self._dependency_map = {}
        self._logger = logging.getLogger(__name__)

        self._cache = {}

        self._sources_with_errors = []
        self._sources_with_warnings = []

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        self._logger = logging.getLogger(state['_logger'])
        del state['_logger']
        self.__dict__.update(state)

    # pylint: disable=E0213,W0212,E1102
    def _memoid(f):
        def _memoid_w(self, *args, **kwargs):
            k = str((f, args, kwargs))
            if not hasattr(self, '_cache'):
                self._cache = {}
            if k not in self._cache.keys():
                self._cache[k] = f(self, *args, **kwargs)
            return self._cache[k]
        return _memoid_w

    # pylint: enable=E0213,W0212,E1102
    def _buildUntilStable(self, f, args=(), kwargs={}):
        failed_builds = []
        previous_failed_builds = None
        for iterations in range(self.MAX_ITERATIONS_UNTIL_STABLE):
            ret = []
            for lib_name, source, errors, warnings in f(*args, **kwargs):
                if errors:
                    failed_builds.append((lib_name, source, errors, warnings))
                if errors or warnings:
                    ret.append((lib_name, source, errors, warnings))

            if failed_builds == previous_failed_builds:
                self._logger.info("'%s' is stable in %d after %d iterations",
                                  f.func_name,
                                  len(failed_builds),
                                  iterations + 1)
                break

            previous_failed_builds = failed_builds
            failed_builds = []

            if iterations == self.MAX_ITERATIONS_UNTIL_STABLE - 1:
                self._logger.error("Iteration limit of %d reached",
                                   self.MAX_ITERATIONS_UNTIL_STABLE)
        return ret

    def addLibrary(self, library_name, sources):
        self._libraries[library_name] = \
                Library(builder=self.builder,
                        sources=sources,
                        name=library_name)

    def hasLibrary(self, library_name):
        return library_name.lower() in self._libraries.keys()

    def addLibrarySources(self, library_name, sources):
        self._libraries[library_name].addSources(sources)

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

        pool_results = pool.map_async(runAsync, f_args)
        pool_results.ready()

        for pool_result in pool_results.get():
            for lib_name, source, errors, warnings in pool_result:
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

        pool_results = pool.map_async(runAsync, f_args)
        pool.close()
        pool.join()
        pool_results.ready()

        for pool_result in pool_results:
            for lib_name, source, errors, warnings in pool_result:
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

        for _, _, errors, warnings in r:
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)

    def buildAsync(self, workers=None, forced=False):
        if workers is None:
            workers = self.BUILD_WORKERS
        for lib in self._libraries.itervalues():
            lib.createOrMapLibrary()

        for _, _, errors, warnings in \
                self._buildUntilStable(self.buildPackagesAsync,
                                       kwargs={'workers': workers,
                                               'forced' : forced}):
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)

        for _, _, errors, warnings in \
                self._buildUntilStable(self.buildAllButPackagesAsync,
                                       kwargs={'workers': workers,
                                               'forced' : forced}):
            if errors:
                print "\n".join(errors)
            if warnings:
                print "\n".join(warnings)

    @_memoid
    def _dependencyRevMap(self):
        for lib in self._libraries.values():
            for src_file, src_deps in lib.getDependencies():
                for src_dep in src_deps:
                    dep_lib, dep_pkgs = src_dep
                    for dep_pkg in dep_pkgs:
                        dep_key = "%s.%s" % (dep_lib, dep_pkg)
                        if dep_key not in self._dependency_rev_map.keys():
                            self._dependency_rev_map[dep_key] = []
                        self._dependency_rev_map[dep_key].append(src_file.filename)

    @_memoid
    def _dependencyMap(self):
        for lib_name, lib in self._libraries.items():
            this_lib_map = {}
            for src_file, src_deps in lib.getDependencies():
                if src_file not in this_lib_map.keys():
                    this_lib_map[src_file] = []
                for dep_lib, dep_pkgs in src_deps:
                    for dep_pkg in dep_pkgs:
                        this_lib_map[src_file].append((dep_lib, dep_pkg))

            self._dependency_map[lib_name] = this_lib_map

    def _getBuildSteps(self):
        self._dependencyMap()

        this_build = []
        units_built = []

        for step in range(self.MAX_BUILD_STEPS):
            units_built += list(set(this_build) - set(units_built))

            this_build = []
            this_step = {}
            for lib_name, lib_deps in self._dependency_map.iteritems():
                for src, src_deps in lib_deps.iteritems():
                    for design_unit in src.getDesignUnits():
                        if (lib_name, design_unit) in units_built:
                            continue
                        if (lib_name, 'all') not in this_build:
                            this_build.append((lib_name, 'all'))
                        if set(src_deps).issubset(units_built):
                            if (lib_name, design_unit) not in this_build:
                                this_build.append((lib_name, design_unit))
                            if lib_name not in this_step.keys():
                                this_step[lib_name] = []
                            if src not in this_step[lib_name]:
                                this_step[lib_name].append(src)

            if not this_build:
                break

            yield this_step

            if step == self.MAX_BUILD_STEPS:
                self._logger.error("Max build steps of %d reached, stopping",
                                   self.MAX_BUILD_STEPS)

        self._logMissingDependencies(units_built)

    def _logMissingDependencies(self, units_built):
        this_step = {}
        for lib_name, lib_deps in self._dependency_map.iteritems():
            for src, src_deps in lib_deps.iteritems():
                for design_unit in src.getDesignUnits():
                    if (lib_name, design_unit) not in units_built:
                        missing_deps = []
                        for dep_lib_name, unit_name in set(src_deps) - set(units_built):
                            if "%s.%s" % (dep_lib_name, unit_name) not in missing_deps:
                                missing_deps.append(
                                    "%s.%s" % (dep_lib_name, unit_name))
                        if missing_deps:
                            self._logger.warning(
                                "Missing dependencies for '%s': %s", src, ", ".join(missing_deps))

                        if lib_name not in this_step.keys():
                            this_step[lib_name] = []
                        this_step[lib_name].append(src)

    def buildByDependency(self):
        for lib in self._libraries.itervalues():
            lib.createOrMapLibrary()

        step_cnt = 0
        for step in self._getBuildSteps():
            step_cnt += 1
            self._logger.debug("Step %d", step_cnt)

            for lib_name, sources in step.iteritems():
                self._logger.debug("  - %s", lib_name)
                for source in sources:
                    self._logger.debug("    - %s", str(source))

                for source, errors, warnings in self._libraries[lib_name].buildSources(sources):
                    for msg in errors + warnings:
                        print msg

    def buildByDependencyWithThreads(self, threads=None):
        threads = threads or self.BUILD_WORKERS
        for lib in self._libraries.itervalues():
            lib.createOrMapLibrary()

        sources_with_errors = []
        sources_with_warnings = []

        step_cnt = 0
        for step in self._getBuildSteps():
            step_cnt += 1
            self._logger.debug("Step %d", step_cnt)

            f_args = []

            fd = open('.build/step_%d.log' % step_cnt, 'w')
            for lib_name, sources in step.iteritems():
                self._logger.debug("  - %s", lib_name)
                for source in sources:
                    self._logger.debug("    - %s", str(source))

                fd.write("library %s\n" % lib_name)
                for source in sources:
                    fd.write("  - %s\n" % source)
                f_args.append((lib_name,
                               self._libraries[lib_name],
                               'buildSources',
                               sources))

            if not f_args:
                break
            fd.write("Pool has %d workers\n" % min(threads, len(f_args)))
            fd.close()
            pool = ThreadPool(min(threads, len(f_args)))
            pool_results = pool.map_async(runAsync, f_args)
            pool_results.wait()
            pool_results.ready()
            pool.close()
            pool.join()

            for worker in pool._pool:
                assert not worker.is_alive()

            for pool_result in pool_results.get():
                for lib_name, source, errors, warnings in pool_result:
                    if errors:
                        if (lib_name, source) not in sources_with_errors:
                            sources_with_errors.append((lib_name, source))
                    if warnings:
                        if (lib_name, source) not in sources_with_warnings:
                            sources_with_warnings.append((lib_name, source))
                    for msg in errors + warnings:
                        print msg

        print "Sources with errors: %d, sources with warnings: %d" % (len(sources_with_errors), len(sources_with_warnings))
        if self._sources_with_errors:
            diff = list(set(self._sources_with_errors) - set(sources_with_errors))
            if diff:
                self._logger.debug("Sources that previously had errors:")
            for lib, src in diff:
                self._logger.debug("(%s) %s", lib, src)

        self._sources_with_errors = sources_with_errors
        self._sources_with_warnings = sources_with_warnings

def runAsync(args):
    lib_name = args[0]
    lib_obj = args[1]
    meth = args[2]
    f_args = args[3:]
    r = []
    for _r in getattr(lib_obj, meth)(*f_args):
        r.append([lib_name] + _r)

    return r
