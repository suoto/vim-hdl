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
"""
Wraps a piece of text and handles inserting _preface before it and then
removing it when the user closes the file. Also handles back up and restoring
in case something goes wrong
"""

import logging
import os
import os.path as p

import six

import vim  # pylint: disable=import-error
from vimhdl.vim_helpers import getProjectFile, presentDialog


# Copied from ycmd
def toBytes(value):  # pragma: no cover
    """
    Consistently returns the new bytes() type from python-future.
    Assumes incoming strings are either UTF-8 or unicode (which is
    converted to UTF-8).
    """

    if not value:
        return bytes()

    # This is tricky. On py2, the bytes type from builtins (from python-future) is
    # a subclass of str. So all of the following are true:
    #   isinstance(str(), bytes)
    #   isinstance(bytes(), str)
    # But they don't behave the same in one important aspect: iterating over a
    # bytes instance yields ints, while iterating over a (raw, py2) str yields
    # chars. We want consistent behavior so we force the use of bytes().

    if isinstance(value, bytes):
        return value

    # This is meant to catch Python 2's native str type.

    if isinstance(value, bytes):
        return bytes(value, encoding="utf8")

    if isinstance(value, str):
        # On py2, with `from builtins import *` imported, the following is true:
        #
        #   bytes(str(u'abc'), 'utf8') == b"b'abc'"
        #
        # Obviously this is a bug in python-future. So we work around it. Also filed
        # upstream at: https://github.com/PythonCharmers/python-future/issues/193
        # We can't just return value.encode('utf8') on both py2 & py3 because on
        # py2 that *sometimes* returns the built-in str type instead of the newbytes
        # type from python-future.

        if six.PY2:
            return bytes(value.encode("utf8"), encoding="utf8")

        return bytes(value, encoding="utf8")

    # This is meant to catch `int` and similar non-string/bytes types.

    return toBytes(str(value))


class ConfigGenWrapper(object):
    """
    Wraps a piece of text and handles inserting _preface before it and then
    removing it when the user closes the file. Also handles back up and
    restoring in case something goes wrong
    """

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
    _default_conf_filename = "vimhdl.prj"

    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._project_file = toBytes(
            getProjectFile() or self._default_conf_filename
        ).decode()

        self._backup_file = p.join(
            p.dirname(self._project_file),
            "." + p.basename(self._project_file) + ".backup",
        )

    def run(self, text):
        """
        Runs the wrapper using 'text' as content
        """
        # Cleanup autogroups before doing anything
        vim.command("autocmd! vimhdl BufUnload")

        # In case no project file was set and we used the default one
        if "vimhdl_conf_file" not in vim.vars:
            vim.vars["vimhdl_conf_file"] = self._project_file

        # Backup
        if p.exists(self._project_file):
            self._logger.info(
                "Backing up %s to %s", self._project_file, self._backup_file
            )
            os.rename(self._project_file, self._backup_file)

        contents = "\n".join([str(self._preface), text, "", "# vim: filetype=vimhdl"])

        self._logger.info("Writing contents to %s", self._project_file)
        open(self._project_file, "w").write(contents)

        # Need to open the resulting file and then setup auto commands to avoid
        # triggering them when loading / unloading the new buffer
        self._openResultingFileForEdit()
        self._setupOnQuitAutocmds()

    def _setupOnQuitAutocmds(self):
        """
        Creates an autocmd for the specified file only
        """
        self._logger.debug("Setting up auto cmds for %s", self._project_file)
        # Create hook to remove preface text when closing the file
        vim.command("augroup vimhdl")
        vim.command(
            "autocmd BufUnload %s :call s:onVimhdlTempQuit()"
            % p.abspath(self._project_file)
        )
        vim.command("augroup END")

    def _openResultingFileForEdit(self):
        """
        Opens the resulting conf file for editing so the user can tweak and
        test
        """
        self._logger.debug("Opening resulting file for edition")
        # If the current buffer is already pointing to the project file, reuse
        # it
        if not p.exists(vim.current.buffer.name) or p.samefile(
            vim.current.buffer.name, self._project_file
        ):
            vim.command("edit! %s" % self._project_file)
        else:
            vim.command("vsplit %s" % self._project_file)

        vim.current.buffer.vars["is_vimhdl_generated"] = True
        vim.command("set filetype=vimhdl")

    def onVimhdlTempQuit(self):
        """
        Callback for closing the generated project file to remove the preface
        from the buffer contents
        """
        # Don't touch files created by the user of files where the preface has
        # already been (presumably) taken out
        if not vim.current.buffer.vars.get("is_vimhdl_generated", False):
            return

        # No pop on Vim's RemoteMap dictionary
        del vim.current.buffer.vars["is_vimhdl_generated"]
        # No need to call this again
        vim.command("autocmd! vimhdl BufUnload")

        try:
            should_save = vim.vars["vimhdl_auto_save_created_config_file"] == 1
        except KeyError:
            # Ask if the user wants to use the resulting file or if the backup
            # should be restored
            should_save = (
                presentDialog(
                    "Project file contents were modified, should save changes or "
                    "restore backup?",
                    ["Save changes", "Restore backup"],
                )
                == 0
            )

        if should_save:
            self._removePrefaceAndSave()
        else:
            self._restoreBackup()

    def _restoreBackup(self):
        """
        Restores the backup file (if exists) as the main project file
        """
        if p.exists(self._backup_file):
            os.rename(self._backup_file, self._project_file)
        else:
            self._logger.info("No backup file exists, can't recover")

    def _removePrefaceAndSave(self):
        """
        Remove contents until the line we said we would and save the file
        """
        # Search for the last line we said we'd remove
        lnum = 0
        for lnum, line in enumerate(vim.current.buffer):
            if "Everything up to this line will be automatically removed" in line:
                self._logger.debug("Breaing at line %d", lnum)
                break

        # Remove line not found
        if not lnum:
            return

        # Update and save
        vim.current.buffer[:] = list(vim.current.buffer)[lnum + 1 :]
        vim.command("write!")
