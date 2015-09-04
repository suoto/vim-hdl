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

import logging, os, re
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


SAVE_FILE = os.path.expanduser("~/temp/builder.project")

def parseArguments():
    import argparse
    parser = argparse.ArgumentParser()
    # pylint: disable=bad-whitespace
    parser.add_argument('--verbose',       '-v',  action='append_const',  const=1)
    parser.add_argument('--clean',         '-c',  action='store_true')
    parser.add_argument('--build',         '-b',  action='store_true')
    parser.add_argument('--library-file',  '-l',  action='store')
    parser.add_argument('--target',        '-t',  action='store')
    parser.add_argument('--threads',       '-m',  action='store', default=10)
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

_RE_LIBRARY_NAME = re.compile(r"(?<=\[)\w+(?=\])")
_RE_COMMENTS = re.compile(r"\s*#.*$")
_RE_BLANK_LINE = re.compile(r"^\s*$")

def _readLibrariesFromFile(filename):
    library = ''
    for line in open(filename, 'r').read().split("\n"):
        line = _RE_COMMENTS.sub("", line)
        if _RE_BLANK_LINE.match(line):
            continue

        if re.match(r"^\s*\[\w+\]", line):
            library = _RE_LIBRARY_NAME.findall(line)
            library = library[0]
        else:
            yield library, re.sub(r"^\s*|\s*$", "", line)

def main():
    args = parseArguments()

    if args.clean:
        os.system('rm -rf ~/temp/builder ' + SAVE_FILE)

    if args.build or args.target:
        try:
            project = cPickle.load(open(SAVE_FILE, 'r'))
        except (IOError, EOFError):
            _logger.info("Unable to recover save file")

            project = ProjectBuilder(builder=msim.MSim('~/temp/builder'))

            for lib_name, sources in _readLibrariesFromFile(args.library_file):
                if lib_name not in project.libraries.keys():
                    project.addLibrary(lib_name, sources)
                else:
                    project.addLibrarySources(lib_name, sources)

        if args.threads:
            project.buildByDependencyWithThreads()
        else:
            project.buildByDependency()

        cPickle.dump(project, open(SAVE_FILE, 'w'))

if __name__ == '__main__':
    main()

