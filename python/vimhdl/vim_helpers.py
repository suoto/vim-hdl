# This file is part of vim-hdl.
#
# Copyright (c) 2015-2016 Andre Souto
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
"Misc helpers for common vim-hdl operations"

import logging
import os
import os.path as p
import socket
import vim                 # pylint: disable=import-error

_logger = logging.getLogger(__name__)

_VIMHDL_DEFAULT_CONFIG_FILE_NAME = 'vimhdl.prj'

def _toUnicode(value):
    """
    Returns a unicode type; either the new python-future str type or
    the real unicode type. The difference shouldn't matter.

    These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe
    """
    if not value:
        return str()
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        # All incoming text should be utf8
        return str(value, 'utf8')
    return str(value)

def _escapeForVim(text):
    """
    Escape text for Vim.
    """
    return _toUnicode(text.replace("'", "' . \"'\" .  '"))

def toVimDict(obj, vim_variable):
    """
    Converts the 'obj' dict to a Vim dictionary by iterating over the
    key/value pairs. The reason for this is because Vim has some issues
    interpreting strings with both escaped single and double quotes (or
    I haven't found a way to code it properly...). The thing is, in some
    cases, doing vim.command('let foo = <some_dict>') often fails when
    key or value has both single and double quotes, but it works if
    the fields are assigned individually, because we can force which
    one of the quotes will require escape
    """
    vim.command("let %s = { }" % vim_variable)
    for key, value in obj.items():
        if isinstance(value, (str, bytes)):
            value = _escapeForVim(value)
        if isinstance(key, (str, bytes)):
            key = _escapeForVim(key)
        vim.command("let {0}['{1}'] = '{2}'".format(vim_variable, key, value))

def postVimInfo(message):
    """
    These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe
    """
    _logger.info(message)
    vim.command("redraw | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))

def postVimWarning(message):
    """
    These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe
    """
    _logger.warning(message)
    vim.command("redraw | echohl WarningMsg | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))

def postVimError(message):
    """
    These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe
    """
    _logger.error(message)
    vim.command("echohl ErrorMsg | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))

def getUnusedLocalhostPort():
    """
    These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe
    """
    sock = socket.socket()
    # This tells the OS to give us any free port in the range [1024 - 65535]
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

# Methods of accessing g: and b: work only with Vim 7.4+

def _getVimGlobals(var=None):
    """
    Returns a global variable, i.e., from g:
    """
    if var is None:
        return vim.vars
    else:
        return vim.vars[var]

def _getBufferVars(vbuffer=None, var=None):
    """
    Returns a buffer variable, i.e., from b:
    """
    if vbuffer is None:
        vbuffer = vim.current.buffer
    if var is None:
        return vbuffer.vars
    else:
        return vbuffer.vars[var]

def getProjectFile():
    """
    Searches for a valid hdlcc configuration file in buffer vars (i.e.,
    inside b:) then in global vars (i.e., inside g:)
    """
    conf_file = None
    if 'vimhdl_conf_file' in _getBufferVars():
        conf_file = p.abspath(p.expanduser(
            _getBufferVars(var='vimhdl_conf_file')))
        if not p.exists(conf_file):
            _logger.warning("Buffer config file '%s' is set but not "
                            "readable", conf_file)
            conf_file = None

    if conf_file is None:
        if 'vimhdl_conf_file' in _getVimGlobals():
            conf_file = p.abspath(p.expanduser(
                _getVimGlobals('vimhdl_conf_file')))
            if not p.exists(conf_file):
                _logger.warning("Global config file '%s' is set but not "
                                "readable", conf_file)
                conf_file = None

    if conf_file is None:
        _logger.warning("Couldn't find a valid config file")
        return

    return conf_file

def getBackupFileName(path):
    return p.join(p.dirname(path), '.' + p.basename(path) + '.backup')
