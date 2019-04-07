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
import sys

def _setupLogging(): # pragma: no cover
    """
    Overwrite the default formatter
    """
    for handler in logging.root.handlers:
        handler.formatter = logging.Formatter(
            '%(levelname)-7s | %(asctime)s | ' +
            '%(name)s @ %(funcName)s():%(lineno)d %(threadName)s ' +
            '|\t%(message)s', datefmt='%H:%M:%S')

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('pynvim').setLevel(logging.WARNING)

_setupLogging()
