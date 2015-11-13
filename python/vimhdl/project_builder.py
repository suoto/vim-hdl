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
from threading import Thread
try:
    import cPickle as pickle
except ImportError:
    import pickle

#  from vimhdl.library import Library
from vimhdl.compilers.msim import MSim
from vimhdl.config_parser import ExtendedConfigParser
from vimhdl.source_file import VhdlSourceFile

# pylint: disable=star-args, bad-continuation

def saveCache(obj, fname):
    pickle.dump(obj, open(fname, 'w'))

_logger = logging.getLogger('build messages')

class ProjectBuilder(object):
    "vim-hdl project builder class"
    MAX_BUILD_STEPS = 20

    def __init__(self, project_file):
        self.builder = None
        self.sources = {}
        self._logger = logging.getLogger(__name__)
        self._conf_file_timestamp = 0
        self._project_file = project_file

        self._build_flags = {
                'batch' : [],
                'single' : [],
                'global' : []
                }

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
        self._build_flags = {
                'batch' : parser.getlist('global', 'batch_build_flags'),
                'single' : parser.getlist('global', 'single_build_flags'),
                'global' : parser.getlist('global', 'global_build_flags'),
                }

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

            for source in sources:
                _source = VhdlSourceFile(source, section)
                if flags:
                    _source.flags = set(flags + self._build_flags['global'])
                else:
                    _source.flags = set(self._build_flags['global'])
                self.sources[_source.abspath()] = _source

    def _filterSourceDependencies(self, source):
        filtered_dependencies = []
        for dependency in source.getDependencies():
            if dependency['library'] in self.builder.builtin_libraries:
                continue
            if dependency['unit'] == 'all':
                continue
            if dependency['library'] == source.library and \
                    dependency['unit'] in source.getDesignUnits():
                continue
            filtered_dependencies += [dependency]
        return filtered_dependencies

    def getBuildSteps(self):
        """Yields a dict that has all the library/sources that can be
        built on a given step"""
        units_built = []
        sources_built = []
        for step in range(self.MAX_BUILD_STEPS):
            self._logger.debug("Step %d, units built: %s", step, str(units_built))
            empty_step = True
            for source in self.sources.values():
                design_units = set(["%s.%s" % (source.library, x['name']) \
                        for x in source.getDesignUnits()])
                if design_units.issubset(units_built):
                    continue

                dependencies = set(["{library}.{unit}".format(**x) \
                        for x in self._filterSourceDependencies(source)])

                self._logger.debug("Source '%s' depends on %s", str(source),
                        ", ".join(["'%s'" % str(x) for x in dependencies]))

                if dependencies.issubset(set(units_built)):
                    if source.abspath() not in sources_built:
                        sources_built += [source.abspath()]
                    empty_step = False
                    units_built += list(design_units)
                    yield source
                else:
                    self._logger.debug("Dependencies needed to build %s: %s",
                            str(source),
                            ", ".join([str(x) for x in dependencies - set(units_built)]))
            if empty_step:
                for source in self.sources.values():
                    if source.abspath() not in sources_built:
                        dependencies = set(["{library}.{unit}".format(**x) \
                                for x in self._filterSourceDependencies(source)])
                        self._logger.warning("Couldn't build source '%s' due to "
                            "missing dependencies %s",
                            str(source),
                            ", ".join([str(x) for x in dependencies - set(units_built)]))



                raise StopIteration()
        assert 0

    def cleanCache(self):
        "Remove the cached project data and clean all libraries as well"
        cache_fname = os.path.join(os.path.dirname(self._project_file), \
            '.' + os.path.basename(self._project_file))

        try:
            os.remove(cache_fname)
        except OSError:
            self._logger.debug("Cache filename '%s' not found", cache_fname)
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

    def buildByDependency(self):
        "Build the project by checking source file dependencies"
        for source in self.getBuildSteps():
            records, _ = self.builder.build(source,
                    flags=self._build_flags['batch'])
            for record in records:
                if record['error_type'] == 'W':
                    _logger.warn(str(record))
                elif record['error_type'] == 'E':
                    _logger.error(str(record))
                else:
                    _logger.fatal(str(record))
                    assert 0

    def _sortBuildMessages(self, records):
        return sorted(records, key=lambda x: \
                (x['error_type'], x['line_number'], x['error_number']))

    def buildByPath(self, path):
        """Finds the library of a given path and builds it. Use the reverse
        dependency map to reset the compile time of the sources that depend on
        'path' to build later"""

        records, _ = self.builder.build(
                self.sources[os.path.abspath(path)], forced=True,
                flags=self._build_flags['single'])

        return self._sortBuildMessages(records)

