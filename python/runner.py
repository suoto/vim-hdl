#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

# This file is part of hdl-check-o-matic.
#
# hdl-check-o-matic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# hdl-check-o-matic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hdl-check-o-matic.  If not, see <http://www.gnu.org/licenses/>.

import logging, os
import cPickle
from config import Config
from compilers import msim
from utils import readLibrariesFromFile
from project_builder import ProjectBuilder

_logger = logging.getLogger(__name__)

_LOG_LEVELS = {
    3 : logging.DEBUG,
    2 : logging.INFO,
    1 : logging.WARNING,
    0 : logging.ERROR
}


SAVE_FILE = os.path.expanduser("~/temp/builder.project")

def parseArguments():
    import argparse
    parser = argparse.ArgumentParser()
    # pylint: disable=bad-whitespace
    parser.add_argument('--verbose',      '-v',  action='append_const',  const=1)
    parser.add_argument('--clean',        '-c',  action='store_true')
    parser.add_argument('--build',        '-b',  action='store_true')
    parser.add_argument('--library-file', '-l',  action='store')
    parser.add_argument('--target',       '-t',  action='store')
    parser.add_argument('--threads',      '-m',  action='store', default=10)
    # pylint: enable=bad-whitespace

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

    return args

def main():
    args = parseArguments()

    if args.clean:
        os.system('rm -rf ~/temp/builder ' + SAVE_FILE)

    if args.library_file:
        try:
            project = cPickle.load(open(SAVE_FILE, 'r'))
        except (IOError, EOFError):
            _logger.info("Unable to recover save file")

            project = ProjectBuilder(builder=msim.MSim('~/temp/builder'))

            for lib_name, sources, flags in readLibrariesFromFile(args.library_file):
                if lib_name not in project.libraries.keys():
                    project.addLibrary(lib_name, sources)
                else:
                    project.addLibrarySources(lib_name, sources)
                if flags:
                    project.addBuildFlags(lib_name, flags)

    if args.build:
        if args.threads:
            project.buildByDependencyWithThreads()
        else:
            project.buildByDependency()

        cPickle.dump(project, open(SAVE_FILE, 'w'))

    if args.target:
        project.buildByPath(args.target)

if __name__ == '__main__':
    main()

