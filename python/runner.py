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

import logging
import os
try:
    import cPickle as pickle
except ImportError:
    import pickle
import ConfigParser
from config import Config
from compilers import msim
from project_builder import ProjectBuilder

_logger = logging.getLogger(__name__)

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
    parser.add_argument('--threads',      '-m',  action='store', default=10, type=int)
    # pylint: enable=bad-whitespace

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args()
    if args.verbose:
        if len(args.verbose) == 0:
            args.log_level = logging.ERROR
        elif len(args.verbose) == 1:
            args.log_level = logging.WARNING
        elif len(args.verbose) == 2:
            args.log_level = logging.INFO
        elif len(args.verbose) == 3:
            args.log_level = logging.DEBUG
        else:
            args.log_level = logging.INFO


    Config.updateFromArgparse(args)
    Config.setupBuild()

    return args

def main():
    args = parseArguments()

    project = ProjectBuilder(library_file=args.library_file, builder=msim.MSim('~/temp/builder'))

    if args.clean:
        project.cleanCache()

    if args.build:
        if args.threads:
            project.buildByDependencyWithThreads()
        else:
            project.buildByDependency()

    if args.target:
        project.buildByPath(args.target)

if __name__ == '__main__':
    main()

