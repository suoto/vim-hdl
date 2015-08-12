#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import logging, sys, os
from config import Config
from compilers import msim

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
    parser.add_argument('--verbose', '-v',  action='append_const', const=1)
    parser.add_argument('--library', '-l', type=str, default='base_lib_pkg')
    parser.add_argument('--source', '-s', type=str, default='~/git-svn/odf/branches/_all/fpga/src/base_lib/base_lib_pkg.vhd')
    parser.add_argument('--clean', '-c', action='store_true')
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
    if args.verbose:
        args.log_level = _LOG_LEVELS[len(args.verbose)]

    Config.updateFromArgparse(args)
    Config.setupBuild()

    return args.clean, args.library, os.path.expanduser(args.source)

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
    clean, library, source = parseArguments()
    if clean:
        os.system('rm -rf ~/temp/builder')
    else:
        _logger.info("Building (%s) %s", library, source)
        compiler = msim.MSim('~/temp/builder/')
        compiler.build(library, source)

if __name__ == '__main__':
    main()


