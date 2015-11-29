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

from vimhdl.config import Config

_logger = logging.getLogger(__name__)

class BaseCompiler(object):
    "Class that implements the base compiler flow"

    __metaclass__ = abc.ABCMeta

    # Shell accesses must be atomic
    _lock = Lock()

    def _setName(self, value):
        self.__builder_name__ = value
    def _getName(self):
        return self.__builder_name__

    __name__ = abc.abstractproperty(_setName, _getName)

    def __init__(self, target_folder):
        self._logger = logging.getLogger(__name__ + '.' + self.__builder_name__)
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

    @abc.abstractmethod
    def _createLibrary(self, library):
        """Callback called to create a library"""

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
        if source.abspath not in self._build_info_cache.keys():
            self._build_info_cache[source.abspath] = {
                'compile_time' : 0,
                'records' : [],
                'rebuilds' : [],
                }

        cached_info = self._build_info_cache[source.abspath]

        build = False
        if forced:
            build = True
            self._logger.info("Forcing build of %s", str(source))
        elif source.getmtime() > cached_info['compile_time']:
            build = True
            self._logger.info("Building %s because it's out of date", \
                    str(source))

        if build:
            # Build a set of unique flags and pass it as tuple
            build_flags = set()
            build_flags.update(source.flags)
            build_flags.update(flags)
            with self._lock:
                self._createLibrary(source)
                records, rebuilds = \
                        self._doBuild(source, flags=tuple(build_flags))

            for rebuild in rebuilds:
                if rebuild[0] == 'work':
                    rebuild[0] = source.library

            cached_info['records'] = records
            cached_info['rebuilds'] = rebuilds
            cached_info['compile_time'] = source.getmtime()

            if not Config.cache_error_messages and \
                    'E' in [x['error_type'] for x in records]:
                cached_info['compile_time'] = 0

            end = time.time()
            self._logger.debug("Compiling took %.2fs", (end - start))
        else:
            self._logger.debug("Nothing to do for %s", source)
            records = cached_info['records']
            rebuilds = cached_info['rebuilds']

        return records, rebuilds

from prettytable import PrettyTable
# TODO: Move this to a tests folder or something
def isRecordValid(record):
    is_valid = True

    t = PrettyTable(["field", "value", "status"])
    t.align['status'] = 'l'
    record_info = dict(zip(record.keys(), ' '*len(record)))

    # Error type check
    if record['error_type'] in ('E', 'W'):
        record_info['error_type'] = ''
    else:
        record_info['error_type'] = 'Invalid value'

    # Line number check
    try:
        int(record['line_number'])
        record_info['line_number'] = ''
    except Exception as e:
        if record['error_number'] not in ('vcom-11', 'vcom-13', 'vcom-19', 'vcom-7'):
            record_info['line_number'] = 'NOK: %s: %s' % (e.__class__.__name__, str(e))
            is_valid = False

    # Error number check
    if record['error_number'] is None:
        record_info['error_number'] = 'No error number found'
    else:
        _errors = []
        if record['error_number'] == ' ':
            _errors += ['ops...']
        for _d in record['error_number']:
            if _d in ('[', ']', '(', ')'):
                _errors += ['invalid char: ' + _d]
                break
        if _errors:
            record_info['error_number'] = "NOK: " + ", ".join(_errors)
            is_valid = False

    # Error message check
    _errors = []
    if record['error_message'] == '':
        _errors += ['empty']
    if type(record['error_message']) is not str:
        _errors += ['not string']

    if _errors:
        record_info['error_message'] = "NOK: " + ", ".join(_errors)
        is_valid = False

    # Filename check
    if record['error_number'] not in ('vcom-11', 'vcom-13', 'vcom-19', 'vcom-7'):
        _errors = []
        if record['filename'] == '':
            _errors += ['empty']
        if type(record['filename']) is not str:
            _errors += ['not string']
        else:
            if 'souto' in record['filename']:
                if not os.path.isfile(record['filename']):
                    _errors += ['file %s should exist!' % repr(record['filename'])]

        if _errors:
            record_info['filename'] = "NOK: " + ", ".join(_errors)
            is_valid = False


    for k, v in record.items():
        if len(str(v)) > 80:
            v = str(v)[:80] + '...'
        info = record_info[k]
        if len(str(info)) > 80:
            info = str(info)[:80] + '...'
        t.add_row([k, v, info])

    if not is_valid:
        print t

    return is_valid

