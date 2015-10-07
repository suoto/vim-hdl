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

import os, re
from compilers.base_compiler import BaseCompiler
from utils import shell
import subprocess

_RE_LIB_DOT_UNIT = re.compile(r"\b\w+\.\w+\b")

_RE_ERROR = re.compile(r"^\*\*\sError:", flags=re.I)
_RE_WARNING = re.compile(r"^\*\*\sWarning:", flags=re.I)
_RE_IGNORED = re.compile('|'.join([
    r"^\s*$",
    r".*Unknown expanded name.\s*$",
    r".*VHDL Compiler exiting\s*$",
]))

VLIB_ARGS = ['-unix', '-type', 'directory']

class MSim(BaseCompiler):
    def __init__(self, target_folder):
        super(MSim, self).__init__(target_folder)
        self._MODELSIM_INI = os.path.join(self._TARGET_FOLDER, 'modelsim.ini')

    def _doBuild(self, library, source, flags=None):
        if flags:
            flags += self.getBuildFlags(library, source)
        else:
            flags = self.getBuildFlags(library, source)

        cmd = ['vcom', '-modelsimini', self._MODELSIM_INI, '-work', os.path.join(self._TARGET_FOLDER, library)]
        cmd += flags
        cmd += [source.filename]

        self._logger.debug(" ".join(cmd))

        try:
            result = list(subprocess.check_output(cmd, stderr=subprocess.STDOUT).split("\n"))
        except subprocess.CalledProcessError as exc:
            result = list(exc.output.split("\n"))
        return result

    def _doBatchBuild(self, library, sources, flags=None):
        if flags:
            flags += self.getBuildFlags(library, sources)
        else:
            flags = self.getBuildFlags(library, sources)

        cmd = 'vcom -modelsimini {modelsimini} -work {library} {flags} {sources}'.format(
            modelsimini=self._MODELSIM_INI,
            library=os.path.join(self._TARGET_FOLDER, library),
            flags=" ".join(flags),

            sources=" ".join(sources))

        self._logger.debug(cmd)
        return os.popen(cmd).read().split("\n")

    def _lineHasError(self, l):
        if '(vcom-11)' in l:
            return False
        if _RE_ERROR.match(l):
            return True
        return False

    def _lineHasWarning(self, l):
        if _RE_WARNING.match(l):
            return True
        return False

    def _getRebuildUnits(self, l):
        if '(vcom-13)' not in l:
            return []
        return [x.split('.') for x in _RE_LIB_DOT_UNIT.findall(l)]

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
        rebuilds = []
        for l in stdout:
            if _RE_IGNORED.match(l):
                continue
            if self._lineHasError(l):
                errors.append(l)
            if self._lineHasWarning(l):
                warnings.append(l)
            rebuilds += self._getRebuildUnits(l)

        if errors:
            self._logger.debug("Messages for (%s) %s:", library, source)
            for msg in errors + warnings:
                self._logger.debug(msg)
        return errors, warnings, rebuilds

    def createLibrary(self, library):
        self._logger.info("Library %s not found, creating", library)
        shell('cd {target_folder} && vlib {vlib_args} {library}'.format(
            target_folder=self._TARGET_FOLDER,
            library=os.path.join(self._TARGET_FOLDER, library),
            vlib_args=" ".join(VLIB_ARGS)
            ))
        shell('cd {target_folder} && vmap {library} {library_path}'.format(
            target_folder=self._TARGET_FOLDER,
            library=library,
            library_path=os.path.join(self._TARGET_FOLDER, library)))

    def deleteLibrary(self, library):
        if not os.path.exists(os.path.join(self._TARGET_FOLDER, library)):
            self._logger.warning("Library %s doesn't exists", library)
            return
        shell('vdel -modelsimini {modelsimini} -lib {library} -all'.format(
            modelsimini=self._MODELSIM_INI, library=library
            ))

    def mapLibrary(self, library):
        self._logger.info("modelsim.ini found, adding %s", library)

        shell('vlib {vlib_args} {library}'.format(
            vlib_args=" ".join(VLIB_ARGS),
            library=os.path.join(self._TARGET_FOLDER, library)))
        shell('vmap -modelsimini {modelsimini} {library} {library_path}'.format(
            modelsimini=self._MODELSIM_INI,
            library=library,
            library_path=os.path.join(self._TARGET_FOLDER, library)))

    def getBuildFlags(self, library, source):
        return []

    def build(self, library, source, flags=None):
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


