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
"Wrapper for vim-hdl usage within Vim's Python interpreter"

import logging
import os
import threading

# pylint: disable=import-error
import vim
# pylint: enable=import-error

from vimhdl.project_builder import ProjectBuilder

__logger__ = logging.getLogger(__name__)
__vimhdl_client__ = None

class VimhdlClient(ProjectBuilder):
    """Wrapper around ProjectBuilder class to make the interface between Vim
    and vim-hdl"""
    def __init__(self, *args, **kwargs):
        super(VimhdlClient, self).__init__(*args, **kwargs)
        self._build_lock = threading.Lock()
        self._threads = []

    def buildByDependencyAsync(self, *args, **kwargs):
        "Builds the project by dependency asynchronously"
        self._build_lock.acquire()
        this_thread = threading.Thread(target=self.buildByDependency,
            args=args, kwargs=kwargs)
        this_thread.start()
        self._threads.append(this_thread)
        self._build_lock.release()

def _getConfigFile():
    if 'vimhdl_conf_file' in vim.current.buffer.vars.keys():
        __logger__.debug("Using config file from buffer dict")
        conf_file = vim.current.buffer.vars['vimhdl_conf_file']
    elif 'vimhdl_conf_file' in vim.vars.keys():
        __logger__.debug("Using config file from global dict")
        conf_file = vim.vars['vimhdl_conf_file']
    else:
        __logger__.warning("No config file specified")
        return

    conf_file_full_path = os.path.abspath(os.path.expanduser(conf_file))

    if os.path.exists(conf_file_full_path):
        return conf_file_full_path
    else:
        __logger__.warning("Config file '%s' doesn't exists", conf_file_full_path)

#  pylint: disable=redefined-outer-name,missing-docstring

def _getProjectObject():
    global __vimhdl_client__
    if __vimhdl_client__ is None:
        config_file = _getConfigFile()
        __logger__.debug("Config file is '%s'", config_file)
        __vimhdl_client__ = VimhdlClient(config_file)
        __vimhdl_client__.buildByDependencyAsync()
    return __vimhdl_client__

def onBufRead():
    __logger__.debug("[%d] No action defined for event 'onBufRead'",
        vim.current.buffer.number)

def onBufWrite():
    __vimhdl_client__ = _getProjectObject()
    __vimhdl_client__.buildByPath(vim.current.buffer.name)
    __logger__.info("Wrote buffer number %d", vim.current.buffer.number)

def onBufEnter():
    __logger__.debug("[%d] No action defined for event 'onBufEnter'",
        vim.current.buffer.number)

def onBufLeave():
    __logger__.debug("[%d] No action defined for event 'onBufLeave'",
        vim.current.buffer.number)

def onBufWinEnter():
    __logger__.debug("[%d] No action defined for event 'onBufWinEnter'",
        vim.current.buffer.number)

def onBufWinLeave():
    __logger__.debug("[%d] No action defined for event 'onBufWinLeave'",
        vim.current.buffer.number)

def onFocusGained():
    __logger__.debug("[%d] No action defined for event 'onFocusGained'",
        vim.current.buffer.number)

def onFocusLost():
    __logger__.debug("[%d] No action defined for event 'onFocusLost'",
        vim.current.buffer.number)

def onCursorHold():
    __logger__.debug("[%d] No action defined for event 'onCursorHold'",
        vim.current.buffer.number)

def onCursorHoldI():
    __logger__.debug("[%d] No action defined for event 'onCursorHoldI'",
        vim.current.buffer.number)

def onWinEnter():
    __logger__.debug("[%d] No action defined for event 'onWinEnter'",
        vim.current.buffer.number)

def onWinLeave():
    __logger__.debug("[%d] No action defined for event 'onWinLeave'",
        vim.current.buffer.number)

def onTabEnter():
    __logger__.debug("[%d] No action defined for event 'onTabEnter'",
        vim.current.buffer.number)

def onTabLeave():
    __logger__.debug("[%d] No action defined for event 'onTabLeave'",
        vim.current.buffer.number)


