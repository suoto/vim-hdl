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
"hdl-check-o-matic project bulider class"

import logging
import os
from library import Library
from multiprocessing.pool import ThreadPool

# pylint: disable=star-args

class ProjectBuilder(object):
    "hdl-check-o-matic project bulider class"
    MAX_ITERATIONS_UNTIL_STABLE = 20
    MAX_BUILD_STEPS = 10
    BUILD_WORKERS = 5

    def __init__(self, builder):
        self.builder = builder
        self.libraries = {}
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
    # pylint: disable=invalid-name
    def _memoid(meth):
        "Store method result in cache to speed thins up"
        def _memoid_w(self, *args, **kwargs):
            "Memorize a result"
            k = str((meth, args, kwargs))
            if not hasattr(self, '_cache'):
                self._cache = {}
            if k not in self._cache.keys():
                self._cache[k] = meth(self, *args, **kwargs)
            return self._cache[k]
        return _memoid_w

    def addLibrary(self, library_name, sources):
        "Adds a library with the given sources"
        self.libraries[library_name] = \
                Library(builder=self.builder,
                        sources=sources,
                        name=library_name)

    def hasLibrary(self, library_name):
        "Returns True is library_name has been added"
        return library_name.lower() in self.libraries.keys()

    def addLibrarySources(self, library_name, sources):
        "Adds sources to library_name"
        self.libraries[library_name].addSources(sources)

    def addBuildFlags(self, library, flags):
        "Adds build flags to the given library"
        self.libraries[library].addBuildFlags(flags)

    @_memoid
    def _getReverseDependencyMap(self):
        """Returns a dict that relates which source files depend on a
        given library/unit"""
        result = {}
        for lib in self.libraries.values():
            for src_file, src_deps in lib.getDependencies():
                for src_dep in src_deps:
                    dep_lib, dep_pkgs = src_dep
                    for dep_pkg in dep_pkgs:
                        dep_key = "%s.%s" % (dep_lib, dep_pkg)
                        if dep_key not in result.keys():
                            result[dep_key] = []
                        result[dep_key].append(src_file.filename)
        return result

    @_memoid
    def _getDependencyMap(self):
        """Returns a dict which library/units a given source file
        depens on"""
        result = {}
        for lib_name, lib in self.libraries.items():
            this_lib_map = {}
            for src_file, src_deps in lib.getDependencies():
                if src_file not in this_lib_map.keys():
                    this_lib_map[src_file] = []
                for dep_lib, dep_pkgs in src_deps:
                    for dep_pkg in dep_pkgs:
                        this_lib_map[src_file].append((dep_lib, dep_pkg))

            result[lib_name] = this_lib_map
        return result

    def _getBuildSteps(self):
        """Yields a dict that has all the library/sources that can be
        built on a given step"""
        self._getDependencyMap()

        this_build = []
        units_built = []

        for step in range(self.MAX_BUILD_STEPS):
            units_built += list(set(this_build) - set(units_built))

            this_build = []
            this_step = {}
            for lib_name, lib_deps in self._getDependencyMap().iteritems():
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
        """Searches for files that weren't build given the units_built
        and logs their dependencies"""
        this_step = {}
        for lib_name, lib_deps in self._getDependencyMap().iteritems():
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
                                "Missing dependencies for '%s': %s",
                                src, ", ".join(missing_deps))

                        if lib_name not in this_step.keys():
                            this_step[lib_name] = []
                        this_step[lib_name].append(src)

    def buildByDependency(self):
        "Build the project by checking source file dependencies"
        for lib in self.libraries.itervalues():
            lib.createOrMapLibrary()

        step_cnt = 0
        for step in self._getBuildSteps():
            step_cnt += 1
            self._logger.debug("Step %d", step_cnt)

            for lib_name, sources in step.iteritems():
                self._logger.debug("  - %s", lib_name)
                for source in sources:
                    self._logger.debug("    - %s", str(source))

                for source, errors, warnings in \
                        self.libraries[lib_name].buildSources(sources):
                    for msg in errors + warnings:
                        print msg

    def buildByDependencyWithThreads(self, threads=None):
        """Same as buildByDependency, only that each library of each
        step is built in parallel"""
        threads = threads or self.BUILD_WORKERS
        for lib in self.libraries.itervalues():
            lib.createOrMapLibrary()

        pool = ThreadPool()

        sources_with_errors = []
        sources_with_warnings = []
        sources_built_ok = []

        step_cnt = 0
        for step in self._getBuildSteps():
            step_cnt += 1
            self._logger.debug("Step %d", step_cnt)

            f_args = []

            fd = open('step_%d.log' % step_cnt, 'w')
            for lib_name, sources in step.iteritems():
                self._logger.debug("  - %s", lib_name)
                for source in sources:
                    self._logger.debug("    - %s", str(source))

                fd.write("library %s\n" % lib_name)
                for source in sources:
                    fd.write("  - %s\n" % source)
                f_args.append((lib_name,
                               self.libraries[lib_name],
                               'buildSources',
                               sources))

            if not f_args:
                break
            fd.write("Pool has %d workers\n" % min(threads, len(f_args)))
            fd.close()
            pool_results = pool.imap(threadPoolRunnerAdapter, f_args)

            for pool_result in pool_results:
                for lib_name, source, errors, warnings in pool_result:
                    if errors:
                        if (lib_name, source) not in sources_with_errors:
                            sources_with_errors.append((lib_name, source))
                    else:
                        if warnings:
                            if (lib_name, source) not in sources_with_warnings:
                                sources_with_warnings.append((lib_name, source))
                        elif (lib_name, source) not in sources_built_ok:
                            sources_built_ok.append((lib_name, source))
                    for msg in errors + warnings:
                        print msg
        pool.close()
        pool.join()
        print "Sources with errors: %d" % len(sources_with_errors)
        print "Sources with warnings: %d" % len(sources_with_warnings)
        print "Sources built OK: %d" % len(sources_built_ok)

        if self._sources_with_errors:
            diff = list(set(self._sources_with_errors) - set(sources_with_errors))
            if diff:
                self._logger.info("Sources that previously had errors:")
            for lib, src in diff:
                self._logger.info("(%s) %s", lib, src)

            diff = list(set(sources_with_errors) - set(self._sources_with_errors))
            if diff:
                self._logger.info("Sources that previously had NO errors:")
            for lib, src in diff:
                self._logger.info("(%s) %s", lib, src)

        self._sources_with_errors = sources_with_errors
        self._sources_with_warnings = sources_with_warnings

    def buildByPath(self, target):
        "Finds the library of a given path and builds it"
        if not os.path.exists(target):
            raise OSError("Path %s doesn't exists" % target)
        for lib in self.libraries.values():
            if lib.hasSource(target):
                print "Source %s is at library %s" % (target, lib.name)
                errors, warnings = lib.buildByPath(target, forced=True)
                for msg in errors + warnings:
                    print msg
                return
        raise RuntimeError("Source %s not found" % target)

def threadPoolRunnerAdapter(args):
    """Run a method from some import object via ThreadPool.
    This is ugly and will be replaced"""
    lib_name = args[0]
    lib_obj = args[1]
    meth = args[2]
    f_args = args[3:]
    result = []
    for _result in getattr(lib_obj, meth)(*f_args):
        result.append([lib_name] + _result)

    return result
