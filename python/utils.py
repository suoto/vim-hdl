# This file is part of hdl-syntax-checker.
#
# hdl-syntax-checker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# hdl-syntax-checker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hdl-syntax-checker.  If not, see <http://www.gnu.org/licenses/>.

import os, logging

_logger = logging.getLogger(__name__)

def shell(cmd, exit_status = 0):
    """
    Dummy wrapper for running shell commands, checking the return value and logging
    """

    sts = os.system(cmd)

    if sts == exit_status:
        _logger.debug(cmd)
    else:
        if sts == 512:
            _logger.debug("'%s' returned %d (expected %d)", cmd, sts, exit_status)
        else:
            _logger.warning("'%s' returned %d (expected %d)", cmd, sts, exit_status)
    return sts

def touch(arg):
    open(str(arg), 'a').close()

