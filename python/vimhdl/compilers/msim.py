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
"ModelSim builder implementation"

import os
import re
import subprocess
from vimhdl.compilers.base_compiler import BaseCompiler
from vimhdl.utils import shell
from vimhdl import exceptions

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

class MSim(BaseCompiler):
    """Implementation of the ModelSim compiler"""
    _BuilderStdoutMessageScanner = re.compile('|'.join([
                r"^\*\*\s*([WE])\w+:\s*",
                r"\((\d+)\):",
                r"[\[\(]([\w-]+)[\]\)]\s*",
                r"(.*\.(vhd|sv|svh)\b)",
                r"\s*\(([\w-]+)\)",
                r"\s*(.+)",
                ]), re.I)

    _BuilderStdoutIgnoreLines = re.compile('|'.join([
        r"^\s*$",
        r"^(?!\*\*\s(Error|Warning):).*",
        r".*VHDL Compiler exiting\s*$",
    ]))

    _BuilderRebuildUnitsScanner = re.compile(
            r"Recompile\s*([^\s]+)\s+because\s+[^\s]+\s+has changed")

    def __init__(self, target_folder):
        self._version = ''
        super(MSim, self).__init__(target_folder)
        self._modelsim_ini = os.path.join(self._target_folder, 'modelsim.ini')

        # FIXME: Built-in libraries should not be statically defined
        # like this. Review this at some point
        self.builtin_libraries = ['ieee', 'std', 'unisim', 'xilinxcorelib',
                'synplify', 'synopsis', 'maxii', 'family_support']

        # FIXME: Check ModelSim changelog to find out which version
        # started to support 'vlib -type directory' flags. We know
        # 10.3a accepts and 10.1a doesn't. ModelSim 10.3a reference
        # manual mentions 3 library formats (6.2-, 6.3 to 10.2, 10.2+)
        if self._version >= '10.2':
            self._vlib_args = ['-type', 'directory']
        else:
            self._vlib_args = []
        self._logger.debug("vlib arguments: '%s'", str(self._vlib_args))


    def _makeMessageRecord(self, line):
        line_number = None
        column = None
        filename = None
        error_number = None
        error_type = None
        error_message = None

        scan = self._BuilderStdoutMessageScanner.scanner(line)

        while True:
            match = scan.match()
            if not match:
                break

            if match.lastindex == 1:
                error_type = match.group(match.lastindex)
            if match.lastindex == 2:
                line_number = match.group(match.lastindex)
            if match.lastindex in (3, 6):
                try:
                    error_number = \
                            re.findall(r"\d+", match.group(match.lastindex))[0]
                except IndexError:
                    error_number = 0
            if match.lastindex == 4:
                filename = match.group(match.lastindex)
            if match.lastindex == 7:
                error_message = match.group(match.lastindex)

        return {
            'checker'        : 'msim',
            'line_number'    : line_number,
            'column'         : column,
            'filename'       : filename,
            'error_number'   : error_number,
            'error_type'     : error_type,
            'error_message'  : error_message,
        }

    def _checkEnvironment(self):
        try:
            version = subprocess.check_output(['vcom', '-version'], \
                stderr=subprocess.STDOUT)
            self._version = \
                    re.findall(r"(?<=vcom)\s+([\w\.]+)\s+(?=Compiler)", \
                    version)[0]
            self._logger.info("vcom version string: '%s'. " + \
                    "Version number is '%s'", \
                    version[:-1], self._version)
        except Exception as exc:
            self._logger.fatal("Sanity check failed")
            raise exceptions.SanityCheckError(str(exc))

    def _getUnitsToRebuild(self, line):
        "Finds units that the compilers is telling us to rebuild"
        rebuilds = []
        if '(vcom-13)' in line:
            for match in self._BuilderRebuildUnitsScanner.finditer(line):
                if not match:
                    continue
                rebuilds.append(match.group(match.lastindex).split('.'))

        return rebuilds

    def _doBuild(self, source, flags=None):
        cmd = ['vcom', '-modelsimini', self._modelsim_ini, '-work', \
                os.path.join(self._target_folder, source.library)]
        cmd += flags
        cmd += [source.filename]

        self._logger.debug(" ".join(cmd))

        try:
            stdout = list(subprocess.check_output(cmd, \
                    stderr=subprocess.STDOUT).split("\n"))
        except subprocess.CalledProcessError as exc:
            stdout = list(exc.output.split("\n"))

        rebuilds = []
        records = []

        for line in stdout:
            if self._BuilderStdoutIgnoreLines.match(line):
                continue
            records.append(self._makeMessageRecord(line))

            #  if not isRecordValid(records[-1]):
            #      self._logger.error("Error parsing %s", repr(line))

            rebuilds += self._getUnitsToRebuild(line)

        return records, rebuilds

    def _createLibrary(self, source):
        if os.path.exists(os.path.join(self._target_folder, source.library)):
            return
        if os.path.exists(self._modelsim_ini):
            self._mapLibrary(source.library)
        else:
            self._addLibraryToIni(source.library)

    def _addLibraryToIni(self, library):
        self._logger.info("Library %s not found, creating", library)
        shell('cd {target_folder} && vlib {vlib_args} {library}'.format(
            target_folder=self._target_folder,
            library=os.path.join(self._target_folder, library),
            vlib_args=" ".join(self._vlib_args)
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

    def _mapLibrary(self, library):
        self._logger.info("modelsim.ini found, adding %s", library)

        shell('vlib {vlib_args} {library}'.format(
            vlib_args=" ".join(self._vlib_args),
            library=os.path.join(self._target_folder, library)))
        shell('vmap -modelsimini {modelsimini} {library} {library_path}'.format(
            modelsimini=self._modelsim_ini,
            library=library,
            library_path=os.path.join(self._target_folder, library)))

