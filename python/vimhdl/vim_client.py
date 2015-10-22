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
import threading

import vim

from vimhdl.project_builder import ProjectBuilder

_logger = logging.getLogger(__name__)

class VimhdlClient(ProjectBuilder):
    def __init__(self, *args, **kwargs):
        super(VimhdlClient, self).__init__(*args, **kwargs)
        self._build_lock = threading.Lock()
        self._threads = []

    def buildByDependencyAsync(self, *args, **kwargs):
        self._build_lock.acquire()
        this_thread = threading.Thread(target=self.buildByDependency,
            args=args, kwargs=kwargs)
        this_thread.start()
        self._threads.append(this_thread)
        self._build_lock.release()

vimhdl_client = None

def _getConfigFile():
    if 'vimhdl_conf_file' in vim.current.buffer.vars.keys():
        _logger.debug("Using config file from buffer dict")
        conf_file = vim.current.buffer.vars['vimhdl_conf_file']
    elif 'vimhdl_conf_file' in vim.vars.keys():
        _logger.debug("Using config file from global dict")
        conf_file = vim.vars['vimhdl_conf_file']
    else:
        _logger.warning("No config file specified")
        return

    conf_file_full_path = os.path.abspath(os.path.expanduser(conf_file))

    if os.path.exists(conf_file_full_path):
        return conf_file_full_path
    else:
        _logger.warning("Config file '%s' doesn't exists", conf_file_full_path)

def _getProjectObject():
    global vimhdl_client
    if vimhdl_client is None:
        config_file = _getConfigFile()
        _logger.debug("Config file is '%s'", config_file)
        vimhdl_client = VimhdlClient(config_file)
        vimhdl_client.buildByDependencyAsync()

def onBufEnter():
    _getProjectObject()
    _logger.info("Entered buffer number %d", vim.current.buffer.number)

def onBufWrite():
    _getProjectObject()
    _logger.info("Wrote buffer number %d", vim.current.buffer.number)

