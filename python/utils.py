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

def findFilesInPath(path, f, recursive=True):
    """
    Finds files that match f(_file_), where _file_ is the relative path to the item found.
    """
    path = os.path.expanduser(path)
    if recursive:
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                relpath_to_filename = os.path.sep.join([dirpath, filename])
                if f(relpath_to_filename):
                    yield os.path.normpath(relpath_to_filename)
    else:
        for l in os.listdir(path):
            l = os.path.sep.join([path, l])
            if not os.path.isfile(l):
                continue
            if f(l):
                yield os.path.normpath(l)

def findVhdsInPath(path, recursive=True):
    return findFilesInPath(path, _is_vhd, recursive)

def _is_vhd(p):
    return os.path.basename(p).lower().endswith('vhd')

def _is_makefile(f):
    return os.path.basename(f) == 'Makefile'
