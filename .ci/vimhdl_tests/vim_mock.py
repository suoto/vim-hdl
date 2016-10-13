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

import sys

try:  # Python 3.x
    import unittest.mock as mock # pylint: disable=import-error, no-name-in-module
except ImportError:  # Python 2.x
    import mock



vim = mock.MagicMock() # pylint: disable=invalid-name

def mockVim():
    sys.modules['vim'] = vim

vim.current = mock.MagicMock()
vim.current.buffer = mock.MagicMock(
        vars={'current_buffer_var_0' : 'current_buffer_value_0',
              'current_buffer_var_1' : 'current_buffer_value_1'})

vim.buffers = {
    0 : mock.MagicMock(vars={'buffer_0_var_0' : 'buffer_0_var_value_0',
                             'buffer_0_var_1' : 'buffer_0_var_value_1'}),
    1 : mock.MagicMock(vars={'buffer_1_var_0' : 'buffer_1_var_value_0',
                             'buffer_1_var_1' : 'buffer_1_var_value_1'}),
}


