#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

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
import logging
import time
import argparse
try:
    import argcomplete
    _HAS_ARGCOMPLETE = True
except ImportError:
    _HAS_ARGCOMPLETE = False

try:
    import cProfile as profile
except ImportError:
    import profile

def _pathSetup():
    import sys
    path_to_this_file = os.path.realpath(__file__).split(os.path.sep)[:-2]
    vimhdl_path = os.path.sep.join(path_to_this_file)
    if vimhdl_path not in sys.path:
        sys.path.insert(0, vimhdl_path)

if __name__ == '__main__':
    _pathSetup()

from vimhdl.config import Config
from vimhdl.project_builder import ProjectBuilder

_logger = logging.getLogger(__name__)

def _fileExtentensionCompleter(extension):
    def _completer(**kwargs):
        prefix = kwargs['prefix']
        if prefix == '':
            prefix = os.curdir

        result = []
        for line in os.listdir(prefix):
            if line.lower().endswith('.' + extension):
                result.append(line)
            elif os.path.isdir(line):
                result.append("./" + line)

        return result
    return _completer


def parseArguments():
    parser = argparse.ArgumentParser()
    # pylint: disable=bad-whitespace

    # Options
    parser.add_argument('--verbose', '-v', action='append_const', const=1,
            help="""Increases verbose level. Use multiple times to
            increase more""")

    parser.add_argument('--clean', '-c', action='store_true',
            help="Cleans the project before building")

    parser.add_argument('--build', '-b', action='store_true',
            help="Builds the project given by <project_file>")

    parser.add_argument('--sources', '-s', action='append', nargs='*',
            help="""Source(s) file(s) to build individually""").completer \
                    = _fileExtentensionCompleter('vhd')

    # Debugging options
    parser.add_argument('--print-dependency-map', action='store_true',
            help = """Prints the dependency map of source file given by [source].
            If [source] was not supplied, prints the dependency map of all
            sources.""")

    parser.add_argument('--print-reverse-dependency-map', action='store_true',
            help = """Prints the reverse dependency map of source file given by
            [source]. If [source] was not supplied, prints the reverse dependency
            map of all sources.""")

    parser.add_argument('--print-design-units', action='store_true')
    parser.add_argument('--debug-print-build-steps', action='store_true')
    parser.add_argument('--debug-profiling', action='store', nargs='?',
            metavar='OUTPUT_FILENAME', const='vimhdl.pstats')

    # Mandatory arguments
    parser.add_argument('project_file', action='store', nargs=1,
            help="""Configuration file that defines what should be built (lists
            sources, libraries, build flags and so on""")

    # pylint: enable=bad-whitespace

    if _HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    args.project_file = args.project_file[0]

    args.log_level = logging.FATAL
    if args.verbose:
        if len(args.verbose) == 0:
            args.log_level = logging.FATAL
        elif len(args.verbose) == 1:
            args.log_level = logging.WARNING
        elif len(args.verbose) == 2:
            args.log_level = logging.INFO
        elif len(args.verbose) >= 3:
            args.log_level = logging.DEBUG

    # Planify source list if supplied
    if args.sources:
        args.sources = [source for sublist in args.sources for source in sublist]

    Config.log_level = args.log_level
    Config.setupBuild()

    return args

def main(args):
    "Main runner command processing"

    _logger.info("Creating project object")

    if args.clean:
        _logger.info("Cleaning up")
        ProjectBuilder.clean(args.project_file)

    project = ProjectBuilder(project_file=args.project_file)
    project.readConfigFile()

    if args.print_dependency_map:
        if args.sources:
            for source in args.sources:
                project.printDependencyMap(source)
        else:
            project.printDependencyMap()

    if args.print_reverse_dependency_map:
        if args.sources:
            for source in args.sources:
                project.printReverseDependencyMap(source)
        else:
            project.printReverseDependencyMap()

    if args.print_design_units:
        for source in args.sources:
            _, _source = project.getLibraryAndSourceByPath(source)
            for unit in _source.getDesignUnits():
                print unit

    if args.debug_print_build_steps:
        step_cnt = 0
        for step in project.getBuildSteps():
            step_cnt += 1
            if not step:
                break
            print "="*10 + (" Step %d " % step_cnt) + "="*10
            for lib_name, sources in step.iteritems():
                print "  - Library %s" % lib_name
                for source in sources:
                    print "    - %s" % source

    if args.build:
        if not args.sources:
            project.buildByDependency()
        else:
            for source in args.sources:
                try:
                    _logger.info("Building source '%s'", source)
                    for record in project.buildByPath(source):
                        print str(record)
                except RuntimeError as e:
                    _logger.error("Unable to build '%s': '%s'", source, str(e))
                    continue

    project.saveCache()


if __name__ == '__main__':
    start = time.time()
    args = parseArguments()
    if args.debug_profiling:
        profile.run('main(args)', args.debug_profiling)
    else:
        main(args)
    end = time.time()
    _logger.info("Process took %.2fs", (end - start))


