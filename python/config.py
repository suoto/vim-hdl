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

import logging, os, sys

class Config(object):
    is_toolchain = True
    silent = True
    thread_limit = 20
    log_file = os.path.join('/', 'tmp', 'build.log')
    log_level = logging.DEBUG
    show_only_current_file = True
    show_reverse_dependencies = "errors" # "none", "errors", "warnings"


    #  log_format = "%(asctime)s <<%(levelname)-8s @ %(name)s >> %(message)s"
    log_format = "%(levelname)-8s || %(name)s || %(message)s"

    _logger = logging.getLogger(__name__)

    @staticmethod
    def _setupStreamHandler(stream):
        stream_handler = logging.StreamHandler(stream)
        stream_handler.formatter = logging.Formatter(Config.log_format)
        logging.root.addHandler(stream_handler)
        logging.root.setLevel(Config.log_level)
        #  Config._logger.addHandler(stream_handler)
        #  _logger_vcom.addHandler(stream_handler)

    @staticmethod
    def _setupFileHandler(f):
        file_handler = logging.FileHandler(f)
        file_handler.formatter = logging.Formatter(Config.log_format)
        logging.root.addHandler(file_handler)
        logging.root.setLevel(Config.log_level)
        #  Config._logger.addHandler(file_handler)
        #  _logger_vcom.addHandler(file_handler)

    @staticmethod
    def _setupToolchain():
        Config._setupFileHandler(Config.log_file)
        Config._logger.info("Setup for toolchain")
        Config.is_toolchain = True
        Config.silent = True

    @staticmethod
    def _setupStandalone():
        Config._setupStreamHandler(sys.stdout)
        Config._logger.info("Setup for standalone")
        Config.is_toolchain = False
        Config.silent = False

    @staticmethod
    def setupBuild():
        if 'VIM' in os.environ.keys():
            Config.log_level = logging.INFO
            Config.is_toolchain = True
            Config._setupToolchain()
        else:
            Config.is_toolchain = False
            Config._setupStandalone()

    @staticmethod
    def updateFromArgparse(args):
        for k, v in args._get_kwargs():
            if k in ('is_toolchain', ):
                raise RuntimeError("Can't redefine %s" % k)

            if k == 'thread_limit' and v is None:
                continue

            setattr(Config, k, v)

        _msg = ["Configuration update"]
        for k, v in Config.getCurrentConfig().iteritems():
            _msg += ["%s = %s" % (str(k), str(v))]

        Config._logger.info("\n".join(_msg))

    @staticmethod
    def getCurrentConfig():
        r = {}
        for k, v in Config.__dict__.iteritems():
            if k.startswith('_'):
                continue
            if k.startswith('__') and k.startswith('__'):
                continue
            if type(v) is staticmethod:
                continue
            r[k] = v
        return r

