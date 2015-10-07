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
import subprocess
import re
from threading import Thread
import time

from utils import memoid
from source_file import VhdlSourceFile

CTAGS_ARGS = '--tag-relative=no --totals=no --sort=foldcase --extra=+f --fields=+i-l+m+s+S --links=yes --append'
RE_CTAGS_IGNORE_LINE = re.compile(r"^\s*$|ctags-exuberant: Warning: Language \"vhdl\" already defined")

class Library(object):
    """Organizes a collection of VhdlSourceFile objects and calls the
    builder with the appropriate parameters"""

    def __init__(self, builder, sources=None, name='work', target_dir=None):
        self.builder = builder
        self.name = name
        self.sources = []

        self.target_dir = target_dir or os.curdir
        self.tag_file = 'tags'

        self._extra_flags = []
        self._logger = logging.getLogger("Library('%s')" % self.name)

        self._build_info_cache = {}
        if sources is not None:
            self.addSources(sources)

    def __str__(self):
        return "Library(name='%s')" % self.name

    def __repr__(self):
        return str(self)

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        self._logger = logging.getLogger(state['_logger'])
        del state['_logger']
        self.__dict__.update(state)

    def _updateTags(self, source):
        cmd = ['ctags-exuberant'] + re.split(r"\s+", CTAGS_ARGS) + \
                ['-f', self.tag_file, str(source)]

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self._logger.fatal(e.output)

    # TODO: Check file modification time to invalidate cached info
    def _buildSource(self, source, forced=False, flags=[]):
        """Handle caching of source build information, like warnings and
        errors."""
        if source.abspath() not in self._build_info_cache.keys():
            self._build_info_cache[source.abspath()] = {
                'compile_time': 0, 'size' : 0, 'errors': (), 'warnings': ()
            }

        cached_info = self._build_info_cache[source.abspath()]

        build = False
        _build_info = ""

        if forced:
            build = True
            _build_info = "forced"
        else:
            if os.stat(source.abspath()).st_size == cached_info['size']:
                build = False
                _build_info = "no size change"
            elif source.getmtime() > cached_info['compile_time']:
                build = True
                _build_info = "mtime"

        if _build_info:
            self._logger.info("[%s] Build info: %s", str(source), _build_info)

        tags_t = None

        if build:
            tags_t = Thread(target=self._updateTags, args=(source,))
            tags_t.start()

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
            cached_info['size'] = os.stat(source.abspath()).st_size
        else:
            errors = cached_info['errors']
            warnings = cached_info['warnings']
            rebuilds = cached_info['rebuilds']

        if rebuilds:
            cached_info['compile_time'] = 0


        if tags_t is not None:
            tags_t.join()
        return errors, warnings, rebuilds

    def addSources(self, sources):
        "Adds a source or a list of sources to this library"
        assert self.sources is not None

        if hasattr(sources, '__iter__'):
            for source in sources:
                if not self.hasSource(source):
                    self.sources.append(VhdlSourceFile(source))
                else:
                    self._logger.warning("Source %s was already added", source)
        else:
            if not self.hasSource(sources):
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
    #  @memoid
    def getDependencies(self):
        """Gets the dependency tree for this library"""

        # Add an entry to our cached with the dependency check info
        if 'dependency_check' not in self._build_info_cache.keys():
            self._build_info_cache['dependency_check'] = {
                    'timestamp' : 0,
                    'dependencies' : {},
                    }

        cached_info = self._build_info_cache['dependency_check']

        # If no sources have changed since we last checked, return the
        # info we have cached
        reparse = False
        for source in self.sources:
            if source.getmtime() > cached_info['timestamp']:
                reparse = True
                break

        if not reparse:
            return cached_info['dependencies']

        self._logger.debug("Some sources changed, reparsing")

        # While parsing, store entries in a dict to change it based
        # on which sources actually changed
        dep_dict = dict(cached_info['dependencies'])

        for source in self.sources:
            # If this source hasn't changed, skip it
            if source.getmtime() < cached_info['timestamp']:
                continue

            self._logger.debug("Source %s changed, updating its "
                    "dependencies", source)

            source_deps = []
            for dep_lib, dep_unit in source.getDependencies():
                # Work library means 'this' library, not a library
                # named work!
                if dep_lib == 'work':
                    dep_lib = self.name

                # When the file depends on something defined within
                # itself, remove this dependency.
                # TODO: Check how to handle circular dependencies
                if dep_lib == self.name and dep_unit in source.getDesignUnits():
                    continue
                source_deps.append((dep_lib, dep_unit))
            dep_dict[source] = source_deps

        cached_info['timestamp'] = time.time()
        # We don't return in a dict-like object. Maybe will do that if
        # helps anything...
        cached_info['dependencies'] = zip(dep_dict.keys(), dep_dict.values())

        self._build_info_cache['dependency_check'] = cached_info

        return cached_info['dependencies']

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

    #  @memoid
    def hasSource(self, path):
        for source in self.sources:
            if os.path.samefile(str(path), str(source)):
                return True
        return False

    def buildSources(self, sources, forced=False, flags=[]):
        """Build a list or a single source. The argument should be
        a VhdlSourceFile object (retrieved via self.sources attribute or
        something similar"""
        if not hasattr(sources, '__iter__'):
            sources = [sources]
        msg = []

        for source in sources:
            if not self.hasSource(source):
                raise RuntimeError("Source %s not found in library %s" \
                        % (source, self.name))
            result = list(self._buildSource(source, forced, flags))
            msg.append([source] + result)
        return msg

    def buildByPath(self, path, forced=False, flags=[]):
        for source in self.sources:
            if os.path.samefile(str(source), path):
                return self._buildSource(source, forced, flags)
    def clearBuildCacheByPath(self, path):
        path = os.path.abspath(path)
        self._build_info_cache[path]['compile_time'] = 0

