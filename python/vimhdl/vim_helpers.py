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

_logger = logging.getLogger(__name__)
import vim                 # pylint: disable=import-error
# Check if we should use vim.List and vim.Dictionary (for Vim itself) or
# Python's list and dict (for neovim)
try:
    list = vim.List        # pylint: disable=redefined-builtin,invalid-name
except AttributeError:     # pragma: no cover
    pass

try:
    dict = vim.Dictionary  # pylint: disable=redefined-builtin,invalid-name
except AttributeError:     # pragma: no cover
    pass


def _escapeForVim(text):
    '''These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe'''
    return text.replace("'", "''")

def postVimInfo(message):
    '''These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe'''
    _logger.info(message)
    vim.command("redraw | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))

def postVimWarning(message):
    '''These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe'''
    _logger.warning(message)
    vim.command("redraw | echohl WarningMsg | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))

def postVimError(message):
    '''These were "Borrowed" from YCM.
    See https://github.com/Valloric/YouCompleteMe'''
    _logger.error(message)
    vim.command("echohl ErrorMsg | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))


# For Vim verion >= 7.3.911 we can access via .vars
#  if vim.eval('has("patch-7.3.911")'):
if hasattr(vim, 'vars'):
    def getVimGlobals(var=None):
        'Return Vim global variables using attribute (newer Vim versions)'
        if var is None:
            return vim.vars
        else:
            return vim.vars[var]

    def getBufferVars(vbuffer=None, var=None):
        if vbuffer is None:
            vbuffer = vim.current.buffer
        if var is None:
            return vbuffer.vars
        else:
            return vbuffer.vars[var]

    def getVimOptions(name, vbuffer=None):
        if vbuffer is None:
            vbuffer = vim.current.buffer
        return vbuffer.options[name]
else: # pragma: no cover
    # We're not going to cover this as tests fail for some reason with
    # Vim 7.3.
    def getVimGlobals(var=None):
        'Return Vim global variables using using vim.eval (for older versions)'
        if var is None:
            return vim.eval('g:')
        else:
            return vim.eval('g:')[var]

    def getBufferVars(vbuffer=None, var=None):
        assert vbuffer is None, "Getting buffer variables from other buffers " \
                                "not implemented"
        if var is None:
            return vim.eval('b:')
        else:
            return vim.eval('b:')[var]

    def getVimOptions(name, vbuffer=None):
        assert vbuffer is None, "Getting buffer variables from other buffers " \
                                "not implemented"
        return vim.eval('&%s' % name)

