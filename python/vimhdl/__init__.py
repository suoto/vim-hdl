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
"""
vim-hdl is a VHDL syntax check provider that relies on third-party tools.
See https://github.com/suoto/vim-hdl for more information
"""

from vimhdl.config import Config
try:
    import vim
    Config.setupBuild()
except ImportError:
    pass
#  from vimhdl.project_builder import ProjectBuilder
#  from vimhdl.static_check import vhdStaticCheck

