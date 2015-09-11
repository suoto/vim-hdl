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

import logging, os

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

    def _memoid(f):
        def _memoid_w(self, *args, **kwargs):
            k = str((f, args, kwargs))
            if not hasattr(self, '_cache'):
                self._cache = {}
            if k not in self._cache.keys():
                self._cache[k] = f(self, *args, **kwargs)
            return self._cache[k]
        return _memoid_w

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
    def _buildSource(self, source, forced=False):
        """Handle caching of source build information, like warnings and
        errors."""
        if source.abspath() not in self._build_info_cache.keys():
            self._build_info_cache[source.abspath()] = {
                'compile_time': 0, 'errors': (), 'warnings': ()
            }

        cached_info = self._build_info_cache[source.abspath()]

        if source.getmtime() > cached_info['compile_time'] or forced:
            errors, warnings = self.builder.build(
                self.name, source, self._extra_flags)

            cached_info['compile_time'] = source.getmtime()
            cached_info['errors'] = errors
            cached_info['warnings'] = warnings
        else:
            errors, warnings = cached_info['errors'], cached_info['warnings']

        #  if errors:
        #      cached_info['compile_time'] = 0

        #  TODO: msim vcom-1195 means something wasn't found. Since this
        # something could be in some file not yet compiled, we'll leave the
        # cached status clear, so we force recompile only in this case.  This
        # should be better studied because avoiding to recompile a file that
        # had errors could be harmful
        for error in errors:
            if '(vcom-11)' in error:
                self._logger.error("(%s) %s %s", self.name, str(source), error)

        return errors, warnings

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

    def buildAll(self, forced=False):
        msg = []
        for source in self.sources:
            r = list(self._buildSource(source, forced))
            msg.append([source] + r)
        return msg

    # TODO: Check file modification time to invalidate cached info
    @_memoid
    def getDependencies(self):
        deps = []
        for source in self.sources:
            source_deps = []
            for dep_lib, dep_unit in source.getDependencies():
                # Work library means 'this' library, not a library
                # named work!
                if dep_lib == 'work':
                    dep_lib = self.name
                source_deps.append((dep_lib, dep_unit))
            deps.append((source, source_deps))
        return deps

    @_memoid
    def hasSource(self, path):
        return os.path.abspath(path) in [x.abspath() for x in self.sources]

    @_memoid
    def _getAbsPathOfSources(self):
        return [x.abspath() for x in self.sources]

    def buildSources(self, sources, forced=False):
        """Build a list or a single source. The argument should be
        a VhdlSourceFile object (retrieved via self.sources attribute or
        something similar"""
        if not hasattr(sources, '__iter__'):
            sources = [sources]
        msg = []
        abs_sources = self._getAbsPathOfSources()
        for source in sources:
            if source.abspath() not in abs_sources:
                raise RuntimeError("Source %s not found in library %s" \
                        % (source, self.name))
            result = list(self._buildSource(source, forced))
            msg.append([source] + result)
        return msg

    def buildByPath(self, path, forced=False):
        path = os.path.abspath(path)
        for source in self.sources:
            if path == source.abspath():
                return self._buildSource(source, forced)

