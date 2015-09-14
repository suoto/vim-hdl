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
import re
import ConfigParser
import atexit
from multiprocessing.pool import ThreadPool
try:
    import cPickle as pickle
except ImportError:
    import pickle

from library import Library
from utils import memoid
from compilers.msim import MSim

# pylint: disable=star-args

def saveCache(obj, fname):
    pickle.dump(obj, open(fname, 'w'))

def getList(parser, *args, **kwargs):
    entry = parser.get(*args, **kwargs)
    entry = re.sub(r"^\s*|\s*$", "", entry)
    if entry:
        return re.split(r"\s+", entry)
    else:
        return []


class ProjectBuilder(object):
    "hdl-check-o-matic project bulider class"
    MAX_BUILD_STEPS = 10
    BUILD_WORKERS = 5

    def __init__(self, library_file):
        self.builder = None
        self.libraries = {}
        self._logger = logging.getLogger(__name__)
        self._conf_file_timestamp = 0
        self._library_file = library_file

        self.batch_build_flags = []
        self.single_build_flags = []

        self.readConfFile()

        self._cache = {}

    def cleanCache(self):
        cache_fname = os.path.join(os.path.dirname(self._library_file), \
            '.' + os.path.basename(self._library_file))
        try:
            os.remove(cache_fname)
        except OSError:
            self._logger.debug("Cache filename '%s' not found", cache_fname)
        while self.libraries:
            self.libraries.popitem()[1].deleteLibrary()
        self._conf_file_timestamp = 0

    @staticmethod
    def clean(library_file):
        _logger = logging.getLogger(__name__)
        cache_fname = os.path.join(os.path.dirname(library_file), \
            '.' + os.path.basename(library_file))

        try:
            os.remove(cache_fname)
        except OSError:
            _logger.debug("Cache filename '%s' not found", cache_fname)

        parser = ConfigParser.SafeConfigParser()
        parser.read(library_file)

        target_dir = parser.get('global', 'target_dir')

        assert not os.system("rm -rf " + target_dir)

    def readConfFile(self):
        cache_fname = os.path.join(os.path.dirname(self._library_file),
                '.' + os.path.basename(self._library_file))

        if os.path.exists(cache_fname):
            try:
                obj = pickle.load(open(cache_fname, 'r'))
                self.__dict__.update(obj.__dict__)
            except EOFError:
                self._logger.warning("Unable to unpickle cached filename")

        atexit.register(saveCache, self, cache_fname)

        if os.path.getmtime(self._library_file) <= self._conf_file_timestamp:
            return

        self._conf_file_timestamp = os.path.getmtime(self._library_file)

        defaults = {'build_flags' : '',
                    'global_build_flags' : '',
                    'batch_build_flags' : '',
                    'single_build_flags' : ''}
        parser = ConfigParser.SafeConfigParser(defaults=defaults)
        parser.read(self._library_file)

        global_build_flags = getList(parser, 'global', 'global_build_flags')
        self.batch_build_flags = getList(parser, 'global', 'batch_build_flags')
        self.single_build_flags = getList(parser, 'global', 'single_build_flags')


        builder = parser.get('global', 'builder')
        target_dir = parser.get('global', 'target_dir')
        self._logger.info("Builder selected: %s at %s", builder, target_dir)

        if builder == 'msim':
            self.builder = MSim(target_dir)
        else:
            raise RuntimeError("Unknown builder '%s'" % builder)

        for section in parser.sections():
            if section == 'global':
                continue
            sources = re.sub(r"^\s*|\s*$", "", parser.get(section, 'sources'))
            sources = re.split(r"\s+", sources)
            flags = getList(parser, section, 'build_flags')

            #  print "[%s] flags: %s" % (section, str(flags))
            #  flags = getList(parser.get(section, 'build_flags')))

            if section not in self.libraries.keys():
                self._logger.info("Found library '%s'", section)
                self.addLibrary(section, sources)
            else:
                self.addLibrarySources(section, sources)

            if global_build_flags:
                self.addBuildFlags(section, global_build_flags)

            if flags:
                self.addBuildFlags(section, flags)

        for lib_name, lib in self.libraries.iteritems():
            if not lib.sources:
                self._logger.warning("Library '%s' has no sources", lib_name)

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        self._logger = logging.getLogger(state['_logger'])
        del state['_logger']
        self.__dict__.update(state)

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

    @memoid
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

    @memoid
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
                        if (dep_lib, dep_pkg) not in this_lib_map[src_file]:
                            this_lib_map[src_file].append((dep_lib, dep_pkg))

            result[lib_name] = this_lib_map
        return result

    def _getBuildSteps(self):
        """Yields a dict that has all the library/sources that can be
        built on a given step"""

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

        this_step = {}
        for lib_name, src in self._logMissingDependencies(units_built):
            if lib_name not in this_step:
                this_step[lib_name] = []
            if src not in this_step[lib_name]:
                this_step[lib_name].append(src)

        if this_step:
            self._logger.debug("Yielding remaining files")
            yield this_step

    def _logMissingDependencies(self, units_built):
        """Searches for files that weren't build given the units_built
        and logs their dependencies"""
        for lib_name, lib_deps in self._getDependencyMap().iteritems():
            for src, src_deps in lib_deps.iteritems():
                for design_unit in src.getDesignUnits():
                    if not design_unit:
                        yield lib_name, src
                    if (lib_name, design_unit) not in units_built:
                        yield lib_name, src
                        missing_deps = []
                        for dep_lib_name, unit_name in set(src_deps) - set(units_built):
                            if "%s.%s" % (dep_lib_name, unit_name) not in missing_deps:
                                missing_deps.append(
                                    "%s.%s" % (dep_lib_name, unit_name))
                        if missing_deps:
                            self._logger.warning(
                                "Missing dependencies for '%s': %s",
                                src, ", ".join(missing_deps))


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
                        self.libraries[lib_name].buildSources(sources,
                                flags=self.batch_build_flags):
                    for msg in errors + warnings:
                        print msg

    def buildByDependencyWithThreads(self, threads=None):
        """Same as buildByDependency, only that each library of each
        step is built in parallel"""
        threads = threads or self.BUILD_WORKERS

        for lib in self.libraries.itervalues():
            lib.createOrMapLibrary()

        pool = ThreadPool()

        for step in self._getBuildSteps():

            f_args = []

            for lib_name, sources in step.iteritems():
                self._logger.debug("  - %s", lib_name)
                for source in sources:
                    self._logger.debug("    - %s", str(source))

                f_args.append((lib_name,
                               self.libraries[lib_name],
                               'buildSources',
                               sources,
                               self.batch_build_flags))

            if not f_args:
                break

            pool_results = pool.imap(threadPoolRunnerAdapter, f_args)

            for pool_result in pool_results:
                for lib_name, source, errors, warnings in pool_result:
                    for msg in errors + warnings:
                        print msg
        pool.close()
        pool.join()

    def _findLibraryByPath(self, path):
        if not os.path.exists(path):
            raise OSError("Path %s doesn't exists" % path)
        for lib in self.libraries.values():
            if lib.hasSource(path):
                return lib
        raise RuntimeError("Source %s not found" % path)

    def getDesignUnitsByPath(self, path):
        lib = self._findLibraryByPath(path)
        for source in lib.sources:
            if source.abspath() == os.path.abspath(path):
                print "Design units for '%s': %s" % (path,\
                        ", ".join(source.getDesignUnits()))
                break


    def buildByPath(self, target):
        "Finds the library of a given path and builds it"
        lib = self._findLibraryByPath(target)
        errors, warnings = lib.buildByPath(target, forced=True, \
                flags=self.single_build_flags)
        for msg in errors + warnings:
            print msg

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
