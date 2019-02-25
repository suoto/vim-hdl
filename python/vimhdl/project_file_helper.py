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

import vim  # pylint: disable=import-error
import vimhdl
from hdlcc.utils import UnknownTypeExtension, getFileType, isFileReadable

_SOURCE_EXTENSIONS = 'vhdl', 'sv', 'v'
_HEADER_EXTENSIONS = 'vh', 'svh'

_DEFAULT_LIBRARY_NAME = {
        'vhdl': 'lib',
        'verilog': 'lib',
        'systemverilog': 'lib'}

class ProjectFileCreator:
    """
    Base class for creating project files semi automatically.
    """

    __metaclass__ = abc.ABCMeta
    _default_conf_filename = 'vimhdl.prj'

    _preface = """\
# This is the resulting project file, please review and save when done. The
# g:vimhdl_conf_file variable has been temporarily changed to point to this
# file should you wish to open HDL files and test the results. When finished,
# close this buffer; you''ll be prompted to either use this file or revert to
# the original one.
#
# ---- Everything up to this line will be automatically removed ----
""".splitlines()

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

        self._project_file = vimhdl.vim_helpers.getProjectFile() or \
                ProjectFileCreator._default_conf_filename

        self._backup_file = p.join(
            p.dirname(self._project_file),
            '.' + p.basename(self._project_file) + '.backup')

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

    def run(self):
        #  return self._runCreationHelper()

        # If this is being called from within an existing config file
        # buffer, quit the existing buffer first
        if vim.current.buffer.vars.get('is_vimhdl_conf_file'):
            self._logger.info("is_vimhdl_conf_file is set, cleaning it up")
            del vim.current.buffer.vars['is_vimhdl_conf_file']
            #  open(vim.current.buffer.name, 'w').write('')
            #  #  vim.command('%%d')
            #  #  vim.command('write')
            vim.command('quit')
            #  self._logger.info("buffer now has %d lines", len(vim.current.buffer))

        # In case no project file was set and we used the default one
        if 'vimhdl_conf_file' not in vim.vars:
            vim.vars['vimhdl_conf_file'] = self._project_file

        # Backup
        if p.exists(self._project_file):
            self._logger.info("Backing up %s to %s", self._project_file,
                              self._backup_file)
            os.rename(self._project_file, self._backup_file)

        open(self._project_file, 'w').write('')

        self._runCreationHelper()
        self._setupVimhdlProjectFileAutocmds()
        self._openResultingFileForEdit()

    def _runCreationHelper(self):
        """
        Runs the _create method in the child class and assemble the actual
        contents of the project file
        """
        self._logger.info("Running creation helpers")

        self._create()
        builder = self._getPreferredBuilder()

        contents = []
        contents += ProjectFileCreator._preface

        contents += ['# Generated on %s' % time.ctime(),
                     '# Files found: %s' % len(self._sources),
                     '# Available builders: %s' % ', '.join(self._builders)]

        if builder in self._builders:
            contents += ['builder = %s' % builder]

        contents += ['']

        # Add include paths if any
        for lang, paths in self._include_paths.items():
            include_paths = self._formatIncludePaths(paths)
            if include_paths:
                contents += ['global_build_flags[%s] = %s' % (lang, include_paths)]

        if self._include_paths:
            contents += ['']

        # Add sources
        sources = []

        for path, flags, library in self._sources:
            file_type = getFileType(path)
            sources.append((file_type, library, path, flags))

        sources.sort(key=lambda x: x[2])

        for file_type, library, path, flags in sources:
            contents += ['{0} {1} {2} {3}'.format(file_type, library, path,
                                                  flags)]

        if self._sources:
            contents += ['', '']

        self._logger.info("Resulting file has %d lines", len(contents))

        open(self._project_file, 'w').write('\n'.join(contents))

    def _setupVimhdlProjectFileAutocmds(self):
        self._logger.debug("Setting up auto cmds")
        vim.command('autocmd! vimhdl QuitPre')
        vim.command('augroup vimhdl')
        vim.command('autocmd QuitPre %s :call s:onVimhdlTempQuit()' % self._project_file)
        vim.command('augroup END')

    def _openResultingFileForEdit(self):
        self._logger.debug("Opening resulting file for edition")
        vim.command('vs %s' % self._project_file)
        vim.command('edit! %')
        vim.current.buffer.vars['config_file'] = self._project_file
        vim.current.buffer.vars['backup_file'] = self._backup_file
        vim.current.buffer.vars['is_vimhdl_conf_file'] = True
        vim.command('set filetype=vimhdl')

    def onVimhdlTempQuit(self):
        if vim.eval('&filetype') != 'vimhdl':
            self._logger.debug("Nothing to do for filetype %s",
                               vim.eval('&filetype'))
            return

        # Disable autocmds
        vim.command('autocmd! vimhdl QuitPre')

        modified = bool(vim.eval('&modified') == "1")

        lnum = 0
        for lnum, line in enumerate(vim.current.buffer):
            if 'Everything up to this line will be automatically removed' in line:
                self._logger.debug("Breaing at line %d", lnum)
                break

        if lnum:
            vim.command('1,%dd' % (lnum + 1))
            if not modified:
                vim.command(':write')

        #  actual_content = '\n'.join(actual_content)
        #  self._logger.info("Actual content: %s", actual_content)
        #  open(self._project_file, 'w').write(str(actual_content))
        #  vim.command(':edit! %s' % vim.current.buffer.name)

class FindProjectFiles(ProjectFileCreator):
    """
    Implementation of ProjectFileCreator that searches for paths on a given
    set of paths recursively
    """
    def __init__(self, builders, cwd, paths):
        super(FindProjectFiles, self).__init__(builders, cwd)
        self._logger.debug("Search paths: %s", paths)
        self._paths = paths
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
