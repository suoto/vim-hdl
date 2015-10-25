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

import os
import re
import subprocess
from vimhdl.compilers.base_compiler import BaseCompiler
from vimhdl.utils import shell
from vimhdl import exceptions

_RE_LIB_DOT_UNIT = re.compile(r"\b\w+\.\w+\b")

_RE_ERROR = re.compile(r"^\*\*\sError:", flags=re.I)
_RE_WARNING = re.compile(r"^\*\*\sWarning:", flags=re.I)

VLIB_ARGS = ['-type', 'directory']

def _lineHasError(line):
    "Parses <line> and return True or False if it contains an error"
    if '(vcom-11)' in line:
        return False
    if _RE_ERROR.match(line):
        return True
    return False

def _lineHasWarning(line):
    "Parses <line> and return True or False if it contains a warning"
    if _RE_WARNING.match(line):
        return True
    return False

def _getRebuildUnits(line):
    "Finds units that the compilers is telling us to rebuild"
    rebuilds = []
    if '(vcom-13)' in line:
        rebuilds = [x.split('.') for x in re.findall(
            r"(?<=recompile)\s*(\w+\.\w+)", line, flags=re.I)
        ]
    return rebuilds


class MSim(BaseCompiler):
    """Implementation of the ModelSim compiler"""

    _BuildMessageScanner = re.compile('|'.join([
                r"^\*\*\s*([WE])\w+:\s*",
                r"\((\d+)\):",
                r"[\[\(]([\w-]+)[\]\)]\s*",
                r"(.*\.(vhd|sv|svh)\b)",
                r"\s*\(([\w-]+)\)",
                r"(.+)",
                ]), re.I)

    _BuildIgnoredLines = re.compile('|'.join([
        r"^\s*$",
        r"^[^\*][^\*]",
        #  r".*VHDL Compiler exiting\s*$",
    ]))

    def __init__(self, target_folder):
        super(MSim, self).__init__(target_folder)
        self._modelsim_ini = os.path.join(self._target_folder, 'modelsim.ini')

        # FIXME: Built-in libraries should not be statically defined
        # like this. Review this at some point
        self.builtin_libraries = ['ieee', 'std', 'unisim', 'xilinxcorelib',
                'synplify', 'synopsis', 'maxii', 'family_support']

    def _makeMessageRecord(self, line):
        line_number = None
        column = None
        filename = None
        error_number = None
        error_type = None
        error_message = None

        scan = self._BuildMessageScanner.scanner(line)

        while True:
            match = scan.match()
            if not match:
                break

            if match.lastindex == 1:
                error_type = match.group(match.lastindex)
            if match.lastindex == 2:
                line_number = match.group(match.lastindex)
            if match.lastindex in (3, 6):
                error_number = match.group(match.lastindex)
            if match.lastindex == 4:
                filename = match.group(match.lastindex)
            if match.lastindex == 7:
                error_message = match.group(match.lastindex)

        return {
            'line_number'    : line_number,
            'column'         : column,
            'filename'       : filename,
            'error_number'   : error_number,
            'error_type'     : error_type,
            'error_message'  : error_message,
        }

    def _checkEnvironment(self):
        try:
            version = subprocess.check_output(['vcom', '-version'],
                stderr=subprocess.STDOUT)
            self._logger.info("vcom version string: '%s'", version[:-1])
        except Exception as exc:
            self._logger.fatal("Sanity check failed")
            raise exceptions.SanityCheckError(str(exc))

    def _doBuild(self, library, source, flags=None):
        if flags:
            flags += self._getBuildFlags(library, source)
        else:
            flags = self._getBuildFlags(library, source)

        cmd = ['vcom', '-modelsimini', self._modelsim_ini,
                '-work', os.path.join(self._target_folder, library)]
        cmd += flags
        cmd += [source.filename]

        self._logger.debug(" ".join(cmd))

        try:
            result = list(subprocess.check_output(cmd,
                stderr=subprocess.STDOUT).split("\n"))
        except subprocess.CalledProcessError as exc:
            result = list(exc.output.split("\n"))
        return result

    def createOrMapLibrary(self, library):
        if os.path.exists(os.path.join(self._target_folder, library)):
            return
        if os.path.exists(self._modelsim_ini):
            self.mapLibrary(library)
        else:
            self.createLibrary(library)

    def _preBuild(self, library, source):
        return self.createOrMapLibrary(library)

    def _postBuild(self, library, source, stdout):
        errors = []
        warnings = []
        rebuilds = []
        for line in stdout:
            if self._BuildIgnoredLines.match(line):
                continue
            if _lineHasError(line):
                errors.append(line)
            if _lineHasWarning(line):
                warnings.append(line)

            self._logger.info("Parsing '%s'", repr(line))
            record = self._makeMessageRecord(line)

            rebuilds += _getRebuildUnits(line)

        if errors:
            self._logger.debug("Messages for (%s) %s:", library, source)
            for msg in errors + warnings:
                self._logger.debug(msg)
        return errors, warnings, rebuilds

    def createLibrary(self, library):
        self._logger.info("Library %s not found, creating", library)
        shell('cd {target_folder} && vlib {vlib_args} {library}'.format(
            target_folder=self._target_folder,
            library=os.path.join(self._target_folder, library),
            vlib_args=" ".join(VLIB_ARGS)
            ))
        shell('cd {target_folder} && vmap {library} {library_path}'.format(
            target_folder=self._target_folder,
            library=library,
            library_path=os.path.join(self._target_folder, library)))

    def deleteLibrary(self, library):
        if not os.path.exists(os.path.join(self._target_folder, library)):
            self._logger.warning("Library %s doesn't exists", library)
            return
        shell('vdel -modelsimini {modelsimini} -lib {library} -all'.format(
            modelsimini=self._modelsim_ini, library=library
            ))

    def mapLibrary(self, library):
        self._logger.info("modelsim.ini found, adding %s", library)

        shell('vlib {vlib_args} {library}'.format(
            vlib_args=" ".join(VLIB_ARGS),
            library=os.path.join(self._target_folder, library)))
        shell('vmap -modelsimini {modelsimini} {library} {library_path}'.format(
            modelsimini=self._modelsim_ini,
            library=library,
            library_path=os.path.join(self._target_folder, library)))

