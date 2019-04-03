# This file is part of vim-hdl.
#
# Copyright (c) 2015-2016 Andre Souto
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
import os.path as p

import vim  # pylint: disable=import-error
from vimhdl.vim_helpers import getProjectFile
from hdlcc.utils import toBytes


class ProjectFileHelper(object):
    _preface = """\
# This is the resulting project file, please review and save when done. The
# g:vimhdl_conf_file variable has been temporarily changed to point to this
# file should you wish to open HDL files and test the results. When finished,
# close this buffer; you''ll be prompted to either use this file or revert to
# the original one.
#
# ---- Everything up to this line will be automatically removed ----"""

    # If the user hasn't already set vimhdl_conf_file in g: or b:, we'll use
    # this instead
    _default_conf_filename = 'vimhdl.prj'
    open_after_running = True

    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._project_file = toBytes(getProjectFile() or
                                     self._default_conf_filename).decode()

        self._backup_file = p.join(
            p.dirname(self._project_file),
            '.' + p.basename(self._project_file) + '.backup')

    def run(self, text):
        # Cleanup autogroups before doing anything
        vim.command('autocmd! vimhdl BufUnload')

        # In case no project file was set and we used the default one
        if 'vimhdl_conf_file' not in vim.vars:
            vim.vars['vimhdl_conf_file'] = self._project_file

        # Backup
        if p.exists(self._project_file):
            self._logger.info("Backing up %s to %s", self._project_file,
                              self._backup_file)
            os.rename(self._project_file, self._backup_file)

        contents = '\n'.join([str(self._preface), text,
                              '', '# vim: filetype=vimhdl'])

        self._logger.info("Writing contents to %s", self._project_file)
        open(self._project_file, 'w').write(contents)

        if self.open_after_running:
            # Need to open the resulting file and then setup auto commands to
            # avoid triggering them when loading / unloading the new buffer
            self._openResultingFileForEdit()
            self._setupOnQuitAutocmds()

    def _setupOnQuitAutocmds(self):
        """
        Creates an autocmd for the specified file only
        """
        self._logger.debug("Setting up auto cmds for %s", self._project_file)
        # Create hook to remove preface text when closing the file
        vim.command('augroup vimhdl')
        vim.command('autocmd BufUnload %s :call s:onVimhdlTempQuit()' %
                    self._project_file)
        vim.command('augroup END')

    def _openResultingFileForEdit(self):
        """
        Opens the resulting conf file for editing so the user can tweak and
        test
        """
        self._logger.debug("Opening resulting file for edition")
        # If the current buffer is already pointing to the project file, reuse
        # it
        if not p.exists(vim.current.buffer.name) or \
                p.samefile(vim.current.buffer.name, self._project_file):
            vim.command('edit! %s' % self._project_file)
        else:
            vim.command('vsplit %s' % self._project_file)

        vim.current.buffer.vars['is_vimhdl_generated'] = True
        vim.command('set filetype=vimhdl')

    def onVimhdlTempQuit(self):
        """
        Callback for closing the generated project file to remove the preface
        from the buffer contents
        """
        # Don't touch files created by the user of files where the preface has
        # already been (presumably) taken out
        if not vim.current.buffer.vars.get('is_vimhdl_generated', False):
            return

        # No pop on Vim's RemoteMap dictionary
        del vim.current.buffer.vars['is_vimhdl_generated']
        # No need to call this again
        vim.command('autocmd! vimhdl BufUnload')

        # Search for the last line we said we'd remove
        lnum = 0
        for lnum, line in enumerate(vim.current.buffer):
            if 'Everything up to this line will be automatically removed' in line:
                self._logger.debug("Breaing at line %d", lnum)
                break

        # Remove line not found
        if not lnum:
            return

        # Update and save
        vim.current.buffer[ : ] = list(vim.current.buffer)[lnum + 1 : ]
        vim.command('write!')
