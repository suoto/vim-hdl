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
try:
    import cPickle as pickle
except ImportError:
    import pickle

from vimhdl.compilers import *               # pylint: disable=wildcard-import
from vimhdl.config_parser import readConfigFile
from vimhdl.source_file import VhdlSourceFile
import vimhdl.exceptions

_logger = logging.getLogger('build messages')

class ProjectBuilder(object):
    "vim-hdl project builder class"
    MAX_BUILD_STEPS = 20

    def __init__(self, project_file):
        self.builder = None
        self.sources = {}
        self._logger = logging.getLogger(__name__)

        self._project_file = {'filename'  : project_file,
                              'timestamp' : 0,
                              'valid'     : False}
        self.halt = False

        self._build_flags = {'batch'  : set(),
                             'single' : set(),
                             'global' : set()}

        self._units_built = []

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

    def _postUnpicklingSanityCheck(self):
        "Sanity checks to ensure the state after unpickling is still valid"
        self.builder.checkEnvironment()

    def readConfigFile(self):
        "Reads the configuration given by self._project_file['filename']"
        cache_fname = os.path.join(os.path.dirname(self._project_file['filename']), \
            '.' + os.path.basename(self._project_file['filename']))

        if os.path.exists(cache_fname):
            try:
                obj = pickle.load(open(cache_fname, 'r'))
                self.__dict__.update(obj.__dict__)
                # Environment may have change since we last saved the file,
                # we must recheck
                try:
                    self._postUnpicklingSanityCheck()
                except vimhdl.exceptions.VimHdlBaseException:
                    self._logger.exception("Sanity check error")
                    self._project_file['valid'] = False
            except (EOFError, IOError):
                self._logger.warning("Unable to unpickle cached filename")

        #  If the library file hasn't changed, we're up to date an return
        if os.path.getmtime(self._project_file['filename']) <= self._project_file['timestamp']:
            return

        self._logger.info("Updating config file")

        self._project_file['timestamp'] = os.path.getmtime(self._project_file['filename'])

        target_dir, builder_name, builder_flags, source_list = \
                readConfigFile(self._project_file['filename'])

        self._logger.info("Builder info:")
        self._logger.info(" - Target dir:    %s", target_dir)
        self._logger.info(" - Builder name:  %s", builder_name)
        self._logger.info(" - Builder flags (global): %s", \
                builder_flags['global'])
        self._logger.info(" - Builder flags (batch): %s", \
                builder_flags['batch'])
        self._logger.info(" - Builder flags (single): %s", \
                builder_flags['single'])
        #  self._logger.info(" - Sources: %s",
        #          "\n".join([str(x) for x in source_list]))

        self._build_flags = builder_flags.copy()

        # Check if the builder selected is implemented and create the
        # builder attribute
        if builder_name == 'msim':
            self.builder = MSim(target_dir)
        elif builder_name == 'xvhdl':
            self.builder = XVHDL(target_dir)
        else:
            raise RuntimeError("Unknown builder '%s'" % builder_name)

        # Iterate over the sections to get sources and build flags.
        # Take care to don't recreate a library
        for source, library, flags in source_list:
            if os.path.abspath(source) in self.sources.keys():
                _source = self.sources[os.path.abspath(source)]
            else:
                _source = VhdlSourceFile(source, library)
            _source.flags = self._build_flags['global'].copy()
            if flags:
                _source.flags.update(flags)

            self.sources[_source.abspath] = _source

        self._project_file['valid'] = True

    def saveCache(self):
        "Dumps project object to a file to recover its state later"
        cache_fname = os.path.join(os.path.dirname(self._project_file['filename']), \
            '.' + os.path.basename(self._project_file['filename']))
        try:
            pickle.dump(self, open(cache_fname, 'w'))
        except pickle.PickleError:
            self._logger.exception("Error saving file!")
            os.remove(cache_fname)

    def cleanCache(self):
        "Remove the cached project data and clean all libraries as well"
        cache_fname = os.path.join(os.path.dirname(self._project_file['filename']), \
            '.' + os.path.basename(self._project_file['filename']))

        try:
            os.remove(cache_fname)
        except OSError:
            self._logger.debug("Cache filename '%s' not found", cache_fname)
        self._project_file['timestamp'] = 0

    @staticmethod
    def clean(project_file):
        "Clean up generated files for a clean build"
        _logger = logging.getLogger(__name__) # pylint: disable=redefined-outer-name
        cache_fname = os.path.join(os.path.dirname(project_file), \
            '.' + os.path.basename(project_file))

        try:
            os.remove(cache_fname)
        except OSError:
            _logger.debug("Cache filename '%s' not found", cache_fname)

        #  parser = ExtendedConfigParser()
        #  parser.read(project_file)

        #  target_dir = parser.get('global', 'target_dir')

        #  assert not os.system("rm -rf " + target_dir)

    def _findSourceByDesignUnit(self, design_unit):
        "Finds the source files that have 'design_unit' defined"
        sources = []
        for source in self.sources.values():
            design_units = set(["%s.%s" % (source.library, x['name']) \
                    for x in source.getDesignUnits()])
            if design_unit in design_units:
                sources += [source]
        assert sources, "Design unit %s not found" % design_unit
        return sources

    def _translateSourceDependencies(self, source):
        """Translate raw dependency list parsed from a given source to the
        project name space"""
        filtered_dependencies = []
        for dependency in source.getDependencies():
            if dependency['library'] in self.builder.builtin_libraries:
                continue
            if dependency['unit'] == 'all':
                continue
            if dependency['library'] == source.library and \
                    dependency['unit'] in \
                        [x['name'] for x in source.getDesignUnits()]:
                continue
            filtered_dependencies += [dependency]
        return filtered_dependencies

    def _getBuildSteps(self):
        "Yields source objects that can be built given the units already built"
        sources_built = []
        for step in range(self.MAX_BUILD_STEPS):
            if self.halt:
                raise StopIteration()
            empty_step = True
            for source in self.sources.values():
                design_units = set(["%s.%s" % (source.library, x['name']) \
                        for x in source.getDesignUnits()])
                dependencies = set(["%s.%s" % (x['library'], x['unit']) \
                        for x in self._translateSourceDependencies(source)])

                missing_dependencies = dependencies - set(self._units_built)

                # If there are missing dependencies skip this file for now
                if missing_dependencies:
                    self._logger.debug("Skipping %s for now because it has "
                                       "missing dependencies: %s", source,
                                       list(missing_dependencies))
                    continue

                # If we have already built this source, skip it also
                if source.abspath in sources_built:
                    continue

                self._logger.debug(
                    "All dependencies for %s are met: %s", str(source),
                    ", ".join(["'%s'" % str(x) for x in dependencies]))

                self._units_built += list(design_units)
                sources_built += [source.abspath]
                empty_step = False
                yield source

            if empty_step:
                sources_not_built = False

                for missing_path in \
                        list(set(self.sources.keys()) - set(sources_built)):
                    source = self.sources[missing_path]
                    dependencies = set(["%s.%s" % (x['library'], x['unit']) \
                            for x in self._translateSourceDependencies(source)])
                    missing_dependencies = dependencies - set(self._units_built)
                    if missing_dependencies:
                        sources_not_built = True
                        self._logger.warning(
                            "Couldn't build source '%s'. Missing dependencies: %s",
                            str(source),
                            ", ".join([str(x) for x in missing_dependencies]))
                    else:
                        self._logger.warning(
                            "Source %s wasn't built but has no missing "
                            "dependencies", str(source))
                        yield source
                if sources_not_built:
                    self._logger.warning("Some sources were not built")

                self._logger.info("Breaking at step %d. Units built: %s",
                                  step, ", ".join(sorted(self._units_built)))

                raise StopIteration()

    def getCompilationOrder(self):
        "Returns the build order osed by the buildByDependency method"
        self._units_built = []
        return self._getBuildSteps()

    def _sortBuildMessages(self, records):
        "Sorts a given set of build records"
        return sorted(records, key=lambda x: \
                (x['error_type'], x['line_number'], x['error_number']))

    def buildByDependency(self):
        "Build the project by checking source file dependencies"
        if not self._project_file['valid']:
            self._logger.warning("Project file is invalid, not building")
        built = 0
        errors = 0
        warnings = 0
        self._units_built = []
        for source in self._getBuildSteps():
            records, _ = self.builder.build(source, \
                    flags=self._build_flags['batch'])
            design_units = set(["%s.%s" % (source.library, x['name']) \
                    for x in source.getDesignUnits()])
            self._units_built += list(design_units)
            for record in self._sortBuildMessages(records):
                if record['error_type'] == 'E':
                    _logger.warning(str(record))
                    errors += 1
                elif record['error_type'] == 'W':
                    _logger.debug(str(record))
                    warnings += 1
                else:
                    _logger.fatal(str(record))
                    assert 0
            built += 1
        self._logger.info("Done. Built %d sources, %d errors and %d warnings", \
                built, errors, warnings)

    def buildByPath(self, path, batch_mode=False):
        """Builds a given source file handling rebuild of units reported by the
        compiler"""
        if not self._project_file['valid']:
            self._logger.warning("Project file is invalid, not building")
            return []

        if os.path.abspath(path) not in self.sources.keys():
            return [{
                'checker'        : 'msim',
                'line_number'    : None,
                'column'         : None,
                'filename'       : path,
                'error_number'   : None,
                'error_type'     : 'W',
                'error_message'  : "Source '%s' not found on the configuration"
                                   " file" % path,
            }]

        flags = self._build_flags['batch'] if batch_mode else \
                self._build_flags['single']

        records, rebuilds = self.builder.build(
            self.sources[os.path.abspath(path)], forced=True,
            flags=flags)

        if rebuilds:
            source = self.sources[os.path.abspath(path)]
            rebuild_units = ["%s.%s" % (x[0], x[1]) for x in rebuilds]

            self._logger.info("Building '%s' triggers rebuild of units: %s",
                              source, ", ".join(rebuild_units))
            for rebuild_unit in rebuild_units:
                for rebuild_source in self._findSourceByDesignUnit(rebuild_unit):
                    self.buildByPath(rebuild_source.abspath, batch_mode=True)
            return self.buildByPath(path)

        return self._sortBuildMessages(records)

