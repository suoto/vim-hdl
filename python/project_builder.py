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
"vim-hdl project bulider class"

import logging
import os
import re
import atexit
from multiprocessing.pool import ThreadPool
#  from threading import Thread
#  import threading
try:
    import cPickle as pickle
except ImportError:
    import pickle

from library import Library
from utils import memoid
from compilers.msim import MSim
from config import Config
from config_parser import ExtendedConfigParser

try:
    import vim
    HAS_VIM = True
except ImportError:
    HAS_VIM = False
#  from file_lock import FileLock


# pylint: disable=star-args

def saveCache(obj, fname):
    pickle.dump(obj, open(fname, 'w'))

class ProjectBuilder(object):
    "vim-hdl project bulider class"
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
        self._build_cnt = 0

        self.readConfFile()

    def cleanCache(self):
        "Remove the cached project data and clean all libraries as well"
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

        parser = ExtendedConfigParser()
        parser.read(library_file)

        target_dir = parser.get('global', 'target_dir')

        assert not os.system("rm -rf " + target_dir)

    def readConfFile(self):
        cache_fname = os.path.join(os.path.dirname(self._library_file), \
            '.' + os.path.basename(self._library_file))

        if os.path.exists(cache_fname):
            try:
                obj = pickle.load(open(cache_fname, 'r'))
                self.__dict__.update(obj.__dict__)
            except EOFError:
                self._logger.warning("Unable to unpickle cached filename")

        atexit.register(saveCache, self, cache_fname)

        # If the library file hasn't changed, we're up to date an return
        if os.path.getmtime(self._library_file) <= self._conf_file_timestamp:
            return

        self._conf_file_timestamp = os.path.getmtime(self._library_file)

        defaults = {'build_flags' : '',
                    'global_build_flags' : '',
                    'batch_build_flags' : '',
                    'single_build_flags' : ''}

        parser = ExtendedConfigParser(defaults=defaults)
        parser.read(self._library_file)

        # Get the global build definitions
        global_build_flags = parser.getlist('global', 'global_build_flags')
        self.batch_build_flags = parser.getlist('global', 'batch_build_flags')
        self.single_build_flags = parser.getlist('global', 'single_build_flags')

        builder = parser.get('global', 'builder')
        target_dir = parser.get('global', 'target_dir')
        self._logger.info("Builder selected: %s at %s", builder, target_dir)

        # Check if the builder selected is implemented and create the
        # builder attribute
        if builder == 'msim':
            self.builder = MSim(target_dir)
        else:
            raise RuntimeError("Unknown builder '%s'" % builder)

        # Iterate over the sections to get sources and build flags.
        # Take care to don't recreate a library
        for section in parser.sections():
            if section == 'global':
                continue
            sources = parser.getlist(section, 'sources')
            flags = parser.getlist(section, 'build_flags')

            if section not in self.libraries.keys():
                self._logger.info("Found library '%s'", section)
                self.addLibrary(section, sources, target_dir)
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
        # Remove the _logger attribute because we can't pickle file or
        # stream objects. In its place, save the logger name
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        # Get a logger with the name given in state['_logger'] (see
        # __getstate__) and update our dictionary with the pickled info
        self._logger = logging.getLogger(state['_logger'])
        self._logger.setLevel(logging.INFO)
        del state['_logger']
        self.__dict__.update(state)

    def addLibrary(self, library_name, sources, target_dir):
        "Adds a library with the given sources"
        self.libraries[library_name] = \
                Library(builder=self.builder,
                        sources=sources,
                        name=library_name,
                        target_dir=target_dir)

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
                        dep_key = (dep_lib, dep_pkg)
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

        #  this_step = {}
        #  for lib_name, src in self._getSourcesWithMissingDependencies(units_built):
        #      if lib_name not in this_step:
        #          this_step[lib_name] = []
        #      if src not in this_step[lib_name]:
        #          this_step[lib_name].append(src)

        #  if this_step:
        #      self._logger.debug("Yielding remaining files")
        #      yield this_step

    @memoid
    def _getSourcesWithMissingDependencies(self, units_built):
        """Searches for files that weren't build given the units_built
        and returns their dependencies"""
        result = []
        for lib_name, lib_deps in self._getDependencyMap().iteritems():
            for src, src_deps in lib_deps.iteritems():
                for design_unit in src.getDesignUnits():
                    if not design_unit:
                        result.append((lib_name, src))
                        #  yield lib_name, src
                    if (lib_name, design_unit) not in units_built:
                        result.append((lib_name, src))
                        #  yield lib_name, src
                        missing_deps = []
                        for dep_lib_name, unit_name in set(src_deps) - set(units_built):
                            if "%s.%s" % (dep_lib_name, unit_name) not in missing_deps:
                                missing_deps.append(
                                    "%s.%s" % (dep_lib_name, unit_name))
                        if missing_deps:
                            self._logger.warning(
                                "Missing dependencies for '%s': %s",
                                src, ", ".join(missing_deps))
        return result


    def buildByDependency(self, silent=False):
        "Build the project by checking source file dependencies"
        self.updateVimTagsConfig()
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

                for source, errors, warnings, rebuilds in \
                        self.libraries[lib_name].buildSources(sources, \
                                flags=self.batch_build_flags):
                    for rebuild in rebuilds:
                        self._logger.info("Rebuilding %s before %s", \
                                str(rebuild), \
                                [str(x) for x in sources])
                        self.buildByDesignUnit(rebuild)

                    if not silent:
                        for msg in errors + warnings:
                            print msg

        self._build_cnt += 1

    def _getLockFilename(self):
        temp_path = os.path.join(os.path.sep, 'tmp', 'vim-hdl')
        if not os.path.exists(temp_path):
            os.mkdir(temp_path)

        lockfile = os.path.join(os.path.sep, 'tmp', temp_path,
            re.sub(os.path.sep, '_', os.path.abspath(self._library_file)))

        return lockfile

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
                for lib_name, source, errors, warnings, rebuilds, in pool_result:
                    for msg in errors + warnings:
                        print msg
        pool.close()
        pool.join()

    @memoid
    def _findLibraryByPath(self, path):
        if not os.path.exists(path):
            raise OSError("Path %s doesn't exists" % path)
        for lib in self.libraries.values():
            if lib.hasSource(path):
                return lib
        raise RuntimeError("Source %s not found" % path)

    @memoid
    def getDesignUnitsByPath(self, path):
        lib = self._findLibraryByPath(path)
        for source in lib.sources:
            if source.abspath() == os.path.abspath(path):
                return source.getDesignUnits()


    def buildByDesignUnit(self, unit):
        lib_name = unit[0].lower()
        if lib_name not in self.libraries.keys():
            raise RuntimeError("Design unit '%s' not found" % unit)
        lib = self.libraries[lib_name]
        source = lib.getSourceByDesignUnit(unit[1])
        self._logger.info("Rebuilding %s.%s", lib, source)
        for _, errors, warnings, rebuilds in lib.buildSources([source], forced=True, \
                flags=self.single_build_flags):
            if rebuilds:
                for rebuild in rebuilds:
                    self._logger.info("Rebuilding %s before %s", \
                            str(rebuild), source)
                    self.buildByDesignUnit(rebuild)
                    self.buildByDesignUnit(unit)
            else:
                for msg in errors + warnings:
                    print msg

    def buildByPath(self, path):
        """Finds the library of a given path and builds it. Use the reverse
        dependency map to reset the compile time of the sources that depend on
        'path' to build later"""
        self._logger.info("Build count: %d", self._build_cnt)
        if self._build_cnt == 0:
            self._logger.info("Running project build before building '%s'", path)
            self.buildByDependency(silent=True)
        self._logger.info("==== Building '%s' ====", path)
        # Find out which library has this path
        lib = self._findLibraryByPath(path)
        errors, warnings, rebuilds = lib.buildByPath(path, forced=True, \
                flags=self.single_build_flags)
        for msg in errors + warnings:
            print msg

        # Find out which design units are found at path to use as key to the
        # reverse dependency map
        units = self.getDesignUnitsByPath(path)
        reverse_dependency_map = self._getReverseDependencyMap()
        for unit in units:
            rev_dep_key = lib.name, unit
            if rev_dep_key in reverse_dependency_map.keys():
                self._logger.info("Building '%s' triggers rebuild of %s",
                        path, ", ".join(reverse_dependency_map[rev_dep_key]))
                for source in reverse_dependency_map[rev_dep_key]:
                    dep_lib = self._findLibraryByPath(source)
                    dep_lib.clearBuildCacheByPath(source)
            else:
                self._logger.info("'%s.%s' has no reverse dependency", lib.name, unit)
        if rebuilds:
            self._logger.warning("Rebuild units: %s", str(rebuilds))
            self.buildByDependency(Config.show_only_current_file)
        self.updateVimTagsConfig()

    def updateVimTagsConfig(self):
        if HAS_VIM:
            tags = [x.tag_file for x in self.libraries.values()]
            self._logger.info('Setting up tags to %s', ', '.join(tags))
            vim.command('set tags=%s' % ','.join(tags))
        else:
            self._logger.info("Vim mode not enable, bypassing")

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
