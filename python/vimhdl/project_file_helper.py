# This file is part of vim-hdl.
#
# Copyright (c) 2015-2019 Andre Souto
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
"Base class for creating a project file"

import abc
import logging
import os
import os.path as p
import time

from hdlcc.utils import UnknownTypeExtension, getFileType, isFileReadable

_logger = logging.getLogger(__name__)

_SOURCE_EXTENSIONS = 'vhdl', 'sv', 'v'
_HEADER_EXTENSIONS = 'vh', 'svh'

_DEFAULT_LIBRARY_NAME = {
        'vhdl': 'default_library',
        'verilog': 'default_library',
        'systemverilog': 'default_library'}

class ProjectFileCreator:
    """
    Base class for creating project files semi automatically.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, builders, cwd):
        """
        Arguments:
            - builders: list of builder names that the server has reported as
                        working
            - cwd: current working directory. This will influence where the
                   resulting file is saved
        """
        self._builders = builders
        self._cwd = cwd
        self._logger = logging.getLogger(self.__class__.__name__)
        self._sources = set()
        self._include_paths = {'verilog': set(),
                               'systemverilog': set()}

    open_after_running = property(lambda self: True, doc="""
        open_after_running enables or disables opening the resulting project
        file after the creator has run.""")

    def _addSource(self, path, flags, library=None):
        """
        Add a source to project. 'flags' and 'library' are only used for
        regular sources and not for header files (files ending in .vh or .svh)
        """
        self._logger.debug("Adding path %s (flgas=%s, library=%s)", path,
                           flags, library)

        if p.basename(path).split('.')[-1].lower() in ('vh', 'svh'):
            file_type = getFileType(path)
            if file_type in ('verilog', 'systemverilog'):
                self._include_paths[file_type].add(p.dirname(path))
        else:
            self._sources.add((path, ' '.join([str(x) for x in flags]),
                               library))

    @abc.abstractmethod
    def _create(self):
        """
        Method that will be called for generating the project file contets and
        should be implemented by child classes
        """

    @abc.abstractmethod
    def _getPreferredBuilder(self):
        """
        Method should be overridden by child classes to express the preferred
        builder
        """

    def _formatIncludePaths(self, paths):
        """
        Format a list of paths to be used as flags by the builder. (Still needs
        a bit of thought, ideally only the builder know how to do this)
        """
        builder = self._getPreferredBuilder()

        if builder == 'msim':
            return ' '.join(['+incdir+%s' % path for path in paths])

        return ''

    def create(self):
        """
        Runs the _create method in the child class and assemble the actual
        contents of the project file
        """
        self._create()
        builder = self._getPreferredBuilder()

        contents = ['# Generated on %s' % time.ctime(),
                    '# Files found: %s' % len(self._sources),
                    '# Available builders: %s' % ', '.join(self._builders),
                    'builder = %s' % builder,
                    '']

        # Add include paths if any
        for lang, paths in self._include_paths.items():
            include_paths = self._formatIncludePaths(paths)
            if include_paths:
                contents += ['global_build_flags[%s] = %s' % (lang, include_paths)]

        if self._include_paths:
            contents += ['']

        # Add sources
        for path, flags, library in self._sources:
            file_type = getFileType(path)
            contents += ['{0} {1} {2} {3}'.format(file_type, library, path,
                                                  flags)]

        if self._sources:
            contents += ['', '']

        for line in contents:
            self._logger.debug(line)

        return '\n'.join(contents)

class FindProjectFiles(ProjectFileCreator):
    """
    Implementation of ProjectFileCreator that searches for paths on a given
    set of paths recursively
    """
    def __init__(self, builders, cwd, paths):
        super(FindProjectFiles, self).__init__(builders, cwd)
        self._logger.info("Search paths: %s", paths)
        self._paths = (p.abspath(path) for path in paths)
        self._valid_extensions = tuple(list(_SOURCE_EXTENSIONS) +
                                       list(_HEADER_EXTENSIONS))

    def _getPreferredBuilder(self):
        if 'msim' in self._builders:
            return 'msim'
        if 'ghdl' in self._builders:
            return 'ghdl'
        return 'xvhdl'

    def _getCompilerFlags(self, path):
        """
        Returns file specific compiler flags
        """
        if self._getPreferredBuilder() != 'msim':
            return []

        flags = []
        # Testbenches are usually more relaxed, so set VHDL 2008
        if (p.basename(path).split('.')[0].endswith('_tb') or
                p.basename(path).startswith('tb_')):
            flags += ['-2008']

        return flags

    def _getLibrary(self, path):  # pylint: disable=no-self-use
        """
        Returns the library name given the path. On this implementation this
        returns a default name; child classes can override this to provide
        specific names (say the library name is embedded on the path itself or
        on the file's contents)
        """
        extension = getFileType(path)
        return _DEFAULT_LIBRARY_NAME[extension]

    def _findSources(self):
        """
        Iterates over the paths and searches for relevant files by extension.
        """
        for path in self._paths:
            for dirpath, _, filenames in os.walk(path):
                for filename in filenames:
                    path = p.join(dirpath, filename)

                    if not p.isfile(path):
                        continue

                    try:
                        # getFileType will fail if the file's extension is not
                        # valid (one of '.vhd', '.vhdl', '.v', '.vh', '.sv',
                        # '.svh')
                        getFileType(filename)
                    except UnknownTypeExtension:
                        continue

                    if isFileReadable(path):
                        yield path

    def _create(self):
        for path in self._findSources():
            self._addSource(path, flags=self._getCompilerFlags(path),
                            library=self._getLibrary(path))
