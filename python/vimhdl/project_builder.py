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
"vim-hdl project builder class"

import logging
import os
import atexit
from threading import Thread
try:
    import cPickle as pickle
except ImportError:
    import pickle

from vimhdl.library import Library
from vimhdl.compilers.msim import MSim
from vimhdl.config import Config
from vimhdl.config_parser import ExtendedConfigParser

def _error(s):
    _logger.debug("[E] " + s)
    if Config.is_toolchain:
        print s

def _warning(s):
    _logger.debug("[W] " + s)
    if Config.is_toolchain:
        print s


# pylint: disable=star-args, bad-continuation

def saveCache(obj, fname):
    pickle.dump(obj, open(fname, 'w'))

_logger = logging.getLogger('build messages')

class ProjectBuilder(object):
    "vim-hdl project builder class"
    MAX_BUILD_STEPS = 20

    def __init__(self, project_file):
        self.builder = None
        self.libraries = {}
        self._logger = logging.getLogger(__name__)
        self._conf_file_timestamp = 0
        self._project_file = project_file

        self.batch_build_flags = []
        self.single_build_flags = []
        self._build_cnt = 0

        self._readConfFile()

    def __getstate__(self):
        "Pickle dump implementation"
        # Remove the _logger attribute because we can't pickle file or
        # stream objects. In its place, save the logger name
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        "Pickle load implementation"
        # Get a logger with the name given in state['_logger'] (see
        # __getstate__) and update our dictionary with the pickled info
        self._logger = logging.getLogger(state['_logger'])
        self._logger.setLevel(logging.INFO)
        del state['_logger']
        self.__dict__.update(state)

    def saveCache(self):
        cache_fname = os.path.join(os.path.dirname(self._project_file), \
            '.' + os.path.basename(self._project_file))
        pickle.dump(self, open(cache_fname, 'w'))

    def _readConfFile(self):
        "Reads the configuration given by self._project_file"
        cache_fname = os.path.join(os.path.dirname(self._project_file), \
            '.' + os.path.basename(self._project_file))

        if os.path.exists(cache_fname):
            try:
                obj = pickle.load(open(cache_fname, 'r'))
                self.__dict__.update(obj.__dict__)
            except (EOFError, IOError):
                self._logger.warning("Unable to unpickle cached filename")

        atexit.register(saveCache, self, cache_fname)

        #  If the library file hasn't changed, we're up to date an return
        if os.path.getmtime(self._project_file) <= self._conf_file_timestamp:
            return

        self._logger.info("Updating config file")

        self._conf_file_timestamp = os.path.getmtime(self._project_file)

        defaults = {'build_flags' : '',
                    'global_build_flags' : '',
                    'batch_build_flags' : '',
                    'single_build_flags' : ''}

        parser = ExtendedConfigParser(defaults=defaults)
        parser.read(self._project_file)

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

    def _getReverseDependencyMap(self):
        """Returns a dict that relates which source files depend on a
        given library/unit"""
        result = {}
        for lib in self.libraries.values():
            for src_file, src_deps in lib.getDependencies():
                for dep_lib, dep_pkg in src_deps:
                    dep_key = (dep_lib, dep_pkg)
                    if dep_key not in result.keys():
                        result[dep_key] = []
                    result[dep_key].append(src_file.filename)
        return result

    def _getDependencyMap(self):
        """Returns a dict which library/units a given source file
        depens on"""
        result = {}
        for lib_name, lib in self.libraries.items():
            this_lib_map = {}
            for src_file, src_deps in lib.getDependencies():
                if src_file not in this_lib_map.keys():
                    this_lib_map[src_file] = []
                for dep_lib, dep_unit in src_deps:
                    if (dep_lib, dep_unit) not in this_lib_map[src_file]:
                        this_lib_map[src_file].append((dep_lib, dep_unit))

            result[lib_name] = this_lib_map
        return result

    def getBuildSteps(self):
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

            yield this_step

            if step == self.MAX_BUILD_STEPS or not this_build:
                self._logger.error("Max build steps of %d reached, stopping",
                                   self.MAX_BUILD_STEPS)

                for lib_name, src, missing_deps, in \
                        self._getSourcesWithMissingDeps(units_built):
                    assert 0
                    self._logger.warning("[%s] %s has missing dependencies: %s",
                            lib_name, src, str(missing_deps))
                break

    def _getSourcesWithMissingDeps(self, units_built):
        """Searches for files that weren't build given the units_built
        and returns their dependencies"""
        for lib_name, lib_deps in self._getDependencyMap().iteritems():
            for src, src_deps in lib_deps.iteritems():
                for design_unit in src.getDesignUnits():
                    if (lib_name, design_unit) not in units_built:
                        missing_deps = []
                        for dep_lib_name, unit_name in \
                                set(src_deps) - set(units_built):
                            if "%s.%s" % (dep_lib_name, unit_name) not in \
                                    missing_deps:
                                missing_deps.append(
                                    "%s.%s" % (dep_lib_name, unit_name))
                        yield lib_name, src, missing_deps

    def getLibraryAndSourceByPath(self, path):
        """Gets the library containing the path. Raises RuntimeError
        if the source is not found anywhere"""
        if not os.path.exists(path):
            raise OSError("Path %s doesn't exists" % path)
        for lib in self.libraries.values():
            source = lib.hasSource(path)
            if source:
                return lib, source
        raise RuntimeError("Source %s not found" % path)

    def cleanCache(self):
        "Remove the cached project data and clean all libraries as well"
        cache_fname = os.path.join(os.path.dirname(self._project_file), \
            '.' + os.path.basename(self._project_file))

        try:
            os.remove(cache_fname)
        except OSError:
            self._logger.debug("Cache filename '%s' not found", cache_fname)
        while self.libraries:
            self.libraries.popitem()[1].deleteLibrary()
        self._conf_file_timestamp = 0

    @staticmethod
    def clean(project_file):
        "Clean up generated files for a clean build"
        _logger = logging.getLogger(__name__)
        cache_fname = os.path.join(os.path.dirname(project_file), \
            '.' + os.path.basename(project_file))

        try:
            os.remove(cache_fname)
        except OSError:
            _logger.debug("Cache filename '%s' not found", cache_fname)

        parser = ExtendedConfigParser()
        parser.read(project_file)

        target_dir = parser.get('global', 'target_dir')

        assert not os.system("rm -rf " + target_dir)

    def addLibrary(self, library_name, sources, target_dir):
        "Adds a library with the given sources"
        if library_name != 'tag_sources':
            self.libraries[library_name] = \
                    Library(builder=self.builder,
                            sources=sources,
                            name=library_name,
                            target_dir=target_dir)
        else:
            self.libraries[library_name] = \
                    Library(builder=None,
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

    def buildByDependency(self, filter=lambda x: 1):
        "Build the project by checking source file dependencies"
        for lib in self.libraries.itervalues():
            lib.createOrMapLibrary()

        step_cnt = 0
        for step in self.getBuildSteps():
            step_cnt += 1
            if not step:
                self._logger.debug("Empty step at iteration %d", step_cnt)
                break

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
                        self.buildByDesignUnit(*rebuild)

                    for error in errors:
                        if filter(error):
                            _error(error)

                    for warning in warnings:
                        if filter(warning):
                            _warning(warning)

        self._build_cnt += 1

    def buildByDesignUnit(self, lib_name, unit):
        """Builds a source file given a design unit, in the format
        """
        if lib_name not in self.libraries.keys():
            raise RuntimeError("Design unit '%s' not found" % unit)
        lib = self.libraries[lib_name]
        source = lib.getSourceByDesignUnit(unit)

        return self.buildSource(lib, source)

    def buildSource(self, library, source, *args, **kwargs):
        "Flow for building library.source"

        self._logger.debug("Build count: %d", self._build_cnt)
        if self._build_cnt == 0:
            self._logger.info("Running project build before building '%s'",
                    str(source))
            self.buildByDependency(filter=lambda x: 1)

        # Start the direct and reverse dependency mapping in a thread
        # to save time
        threads = [Thread(target=self._getDependencyMap),
                   Thread(target=self._getReverseDependencyMap)]

        [t.start() for t in threads]

        self._logger.info("Building [%s] '%s'", library.name, str(source))
        errors, warnings, rebuilds = library.buildSource(source,
                *args, **kwargs)

        # Join the dependency mapping threads before we need that
        # information
        [t.join() for t in threads]

        for dep_errors, dep_warnings, dep_rebuilds in \
                self._buildReverseDependencies(library, source):
            errors += dep_errors
            warnings += dep_warnings
            rebuilds += dep_rebuilds

        return errors, warnings, rebuilds

    def _buildReverseDependencies(self, library, source):
        """Builds sources that depends on the given library/source.
        Notes on current implementation:
        1) We won't build recursively because this can lead to to
        rebuilding the entire library, which may take much more time
        than we want to wait for a syntax check. However, building only
        first level dependencies makes second level dependencies out of
        date. This should be handled (maybe in background), or else
        things can get very messy
        2) The build order is not checked. If A triggers rebuilding B
        and C but C also depends on B (and thus should be built after
        B), there is no guarantee that B will be built before C"""

        if not (Config.show_reverse_dependencies_errors or \
                Config.show_reverse_dependencies_warnings):
            raise StopIteration()

        # Find out which design units are found on the source to use
        # as key to the reverse dependency map
        units = source.getDesignUnits()
        reverse_dependency_map = self._getReverseDependencyMap()

        # We'll insert packages at the start of the list and append
        # non packages at the end. We need to do this before actually
        # building anything to check if the amount of sources that
        # should be rebuilt doesn't exceeds the value given by
        # Config.max_reverse_dependency_sources
        build_list = []

        for unit in units:
            rev_dep_key = library.name, unit
            if rev_dep_key in reverse_dependency_map.keys():
                self._logger.info("Building '%s' triggers rebuild of %s",
                    str(source), ", ".join(reverse_dependency_map[rev_dep_key]))

                for _source in reverse_dependency_map[rev_dep_key]:
                    dep_lib, _source = self.getLibraryAndSourceByPath(_source)

                    if _source.hasPackage():
                        self._logger.debug("Inserting [%s] '%s'", dep_lib.name,
                                str(_source))
                        build_list.insert(0, (dep_lib, _source))
                    else:
                        self._logger.debug("Appending [%s] '%s'", dep_lib.name,
                                str(_source))
                        build_list.append((dep_lib, _source))

        # TODO: If we exceed the maximum number of dependencies allowed
        # to be rebuilt, we should warn the user we're not rebuilding
        # anything
        if len(build_list) > Config.max_reverse_dependency_sources:
            self._logger.warning("Number of tracked rebuilds of %d exceeds "
                    "the maximum configured of %d", len(build_list),
                    Config.max_reverse_dependency_sources)
            raise StopIteration()
        else:
            self._logger.info("Tracked %d rebuilds", len(build_list))

        for dep_lib, dep_source in build_list:
            self._logger.info("Building scheduled [%s] '%s'",
                    dep_lib.name, str(dep_source))
            errors, warnings, rebuilds = \
                dep_lib.buildSource(dep_source, forced=True, \
                flags=self.single_build_flags)

            # Append errors and/or warnings according to
            # user preferences to make sure we keep printing
            # errors before the warnings
            if not Config.show_reverse_dependencies_errors:
                errors = []
            elif not Config.show_reverse_dependencies_warnings:
                warnings = []
            yield errors, warnings, rebuilds

    def buildByPath(self, path):
        """Finds the library of a given path and builds it. Use the reverse
        dependency map to reset the compile time of the sources that depend on
        'path' to build later"""

        # Find out which library has this path
        lib, source = self.getLibraryAndSourceByPath(path)
        errors, warnings, rebuilds = self.buildSource(lib, source, \
                forced=True, flags=self.single_build_flags)

        for error in errors:
            _error(error)

        for warning in warnings:
            _warning(warning)

        if rebuilds:
            self._logger.warning("Rebuild units: %s", str(rebuilds))
            self.buildByDependency(lambda s: not Config.show_only_current_file)

    # Methods for displaying info about the project
    def printDependencyMap(self, source=None):
        "Prints the dependencies of all sources or of a single file"
        if source is None:
            for lib_name, lib_deps in self._getDependencyMap().iteritems():
                print "Library %s" % lib_name
                for src, src_deps in lib_deps.iteritems():
                    if src_deps:
                        print " - %s: %s" % \
                            (src, ", ".join(
                                ["%s.%s" % (x[0], x[1]) for x in src_deps]
                            ))
                    else:
                        print " - %s: None" % src
        else:
            _, source = self.getLibraryAndSourceByPath(source)
            print "\n".join(["%s.%s" % tuple(x) for x in source.getDependencies()])

    def printReverseDependencyMap(self, source=None):
        """Prints the reverse dependency map (i.e., 'who depends on
        me?', as opposite to the direct dependency map 'who do I depend
        on?')
        """
        if source is None:
            for (lib_name, design_unit), deps in \
                    self._getReverseDependencyMap().iteritems():
                _s =  "- %s.%s: " % (lib_name, design_unit)
                if deps:
                    _s += " ".join(deps)
                else:
                    _s += "None"
                print _s
        else:
            lib, source = self.getLibraryAndSourceByPath(source)
            rev_depmap = self._getReverseDependencyMap()
            for unit in source.getDesignUnits():
                k = lib.name, unit
                print "\n".join(rev_depmap[k])


