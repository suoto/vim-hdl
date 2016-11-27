" This file is part of vim-hdl.
"
" Copyright (c) 2015-2016 Andre Souto
"
" vim-hdl is free software: you can redistribute it and/or modify
" it under the terms of the GNU General Public License as published by
" the Free Software Foundation, either version 3 of the License, or
" (at your option) any later version.
"
" vim-hdl is distributed in the hope that it will be useful,
" but WITHOUT ANY WARRANTY; without even the implied warranty of
" MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
" GNU General Public License for more details.
"
" You should have received a copy of the GNU General Public License
" along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.
"
let s:vimhdl_path = escape(expand('<sfile>:p:h'), '\') . "/../"

function! vimhdl#UsingPython2() "{ Inspired on YCM
    if has('python3')
        return 0
    elseif has('python')
        return 1
    endif
    throw "Unable to identify Python version"
endfunction
"}

" Inspired on YCM
let s:using_python2 = vimhdl#UsingPython2()
let s:python_until_eof = s:using_python2 ? "python << EOF" : "python3 << EOF"
let s:python_command = s:using_python2 ? "py " : "py3 "

function! s:Pyeval( eval_string ) "{ Inspired on YCM
  if s:using_python2
    return pyeval( a:eval_string )
  endif
  return py3eval( a:eval_string )
endfunction
"}
" { vimhdl#setupPython() Setup Vim's Python environment to call vim-hdl within Vim
" ============================================================================
function! vimhdl#setupPython()
    let python = s:using_python2 ? "python2" : "python3"

    exec s:python_until_eof
import sys
if 'vimhdl' not in sys.modules:
    import sys, vim
    import os.path as p
    import logging
    _logger = logging.getLogger(__name__)

    # Add a null handler for issue #19
    logging.root.addHandler(logging.NullHandler())

    _logger = logging.getLogger(__name__)
    for path in (p.join(vim.eval('s:vimhdl_path'), 'python'),
                 p.join(vim.eval('s:vimhdl_path'), 'dependencies', 'requests'),
                 p.join(vim.eval('s:vimhdl_path'), 'dependencies', 'hdlcc')):
        if path not in sys.path:
            path = p.abspath(path)
            if p.exists(path):
                sys.path.insert(0, path)
                _logger.info("Adding %s", path)
            else:
                _logger.warning("Path '%s' doesn't exists!", path)
    import vimhdl

# Create the client if it doesn't exists yet
try:
    vimhdl_client
    _logger.warning("vimhdl client already exists, skiping")
except NameError:
    vimhdl_client = vimhdl.VimhdlClient(python=vim.eval('python'))
EOF
endfunction
" }
" { vimhdl#setupCommands() Setup Vim commands to interact with vim-hdl
" ============================================================================
function! vimhdl#setupCommands()
    command! VimhdlInfo           call s:PrintInfo()
    command! VimhdlRebuildProject :py vimhdl_client.rebuildProject()
    command! VimhdlRestartServer  call s:RestartServer()

    " command! VimhdlListLibraries                   call vimhdl#listLibraries()
    " command! VimhdlListLibrariesAndSources         call vimhdl#listLibrariesAndSources()
    " command! VimhdlViewLog                         call vimhdl#viewLog()
    " command! VimhdlCleanProjectCache               call vimhdl#cleanProjectCache()

    " command! -nargs=? VimhdlAddSourceToLibrary call vimhdl#addSourceToLibrary(<f-args>)
    " command! -nargs=? VimhdlRemoveSourceFromLibrary call vimhdl#removeSourceFromLibrary(<f-args>)
endfunction
" }
" { vimhdl#setupHooks() Setup filetype hooks
" ============================================================================
function! vimhdl#setupHooks(...)
    for ext in a:000
        for event in ['BufWritePost', 'FocusGained', 'CursorMoved',
                    \'CursorMovedI', 'CursorHold', 'CursorHoldI',
                    \'InsertEnter']
            execute("autocmd! " . event . " " . ext . " " . 
                   \":" . s:python_command . " vimhdl_client.requestUiMessages('" . event . "')")
        endfor
        for event in ['BufEnter', 'FocusGained', 'InsertLeave']
            execute("autocmd! " . event . " " . ext . " " . 
                   \":" . s:python_command . " vimhdl_client.onBufferVisit()")
        endfor
        execute("autocmd! BufLeave " . ext . " " . 
               \":" . s:python_command . " vimhdl_client.onBufferLeave()")
    endfor
endfunction
" }
" { vimhdl#setup() Main vim-hdl setup
" ============================================================================
function! vimhdl#setup()
    if !(exists('g:vimhdl_loaded') && g:vimhdl_loaded)
        let g:vimhdl_loaded = 1
        call vimhdl#setupPython()
        call vimhdl#setupCommands()
        call vimhdl#setupHooks('*.vhd', '*.vhdl', '*.v', '*.sv')
    endif

    if count(['vhdl', 'verilog', 'systemverilog'], &filetype)
        if !(exists('g:vimhdl_server_started') && g:vimhdl_server_started)
            let g:vimhdl_server_started = 1
            call s:Pyeval('vimhdl_client.startServer()')
        endif
    endif

endfunction
" }
" { vimhdl#PrintInfo() Handle for VimHdlInfo command
" ============================================================================
function! s:PrintInfo()
  echom "vimhdl debug info"
  let debug_info = s:Pyeval('vimhdl_client.getVimhdlInfo()')
  for line in split( debug_info, "\n" )
    echom line
  endfor
endfunction
" }
" { vimhdl#RestartServer() Handle for VimHdlRestartServer command
" ============================================================================
function! s:RestartServer()
  echom "Restarting hdlcc server"
  let python = s:using_python2 ? "python2" : "python3"
  exec s:python_until_eof
_logger.info("Restarting hdlcc server")
vimhdl_client.shutdown()
del vimhdl_client
vimhdl_client = vimhdl.VimhdlClient(python=vim.eval('python'))
vimhdl_client.startServer()
_logger.info("hdlcc restart done")
EOF
endfunction
" }
" { vimhdl#RestartServer() Restart the hdlcc server
" ============================================================================
function! vimhdl#GetMessagesForCurrentBuffer()
    let loclist = []
exec s:python_until_eof
try:
    vimhdl_client.getMessages(vim.current.buffer, 'loclist')
except:
    _logger.exception("Error getting messages")
EOF
    return loclist
endfunction
"}

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
