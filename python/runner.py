#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

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

import logging, os
import cPickle
from config import Config
from compilers import msim
from utils import findVhdsInPath
from project_builder import ProjectBuilder

_logger = logging.getLogger(__name__)

_LOG_LEVELS = {
    3 : logging.DEBUG,
    2 : logging.INFO,
    1 : logging.WARNING,
    0 : logging.ERROR
}


def parseArguments():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose',  '-v',  action='append_const',  const=1)
    parser.add_argument('--clean',    '-c',  action='store_true')
    parser.add_argument('--build',    '-b',  action='store_true')
    parser.add_argument('--target',   '-t',  action='store')

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args()
    if args.verbose:
        args.log_level = _LOG_LEVELS[len(args.verbose)]

    Config.updateFromArgparse(args)
    Config.setupBuild()

    return args.clean, args.build, args.target


SAVE_FILE = os.path.expanduser("~/temp/builder.project")

def main():
    #  clean, library, sources = parseArguments()
    clean, build, target = parseArguments()
    if clean:
        os.system('rm -rf ~/temp/builder ' + SAVE_FILE)

    if build or target:
        try:
            project = cPickle.load(open(SAVE_FILE, 'r'))
        except (IOError, EOFError):
            _logger.warning("Unable to recover save file")

            project = ProjectBuilder(builder=msim.MSim('~/temp/builder'))

            # pylint: disable=bad-whitespace
            for lib, path, flags in (
                    ('unisim',    '~/hdl_lib/unisim/',  '',),
                    ('osvvm_lib',    '~/hdl_lib/osvvm_lib/',      ('-2008',  )),
                    ('common_lib',   '~/hdl_lib/common_lib/',     ''),
                    ('pck_fio_lib',  '~/hdl_lib/pck_fio_lib',     ''),
                    ('memory',       '~/hdl_lib/memory/',         ''),
                    ('cordic',       '~/opencores/cordic/',       ''),
                    ('avs_aes_lib',  '~/opencores/avs_aes/',      ''),
                    ('work',         '~/opencores/gecko3/',       ''),
                    ('i2c',         '~/opencores/i2c/',          ('-2008',  )),
                    ('pcie_sg_dma',         '~/opencores/pcie_sg_dma/',  '',        ),
                    ('plasma',         '~/opencores/plasma/',       '',        ),
                ):
                if not project.hasLibrary(lib):
                    project.addLibrary(lib, findVhdsInPath(path))
                else:
                    project.addLibrarySources(lib, findVhdsInPath(path))
                for flag in flags:
                    project.addBuildFlags(lib, flag)

        #  project.build()
        project.buildByDependency()

        cPickle.dump(project, open(SAVE_FILE, 'w'))

if __name__ == '__main__':
    main()

