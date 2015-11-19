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
"Base class that implements the base compiler flow"

import logging
import os
import abc
import time
from threading import Lock

_logger = logging.getLogger(__name__)

class BaseCompiler(object):
    "Class that implements the base compiler flow"

    __metaclass__ = abc.ABCMeta

    # Shell accesses must be atomic
    _lock = Lock()

    def __init__(self, target_folder):
        self._logger = logging.getLogger(__name__)
        self._target_folder = os.path.abspath(os.path.expanduser(target_folder))

        self.builtin_libraries = []
        self._build_info_cache = {}

        if not os.path.exists(self._target_folder):
            self._logger.info("%s doens't exists", self._target_folder)
            os.mkdir(self._target_folder)
        else:
            self._logger.info("%s already exists", self._target_folder)

        self._checkEnvironment()

    @abc.abstractmethod
    def _makeMessageRecord(self, message):
        """Static method that converts a string into a dict that has
        elements identifying its fields"""

    @abc.abstractmethod
    def _checkEnvironment(self):
        """Sanity environment check that should be implemented by child
        classes. Nothing is done with the return, the child class should
        raise an exception by itself"""

    @abc.abstractmethod
    def _doBuild(self, source, flags=None):
        """Callback called to actually build the source"""

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        self._logger = logging.getLogger(state['_logger'])
        del state['_logger']
        self.__dict__.update(state)

    def build(self, source, forced=False, flags=None):
        """Method that interfaces with parents and implements the
        building chain"""

        start = time.time()
        if source.abspath() not in self._build_info_cache.keys():
            self._build_info_cache[source.abspath()] = {
                'compile_time': 0, 'size' : 0, 'records': ()
            }

        cached_info = self._build_info_cache[source.abspath()]

        build = False
        if forced:
            build = True
            self._logger.info("Forcing build of %s", str(source))
        if source.getmtime() > cached_info['compile_time']:
            build = True
            self._logger.info("Building %s because it has changed", str(source))

        if build:
            # Build a set of unique flags and pass it as tuple
            build_flags = set()
            build_flags.update(source.flags)
            build_flags.update(flags)
            with self._lock:
                records, rebuilds = self._doBuild(source, flags=tuple(build_flags))

            cached_info['compile_time'] = source.getmtime()
            cached_info['records'] = records
            cached_info['rebuilds'] = rebuilds
            cached_info['size'] = os.stat(source.abspath()).st_size

            end = time.time()
            self._logger.debug("Compiling took %.2fs", (end - start))
        else:
            records = cached_info['records']
            rebuilds = cached_info['rebuilds']

        return records, rebuilds

