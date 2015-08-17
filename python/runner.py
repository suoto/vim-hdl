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

import logging, sys, os
from config import Config
from compilers import msim
from library import Library
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
    parser.add_argument('--verbose', '-v', action='append_const', const=1)
    #  parser.add_argument('--library', '-l', type=str, default='common_lib')
    parser.add_argument('--clean', '-c', action='store_true')
    #  parser.add_argument('sources', action='append', nargs='+')#--, default='~/hdl_lib/common_lib/common_pkg.vhd')
    #  parser.add_argument('--build-source',       '-c',                action='store')
    #  parser.add_argument('--build-until-stable', '-f',                action='store_true')
    #  parser.add_argument('--thread-limit',       action='store',      type=int)
    #  parser.add_argument('--silent',             action='store_true', default=False)

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args()
    print args
    if args.verbose:
        args.log_level = _LOG_LEVELS[len(args.verbose)]

    Config.updateFromArgparse(args)
    Config.setupBuild()

    #  sources = []
    #  for _a in args.sources:
    #      for __a in _a:
    #          sources.append(os.path.expanduser(__a))

    return args.clean #, args.library, sources

    #  Config.updateFromArgparse(args)

    #  libraries = {}
    #  libraries.update(search_makefiles())
    #  libraries.update(get_custom_libs())

    #  # libraries = imported_from_prj()

    #  if Config.build_ctags:
    #      tags_t = threading.Thread(target=build_tags, args=(libraries,))
    #      tags_t.start()

    #  if Config.silent:
    #      verbose = False
    #  else:
    #      verbose = True
    #  if Config.build_until_stable:
    #      build_until_stable(libraries, verbose)

    #  if Config.build_source:
    #      _logger.debug("Searching for '%s'", Config.build_source)
    #      if build_source(libraries, Config.build_source):
    #          _logger.warning("Unable to find source file '%s'", Config.build_source)
    #          print "** Warning: %s(1): Unable to find source file" % Config.build_source

    #  if Config.build_ctags:
    #      tags_t.join()

def main():
    #  clean, library, sources = parseArguments()
    clean = parseArguments()
    if clean:
        os.system('rm -rf ~/temp/builder')

    project = ProjectBuilder(builder=msim.MSim('~/temp/builder'))

    for lib, path, flags in (
            ('osvvm_lib', '~/hdl_lib/osvvm_lib/', ('-2008', )),
            ('common_lib', '~/hdl_lib/common_lib/', ''),
            ('pck_fio_lib', '~/hdl_lib/pck_fio_lib', ''),
            ('memory', '~/hdl_lib/memory/', ''),
        ):
        project.addLibrary(lib, findVhdsInPath(path))
        for flag in flags:
            project.addBuildFlags(lib, flag)

    project.build()

    #  libraries = {}

    #  for lib, lib_path in LIBS:
    #      libraries[lib] = Library(builder=builder, name=lib, sources=list(findFilesInPath(lib_path, _is_vhd)), build_location='~/temp/builder/')
    #      libraries[lib].build()

    #      #  builder.build(lib, sources)
    #      #  for source in sources:
    #      #      _logger.info("Building (%s) %s", lib, source)
    #      #      builder.build(lib, source)

if __name__ == '__main__':
    main()


