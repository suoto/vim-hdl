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

import logging, os, re
import subprocess

_logger = logging.getLogger(__name__)

def _is_vhd(p):
    return os.path.basename(p).lower().endswith('vhd')

def _is_makefile(f):
    return os.path.basename(f) == 'Makefile'

def shell(cmd):
    """
    Dummy wrapper for running shell commands, checking the return value and logging
    """

    _logger.debug(cmd)
    for l in subprocess.check_output(cmd, shell=True).split("\n"):
        if re.match(r"^\s*$", l):
            continue
        _logger.debug(l)


class BaseCompiler(object):
    def __init__(self, target_folder):
        self._logger = logging.getLogger(__name__)
        self._TARGET_FOLDER = os.path.abspath(os.path.expanduser(target_folder))
        self._MODELSIM_INI = os.path.join(self._TARGET_FOLDER, 'modelsim.ini')

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

    def _doBuild(self, library, source, flags=None):
        if flags:
            flags += self.getBuildFlags(library, source)
        else:
            flags = self.getBuildFlags(library, source)

        cmd = 'vcom -modelsimini {modelsimini} -work {library} {flags} {source}'.format(
            modelsimini=self._MODELSIM_INI, library=os.path.join(self._TARGET_FOLDER, library), flags=" ".join(flags),
            source=source)

        self._logger.debug(cmd)
        return os.popen(cmd).read().split("\n")
    def _doBatchBuild(self, library, sources, flags=None):
        if flags:
            flags += self.getBuildFlags(library, sources)
        else:
            flags = self.getBuildFlags(library, sources)

        cmd = 'vcom -modelsimini {modelsimini} -work {library} {flags} {sources}'.format(
            modelsimini=self._MODELSIM_INI, library=os.path.join(self._TARGET_FOLDER, library), flags=" ".join(flags),
            sources=" ".join(sources))

        self._logger.debug(cmd)
        return os.popen(cmd).read().split("\n")
    def _lineHasError(self, l):
        if self._re_error.match(l):
            return True
        return False
    def _lineHasWarning(self, l):
        if self._re_warning.match(l):
            return True
        return False
    def createOrMapLibrary(self, library):
        if os.path.exists(os.path.join(self._TARGET_FOLDER, library)):
            return
        if os.path.exists(self._MODELSIM_INI):
            self.mapLibrary(library)
        else:
            self.createLibrary(library)

    def _preBuild(self, library, source):
        return self.createOrMapLibrary(library)
    def _postBuild(self, library, source, stdout):
        errors = []
        warnings = []
        for l in stdout:
            if self._re_ignored.match(l):
                continue
            self._logger.debug(l)
            if self._lineHasError(l):
                errors.append(l)
            if self._lineHasWarning(l):
                warnings.append(l)
        return errors, warnings
    def createLibrary(self, library):
        self._logger.info("Library %s not found, creating", library)
        shell('cd {target_folder} && vlib {library}'.format(target_folder=self._TARGET_FOLDER, library=os.path.join(self._TARGET_FOLDER, library)))
        shell('cd {target_folder} && vmap {library} {library_path}'.format(
            target_folder=self._TARGET_FOLDER,
            library=library, library_path=os.path.join(self._TARGET_FOLDER, library)))
    def mapLibrary(self, library):
        self._logger.info("Library %s found, mapping", library)

        shell('vlib {library}'.format(library=os.path.join(self._TARGET_FOLDER, library)))
        shell('vmap -modelsimini {modelsimini} {library} {library_path}'.format(
            modelsimini=self._MODELSIM_INI, library=library, library_path=os.path.join(self._TARGET_FOLDER, library)))
    def getBuildFlags(self, library, source):
        return []
    def build(self, library, source, flags=None):
        source = os.path.relpath(str(source))
        self._preBuild(library, source)
        stdout = self._doBuild(library, source, flags)
        return self._postBuild(library, source, stdout)
    def batchBuild(self, library, sources, flags=None):
        self._preBuild(library, sources)
        stdout = self._doBatchBuild(library, sources, flags)
        errors, warnings = self._postBuild(library, sources, stdout)
        if not errors:
            return errors, warnings
        errors = []
        warnings = []
        for source in sources:
            _errors, _warnings = self.build(library, source, flags)
            errors.append(_errors)
            warnings.append(_warnings)
        return errors, warnings


