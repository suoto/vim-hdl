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

_logger = logging.getLogger(__name__)

class abstractstaticmethod(staticmethod):
    __slots__ = ()
    def __init__(self, function):
        super(abstractstaticmethod, self).__init__(function)
        function.__isabstractmethod__ = True
    __isabstractmethod__ = True

class BaseCompiler(object):
    "Class that implements the base compiler flow"

    __metaclass__ = abc.ABCMeta

    def __init__(self, target_folder):
        self._logger = logging.getLogger(__name__)
        self._target_folder = os.path.abspath(os.path.expanduser(target_folder))

        self.builtin_libraries = []

        if not os.path.exists(self._target_folder):
            self._logger.info("%s doens't exists", self._target_folder)
            os.mkdir(self._target_folder)
        else:
            self._logger.info("%s already exists", self._target_folder)

        self._checkEnvironment()

    @abstractstaticmethod
    def _makeMessageRecord(message):
        """Static method that converts a string into a dict that has
        elements identifying its fields"""

    @abc.abstractmethod
    def _checkEnvironment(self):
        """Sanity environment check that should be implemented by child
        classes. Nothing is done with the return, the child class should
        raise an exception by itself"""

    @abc.abstractmethod
    def _preBuild(self, library, source):
        """Callback called before building anything. Usually to create
        stuff needed by the compiler (library, clean up, checking,
        etc"""

    @abc.abstractmethod
    def _doBuild(self, library, source, flags=None):
        """Callback called to actually build the source"""

    @abc.abstractmethod
    def _postBuild(self, library, source, stdout):
        """Callback to process output to stdout by the compiler.
        Use this to parse the output and find errors and warnings
        issued"""

    def _getBuildFlags(self, library, source):
        "Holds compiler based build flags"
        return []

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, state):
        self._logger = logging.getLogger(state['_logger'])
        del state['_logger']
        self.__dict__.update(state)

    def build(self, library, source, flags=None):
        """Method that interfaces with parents and implements the
        building chain"""
        start = time.time()
        self._preBuild(library, source)
        stdout = self._doBuild(library, source, flags)
        result = self._postBuild(library, source, stdout)
        end = time.time()
        self._logger.debug("Compiling took %.2fs", (end - start))
        return result

