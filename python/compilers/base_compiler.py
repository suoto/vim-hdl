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

import logging, os, re
from utils import shell

_logger = logging.getLogger(__name__)

class BaseCompiler(object):

    def __init__(self, target_folder):
        self._logger = logging.getLogger(__name__)
        self._TARGET_FOLDER = os.path.abspath(os.path.expanduser(target_folder))

        if not os.path.exists(self._TARGET_FOLDER):
            self._logger.info("%s doens't exists", self._TARGET_FOLDER)
            os.mkdir(self._TARGET_FOLDER)
        else:
            self._logger.info("%s already exists", self._TARGET_FOLDER)

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, d):
        self._logger = logging.getLogger(d['_logger'])
        del d['_logger']
        self.__dict__.update(d)

