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

import logging
import time

from config import Config
from project_builder import ProjectBuilder

_logger = logging.getLogger(__name__)

def parseArguments():
    import argparse
    parser = argparse.ArgumentParser()
    # pylint: disable=bad-whitespace
    parser.add_argument('--verbose',      '-v', action='append_const', const=1)
    parser.add_argument('--clean',        '-c', action='store_true')
    parser.add_argument('--build',        '-b', action='store_true')
    parser.add_argument('--library-file', '-l', action='store')
    parser.add_argument('--target',       '-t', action='store')
    parser.add_argument('--threads',      '-m', action='store_true', default=False)

    # Debugging options
    parser.add_argument('--print-dependency-map',
            action='store_true', default=False)
    parser.add_argument('--print-reverse-dependency-map',
            action='store_true', default=False)
    parser.add_argument('--print-design-units',   action='store', default=False)
    # pylint: enable=bad-whitespace

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args()
    args.log_level = logging.FATAL
    if args.verbose:
        if len(args.verbose) == 0:
            args.log_level = logging.FATAL
        elif len(args.verbose) == 1:
            args.log_level = logging.WARNING
        elif len(args.verbose) == 2:
            args.log_level = logging.INFO
        elif len(args.verbose) == 3:
            args.log_level = logging.DEBUG
        else:
            args.log_level = logging.ERROR


    Config.updateFromArgparse(args)
    Config.setupBuild()

    return args

def main():
    args = parseArguments()

    _logger.info("Creating project object")

    if args.clean:
        _logger.info("Cleaning up")
        ProjectBuilder.clean(args.library_file)

    project = ProjectBuilder(library_file=args.library_file)

    if args.print_dependency_map:
        for lib_name, lib_deps in project._getDependencyMap().iteritems():
            print "Library %s" % lib_name
            for src, src_deps in lib_deps.iteritems():
                if src_deps:
                    print " - %s: %s" % (src, ", ".join(["%s.%s" % (x[0], x[1]) \
                            for x in src_deps]))
                else:
                    print " - %s: None" % src

    if args.print_reverse_dependency_map:
        for (lib_name, design_unit), deps in project._getReverseDependencyMap().iteritems():
            _s =  "- %s.%s: " % (lib_name, design_unit)
            if deps:
                _s += " ".join(deps)
            else:
                _s += "None"
            print _s
        #  for lib_name, lib_deps in project._getDependencyMap().iteritems():
        #      print lib_name
        #      for src, src_deps in lib_deps.iteritems():
        #          if src_deps:
        #              print " - %s: %s" % (src, ", ".join(["%s.%s" % (x[0], x[1]) \
        #                      for x in src_deps]))
        #          else:
        #              print " - %s: None" % src

    if args.print_design_units:
        for unit in project.getDesignUnitsByPath(args.print_design_units):
            print unit

    if args.build:
        if args.threads:
            _logger.info("Building with threads")
            project.buildByDependencyWithThreads()
        else:
            _logger.info("Building without threads")
            project.buildByDependency()

    if args.target:
        _logger.info("Building target '%s'", args.target)
        project.buildByPath(args.target)

if __name__ == '__main__':
    start = time.time()
    main()
    end = time.time()
    _logger.info("Process took %.2fs", (end - start))


