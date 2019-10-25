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
let s:vimhdl_path = escape(expand('<sfile>:p:h'), '\') . '/../'

function! s:usingPython2() abort   abort "{ Inspired on YCM
    if has('python3')
        return 0
    elseif has('python')
        return 1
    endif
    throw 'Unable to identify Python version'
endfunction
"}

" Inspired on YCM
let s:using_python2 = s:usingPython2()
let s:python_until_eof = s:using_python2 ? 'python << EOF' : 'python3 << EOF'
let s:python_command = s:using_python2 ? 'py ' : 'py3 '

function! s:pyEval( eval_string ) abort "{ Inspired on YCM
  if s:using_python2
    return pyeval( a:eval_string )
  endif
  return py3eval( a:eval_string )
endfunction
"}
function! s:postWarning(msg) abort "{ function!
    redraw | echohl WarningMsg | echom a:msg | echohl None"
endfunction "}
function! s:postInfo(msg) abort "{ function!
    redraw | echom a:msg | echohl None
endfunction "}
" { s:setupPython() Setup Vim's Python environment to call vim-hdl within Vim
" ============================================================================
function! s:setupPython() abort
    let l:log_level = get(g:, 'vimhdl_log_level', 'INFO')
    let l:log_file = get(g:, 'vimhdl_log_file', '')

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
    for path in (p.join(vim.eval('s:vimhdl_path'), 'python'),):
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
    vimhdl_client = vimhdl.VimhdlClient(
        log_level=vim.eval('l:log_level'),
        log_target=vim.eval('l:log_file'),
    )
EOF

endfunction
" }
" { s:setupCommands() Setup Vim commands to interact with vim-hdl
" ============================================================================
function! s:setupCommands() abort
    command! VimhdlInfo              call s:printInfo()
    command! VimhdlViewDependencies  call s:viewDependencies()
    command! VimhdlRebuildProject    call s:pyEval('bool(vimhdl_client.rebuildProject())')
    command! VimhdlRestartServer     call s:restartServer()
    command! VimhdlViewBuildSequence call s:viewBuildSequence()
    command! -nargs=* -complete=dir 
                \ VimhdlCreateProjectFile call s:createProjectFile(<f-args>)
endfunction
" }
" { s:setupHooks() Setup filetype hooks
" ============================================================================
function! s:setupHooks(...) abort
    augroup vimhdl
    for l:ext in a:000
        for l:event in ['BufWritePost', 'FocusGained', 'CursorMoved',
                    \'CursorMovedI', 'CursorHold', 'CursorHoldI',
                    \'InsertEnter']
            execute('autocmd! ' . l:event . ' ' . l:ext . ' ' .
                   \':' . s:python_command . ' vimhdl_client.requestUiMessages(''' . l:event . ''')')
        endfor
    endfor
    augroup END
endfunction
" }
" { s:setupSyntastic() Setup Syntastic to use vimhdl in the given filetypes
" ============================================================================
function! s:setupSyntastic(...) abort
    for l:filetype in a:000
        if !exists('g:syntastic_' . l:filetype . '_checkers')
            execute('let g:syntastic_' . l:filetype . '_checkers = ["vimhdl"]')
        else
            execute('let g:syntastic_' . l:filetype . '_checkers += ["vimhdl"]')
        end
    endfor

endfunction
" }
" { s:printInfo() Handle for VimHdlInfo command
" ============================================================================
function! s:printInfo() abort
    echom 'vimhdl debug info'
    let l:debug_info = s:pyEval('vimhdl_client.getVimhdlInfo()')
    for l:line in split( l:debug_info, '\n' )
        echom l:line
  endfor
endfunction
" }
" { s:restartServer() Handle for VimHdlRestartServer command
" ============================================================================
function! s:restartServer() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call s:postWarning("Not a HDL file, can't restart server")
        return
    endif
    echom 'Restarting HDL Checker server'

    let l:log_level = get(g:, 'vimhdl_log_level', 'INFO')
    let l:log_file = get(g:, 'vimhdl_log_file', v:null)

    exec s:python_until_eof
_logger.info("Restarting HDL Checker server")
vimhdl_client.shutdown()
del vimhdl_client
vimhdl_client = vimhdl.VimhdlClient(
    log_level=vim.eval('l:log_level'),
    log_target=vim.eval('l:log_file'),
)
EOF
    unlet! g:vimhdl_server_started
    call s:startServer()

endfunction
" }
" { vimhdl#getMessagesForCurrentBuffer()
" ============================================================================
function! vimhdl#getMessagesForCurrentBuffer() abort
    let l:loclist = []
exec s:python_until_eof
try:
    vimhdl_client.getMessages(vim.current.buffer, 'l:loclist')
except:
    _logger.exception("Error getting messages")
EOF
    return l:loclist
endfunction
"}
" { s:listDependencies()
" ============================================================================
function! s:viewDependencies() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call s:postWarning("Not a HDL file, can't restart server")
        return
    endif
    let l:dependencies = s:pyEval('vimhdl_client.getDependencies()')
    for l:line in split(l:dependencies, "\n")
        echom l:line
    endfor
endfunction
"}
" { s:listBuildSequence()
" ============================================================================
function! s:viewBuildSequence() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call s:postWarning("Not a HDL file, can't restart server")
        return
    endif
    let l:sequence = s:pyEval('vimhdl_client.getBuildSequence()')
    for l:line in split(l:sequence, "\n")
        echom l:line
    endfor
endfunction
"}
" { s:createProjectFile
" ============================================================================
function! s:createProjectFile(...) abort
    call s:startServer()

    let b:local_arg = a:000
    exec s:python_until_eof
vimhdl_client.updateHelperWrapper()
EOF
endfunction
"}
" { s:onVimhdlTempQuit() Handles leaving the temporary config file edit
" ============================================================================
function! s:onVimhdlTempQuit()
    exec s:python_until_eof
vimhdl_client.helper_wrapper.onVimhdlTempQuit()
EOF
endfunction
"}
" { vimhdl#setup() Main vim-hdl setup
" ============================================================================
function! vimhdl#setup() abort
    if !(exists('g:vimhdl_loaded') && g:vimhdl_loaded)
        let g:vimhdl_loaded = 1
        call s:setupPython()
        call s:setupCommands()
        call s:setupHooks('*.vhd', '*.vhdl', '*.v', '*.sv')
        call s:setupSyntastic('vhdl', 'verilog', 'systemverilog')
    endif

    if count(['vhdl', 'verilog', 'systemverilog'], &filetype)
        call s:startServer()
    endif
endfunction
" }
" { s:startServer() Starts HDL Checker server
" ============================================================================
function! s:startServer() abort
    if (exists('g:vimhdl_server_started') && g:vimhdl_server_started)
        return
    endif

    let g:vimhdl_server_started = 1
    call s:pyEval('bool(vimhdl_client.startServer())')

endfunction
"}
" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
