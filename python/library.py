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

import logging
import os

from utils import memoid
from source_file import VhdlSourceFile

class Library(object):
    """Organizes a collection of VhdlSourceFile objects and calls the
    builder with the appropriate parameters"""

    def __init__(self, builder, sources=None, name='work'):
        self.builder = builder
        self.name = name
        self.sources = []
        if sources is not None:
            self.addSources(sources)

        self._extra_flags = []
        self._logger = logging.getLogger("Library('%s')" % self.name)

        self._build_info_cache = {}

    def __str__(self):
        return "Library(name='%s')" % self.name

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        self._logger = logging.getLogger(state['_logger'])
        del state['_logger']
        self.__dict__.update(state)

    # TODO: Check file modification time to invalidate cached info
    def _buildSource(self, source, forced=False, flags=[]):
        """Handle caching of source build information, like warnings and
        errors."""
        if source.abspath() not in self._build_info_cache.keys():
            self._build_info_cache[source.abspath()] = {
                'compile_time': 0, 'size' : 0, 'errors': (), 'warnings': ()
            }

        cached_info = self._build_info_cache[source.abspath()]

        if os.stat(source.abspath()).st_size == cached_info['size']:
            self._logger.warning("'%s' => size is the same!", str(source))
            forced = False

        if source.getmtime() > cached_info['compile_time'] or forced:

            build_flags = []
            for flag in self._extra_flags + flags:
                if flag not in build_flags:
                    build_flags.append(flag)

            errors, warnings, rebuilds = self.builder.build(
                self.name, source, build_flags)

            for i in range(len(rebuilds)):
                lib, unit = rebuilds[i]
                if lib == 'work':
                    lib = self.name
                rebuilds[i] = (lib, unit)

            cached_info['compile_time'] = source.getmtime()
            cached_info['errors'] = errors
            cached_info['warnings'] = warnings
            cached_info['rebuilds'] = rebuilds
        else:
            errors   = cached_info['errors']
            warnings = cached_info['warnings']
            rebuilds = cached_info['rebuilds']

        #  if errors or rebuilds:
        if rebuilds:
            cached_info['compile_time'] = 0

        #  TODO: msim vcom-1195 means something wasn't found. Since this
        # something could be in some file not yet compiled, we'll leave the
        # cached status clear, so we force recompile only in this case.  This
        # should be better studied because avoiding to recompile a file that
        # had errors could be harmful
        for error in errors:
            if '(vcom-11)' in error:
                self._logger.error("(%s) %s %s", self.name, str(source), error)

        return errors, warnings, rebuilds

    def addSources(self, sources):
        "Adds a source or a list of sources to this library"
        assert self.sources is not None

        filenames = [x.abspath() for x in self.sources]

        if hasattr(sources, '__iter__'):
            for source in sources:
                if os.path.abspath(source) not in filenames:
                    self.sources.append(VhdlSourceFile(source))
                else:
                    self._logger.warning("Source %s was already added", source)
        else:
            if os.path.abspath(sources) not in filenames:
                self.sources.append(VhdlSourceFile(sources))
            else:
                self._logger.warning("Source %s was already added", sources)

    def addBuildFlags(self, flags):
        """Adds a flag or a list of flags to be used when building
        source files for this library"""
        if not hasattr(flags, '__iter__'):
            flags = [flags]

        for flag in flags:
            if flag not in self._extra_flags:
                self._extra_flags.append(flag)

    def createOrMapLibrary(self):
        return self.builder.createOrMapLibrary(self.name)

    def deleteLibrary(self):
        return self.builder.deleteLibrary(self.name)

    def buildAll(self, forced=False):
        msg = []
        for source in self.sources:
            r = list(self._buildSource(source, forced))
            msg.append([source] + r)
        return msg

    # TODO: Check file modification time to invalidate cached info
    @memoid
    def getDependencies(self):
        deps = []
        for source in self.sources:
            source_deps = []
            for dep_lib, dep_units in source.getDependencies():
                # Work library means 'this' library, not a library
                # named work!
                if dep_lib == 'work':
                    dep_lib = self.name

                # When the file depends on something defined within
                # itself, remove this dependency.
                # TODO: Check how to handle circular dependencies
                if dep_lib == self.name:
                    for dep_unit in dep_units:
                        if dep_unit in source.getDesignUnits():
                            dep_units.remove(dep_unit)
                source_deps.append((dep_lib, dep_units))
            deps.append((source, source_deps))
        return deps

    @memoid
    def hasDesignUnit(self, unit):
        for source in self.sources:
            if unit in source.getDesignUnits():
                return True
        return False

    @memoid
    def getSourceByDesignUnit(self, unit):
        for source in self.sources:
            if unit in source.getDesignUnits():
                return source
        raise RuntimeError("Design unit '%s' not found in library '%s'" % \
                (str(unit), self.name))

    @memoid
    def hasSource(self, path):
        return os.path.abspath(path) in [x.abspath() for x in self.sources]

    @memoid
    def _getAbsPathOfSources(self):
        return [x.abspath() for x in self.sources]

    def buildSources(self, sources, forced=False, flags=[]):
        """Build a list or a single source. The argument should be
        a VhdlSourceFile object (retrieved via self.sources attribute or
        something similar"""
        if not hasattr(sources, '__iter__'):
            sources = [sources]
        msg = []
        abs_sources = self._getAbsPathOfSources()
        #  print "1 [%s] flags: %s" % (self.name, str(flags))
        for source in sources:
            if source.abspath() not in abs_sources:
                raise RuntimeError("Source %s not found in library %s" \
                        % (source, self.name))
            result = list(self._buildSource(source, forced, flags))
            msg.append([source] + result)
        return msg

    def buildByPath(self, path, forced=False, flags=[]):
        path = os.path.abspath(path)
        for source in self.sources:
            if path == source.abspath():
                return self._buildSource(source, forced, flags)
    def clearBuildCacheByPath(self, path):
        path = os.path.abspath(path)
        self._build_info_cache[os.path.abspath(path)]['compile_time'] = 0

