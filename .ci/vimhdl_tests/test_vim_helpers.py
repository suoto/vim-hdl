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

# pylint: disable=function-redefined, missing-docstring, protected-access

import sys
import os
import os.path as p
import logging

from nose2.tools import such

_CI = os.environ.get("CI", None) is not None

_logger = logging.getLogger(__name__)

def _setupPaths():
    base_path = p.abspath(p.join(p.dirname(__file__), '..', '..'))
    for path in (p.join(base_path, 'python'),
                 p.join(base_path, 'dependencies', 'requests')):
        print path
        sys.path.insert(0, path)

_setupPaths()

# pylint: disable=import-error,wrong-import-position
from vimhdl_tests.vim_mock import mockVim
mockVim()
import vim
import vimhdl.vim_helpers as vim_helpers
# pylint: enable=import-error,wrong-import-position

with such.A('vim_helpers module') as it:
    @it.should("return all buffer variables from the current buffer if "
               "neither buffer or variable are defined")
    def test():
        it.assertEquals(
            vim_helpers._getBufferVars(),
            {'current_buffer_var_0' : 'current_buffer_value_0',
             'current_buffer_var_1' : 'current_buffer_value_1'})

    @it.should("return the given buffer variable of the current buffer if "
               "only the first one is given")
    def test():
        it.assertEquals(vim_helpers._getBufferVars(var='current_buffer_var_0'),
                        'current_buffer_value_0')
        it.assertEquals(vim_helpers._getBufferVars(var='current_buffer_var_1'),
                        'current_buffer_value_1')

    @it.should("return all variables of other buffers")
    def test():
        it.assertEquals(
            vim_helpers._getBufferVars(vim.buffers[0]),
            {'buffer_0_var_0' : 'buffer_0_var_value_0',
             'buffer_0_var_1' : 'buffer_0_var_value_1',}
            )
        it.assertEquals(
            vim_helpers._getBufferVars(vim.buffers[1]),
            {'buffer_1_var_0' : 'buffer_1_var_value_0',
             'buffer_1_var_1' : 'buffer_1_var_value_1',}
            )

    @it.should("return a specific variable of a specific buffer")
    def test():
        it.assertEquals(
            vim_helpers._getBufferVars(vim.buffers[0], 'buffer_0_var_0'),
            'buffer_0_var_value_0',)

it.createTests(globals())

