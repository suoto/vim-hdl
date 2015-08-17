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
    for l in os.popen(cmd).read().split("\n"):
        if re.match(r"^\s*$", l):
            continue
        _logger.debug(l)


class BaseCompiler(object):
    def __init__(self, target_folder):
        self._TARGET_FOLDER = os.path.expanduser(target_folder)
        self._MODELSIM_INI = os.path.join(self._TARGET_FOLDER, 'modelsim.ini')

        if not os.path.exists(self._TARGET_FOLDER):
            os.mkdir(self._TARGET_FOLDER)

        os.chdir(self._TARGET_FOLDER)
        self._logger = logging.getLogger(__name__)

        self._re_error = re.compile(r"^\*\*\sError:", flags=re.I)
        self._re_warning = re.compile(r"^\*\*\sWarning:", flags=re.I)

    def createLibrary(self, library):
        self._logger.info("Library %s not found, creating", library)
        shell('vlib {library}'.format(library=os.path.join(self._TARGET_FOLDER, library)))
        shell('vmap {library} {library_path}'.format(
            library=library, library_path=os.path.join(self._TARGET_FOLDER, library)))
    def mapLibrary(self, library):
        self._logger.info("Library %s found, mapping", library)

        shell('vlib {library}'.format(library=os.path.join(self._TARGET_FOLDER, library)))
        shell('vmap -modelsimini {modelsimini} {library} {library_path}'.format(
            modelsimini=self._MODELSIM_INI, library=library, library_path=os.path.join(self._TARGET_FOLDER, library)))
    def preBuild(self, library, source):
        if os.path.exists(os.path.join(self._TARGET_FOLDER, library)):
            return
        if os.path.exists(self._MODELSIM_INI):
            self.mapLibrary(library)
        else:
            self.createLibrary(library)
    def postBuild(self, library, source, stdout):
        errors = warnings = []
        for l in stdout.split("\n"):
            if re.match(r"^\s*$", l):
                continue
            self._logger.debug(l)
            errors += self.getErrors(l)
            warnings += self.getWarnings(l)
        return errors, warnings
    def getErrors(self, l):
        if self._re_error.match(l):
            #  self._logger.error(l)
            return [l]
        return []
    def getWarnings(self, l):
        if self._re_warning.match(l):
            #  self._logger.warning(l)
            return [l]
        return []
    def getFlags(self, library, source):
        return []
    def _doBuild(self, library, source, flags=None):
        if flags:
            flags += self.getFlags(library, source)
        else:
            flags = self.getFlags(library, source)

        cmd = 'vcom -modelsimini {modelsimini} -work {library} {flags} {source}'.format(
            modelsimini=self._MODELSIM_INI, library=os.path.join(self._TARGET_FOLDER, library), flags=" ".join(flags),
            source=source)

        self._logger.debug(cmd)
        return os.popen(cmd).read()
    def _doBatchBuild(self, library, sources, flags=None):
        if flags:
            flags += self.getFlags(library, sources)
        else:
            flags = self.getFlags(library, sources)

        cmd = 'vcom -modelsimini {modelsimini} -work {library} {flags} {source}'.format(
            modelsimini=self._MODELSIM_INI, library=os.path.join(self._TARGET_FOLDER, library), flags=" ".join(flags),
            source=" ".join(sources))

        self._logger.debug(cmd)
        return os.popen(cmd).read()

    def build(self, library, source, flags=None):
        self.preBuild(library, source)
        stdout = self._doBuild(library, source, flags)
        return self.postBuild(library, source, stdout)
    def buildPackages(self, library, source, flags=None):
        if flags:
            flags += ['-just p']
        else:
            flags = ['-just p']
        return self._doBatchBuild(library, source, flags)
    def buildAllButPakcages(self, library, source, flags=None):
        if flags:
            flags += ['-skip p']
        else:
            flags = ['-skip p']
        return self._doBatchBuild(library, source, flags)
    def batchBuild(self, library, source, flags=None):
        self.preBuild(library, source)
        stdout = ''
        stdout += self.buildPackages(library, source, flags)
        stdout += self.buildAllButPakcages(library, source, flags)
        return self.postBuild(library, source, stdout)

