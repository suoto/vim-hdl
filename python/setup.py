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
"Setup vimhdl Python paths"

import sys
import logging
_logger = logging.getLogger(__name__)

def vimhdlcreateClientIfNeeded():
    "Create the client if it doesn't exists yet"
    if 'vimhdl_client' not in globals():
        _logger.info("Creating client")
        globals()['vimhdl_client'] = vimhdl.VimhdlClient()
    else:
        _logger.info("Client already existed")

def vimhdlRestartServer(**server_args):
    _logger.info("Restarting hdlcc server")
    if 'vimhdl_client' in globals():
        globals()['vimhdl_client'].shutdown()
    del globals()['vimhdl_client']
    globals()['vimhdl_client'] = vimhdl.VimhdlClient(**server_args)
    globals()['vimhdl_client'].startServer()
    _logger.info("hdlcc restart done")


if 'vimhdl' not in sys.modules:
    import vim  # pylint: disable=import-error
    import os.path as p

    # Add a null handler for issue #19
    logging.root.addHandler(logging.NullHandler())

    for path in (p.join(vim.eval('vimhdl#basePath()'), 'python'),
                 p.join(vim.eval('vimhdl#basePath()'), 'dependencies', 'hdlcc')):
        if path not in sys.path:
            path = p.abspath(path)
            if p.exists(path):
                sys.path.insert(0, path)
                _logger.info("Adding %s", path)
            else:
                _logger.warning("Path '%s' doesn't exists!", path)

    import vimhdl
    import hdlcc  # pylint: disable=import-error,unused-import
    vimhdlcreateClientIfNeeded()
