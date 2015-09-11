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

import os, re, logging, subprocess

_logger = logging.getLogger(__name__)

def shell(cmd):
    """Dummy wrapper for running shell commands, checking the return value and
    logging"""

    _logger.debug(cmd)
    for l in subprocess.check_output(cmd, shell=True).split("\n"):
        if re.match(r"^\s*$", l):
            continue
        _logger.debug(l)

def touch(arg):
    open(str(arg), 'a').close()

def findFilesInPath(path, f, recursive=True):
    """Finds files that match f(_file_), where _file_ is the relative path to
    the item found."""
    path = os.path.expanduser(path)
    if recursive:
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                relpath_to_filename = os.path.sep.join([dirpath, filename])
                if f(relpath_to_filename):
                    yield os.path.normpath(relpath_to_filename)
    else:
        for l in os.listdir(path):
            l = os.path.sep.join([path, l])
            if not os.path.isfile(l):
                continue
            if f(l):
                yield os.path.normpath(l)

def findVhdsInPath(path, recursive=True):
    return findFilesInPath(path, _is_vhd, recursive)

def _is_vhd(p):
    return os.path.basename(p).lower().endswith('vhd')

def _is_makefile(f):
    return os.path.basename(f) == 'Makefile'

_RE_LIBRARY_NAME = re.compile(r"(?<=\[)\w+(?=\])")
_RE_BUILD_OPTIONS = re.compile(r"^\s*build_flags\s*=\s*")
_RE_COMMENTS = re.compile(r"\s*#.*$")
_RE_BLANK_LINE = re.compile(r"^\s*$")

def readLibrariesFromFile(filename):
    "Parse a file and return library names, sources and build flags"
    library = ''
    build_flags = ''
    for line in open(filename, 'r').read().split("\n"):
        line = _RE_COMMENTS.sub("", line)
        if _RE_BLANK_LINE.match(line):
            continue

        if _RE_BUILD_OPTIONS.match(line):
            build_flags = _RE_BUILD_OPTIONS.sub('', line)
            build_flags = re.split(r"\s+", build_flags)
            continue

        if re.match(r"^\s*\[\w+\]", line):
            library = _RE_LIBRARY_NAME.findall(line)
            library = library[0]
            build_flags = ''
        else:
            yield library, re.sub(r"^\s*|\s*$", "", line), build_flags

