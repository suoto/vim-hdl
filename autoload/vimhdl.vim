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

function! vimhdl#basePath()
  return s:vimhdl_path
endfunction

" FIXME: Test with other LSP clients in the future
let s:use_lsp_server = exists(':ALEInfo') != 0

function! vimhdl#useLspServer ()
  return s:use_lsp_server
endfunction

function! vimhdl#usingPython2() abort "{ Inspired on YCM
  if has('python3')
    return 0
  elseif has('python')
    return 1
  endif
  throw 'Unable to identify Python version'
endfunction
"}

" Inspired on YCM
let s:using_python2 = vimhdl#usingPython2()
let s:python_until_eof = s:using_python2 ? 'python << EOF' : 'python3 << EOF'
let s:python_command = s:using_python2 ? 'py ' : 'py3 '

function! vimhdl#pyEval( eval_string ) abort "{ Inspired on YCM
  if s:using_python2
    return pyeval( a:eval_string )
  endif
  return py3eval( a:eval_string )
endfunction
"}

function! vimhdl#postWarning(msg) abort "{
  redraw | echohl WarningMsg | echom a:msg | echohl None"
endfunction "}

function! vimhdl#postInfo(msg) abort "{ function!
  redraw | echom a:msg | echohl None
endfunction "}

" { s:setupPython() Setup Vim's Python environment to call vim-hdl within Vim
" ============================================================================
function! s:setupPython() abort
  let l:python = s:using_python2 ? 'python2' : 'python3'
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
  for path in (p.join(vim.eval('vimhdl#basePath()'), 'python'),
               p.join(vim.eval('vimhdl#basePath()'), 'dependencies', 'hdlcc')):
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
  vimhdl_client = vimhdl.VimhdlClient(python=vim.eval('l:python'))
EOF

endfunction
" }

" { s:setupCommands() Setup Vim commands to interact with vim-hdl
" ============================================================================
function! s:setupCommands() abort
  command! VimhdlInfo              call vimhdl#printInfo()
  command! VimhdlViewDependencies  call vimhdl#viewDependencies()
  command! VimhdlRebuildProject    call vimhdl#pyEval('bool(vimhdl_client.rebuildProject())')
  command! VimhdlRestartServer     call vimhdl#restartServer()
  command! VimhdlViewBuildSequence call vimhdl#viewBuildSequence()
  command! -nargs=* -complete=dir 
        \ VimhdlCreateProjectFile call vimhdl#createProjectFile(<f-args>)
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
      for l:event in ['BufEnter', 'FocusGained', 'InsertLeave']
        execute('autocmd! ' . l:event . ' ' . l:ext . ' ' .
              \':' . s:python_command . ' vimhdl_client.onBufferVisit()')
      endfor
      execute('autocmd! BufLeave ' . l:ext . ' ' .
            \':' . s:python_command . ' vimhdl_client.onBufferLeave()')

    endfor
  augroup END
endfunction
" }

" { s:setupSyntastic() Setup Syntastic to use vimhdl in the given filetypes
" ============================================================================
function! s:setupSyntastic(...) abort
  call vimhdl#pyEval('_logger.info("Setting up Syntastic support")')
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
function! vimhdl#printInfo() abort
  echom 'vimhdl debug info'
  let l:debug_info = vimhdl#pyEval('vimhdl_client.getVimhdlInfo()')
  for l:line in split( l:debug_info, '\n' )
    echom l:line
  endfor
endfunction
" }

" { s:restartServer() Handle for VimHdlRestartServer command
" ============================================================================
function! vimhdl#restartServer() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call vimhdl#postWarning("Not a HDL file, can't restart server")
        return
    endif
    echom 'Restarting hdlcc server'
    let l:python = s:using_python2 ? 'python2' : 'python3'
    exec s:python_until_eof
_logger.info("Restarting hdlcc server")
vimhdl_client.shutdown()
del vimhdl_client
vimhdl_client = vimhdl.VimhdlClient(python=vim.eval('l:python'))
vimhdl_client.startServer(vim.eval('vimhdl#useLspServer()'))
_logger.info("hdlcc restart done")
EOF
endfunction
" }

" { vimhdl#getMessagesForCurrentBuffer()
" ============================================================================
function! vimhdl#getMessagesForCurrentBuffer(...) abort
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

" { vimhdl#listDependencies()
" ============================================================================
function! vimhdl#viewDependencies() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call vimhdl#postWarning("Not a HDL file, can't restart server")
        return
    endif
    let l:dependencies = vimhdl#pyEval('vimhdl_client.getDependencies()')
    for l:line in split(l:dependencies, "\n")
        echom l:line
    endfor
endfunction
"}
" { vimhdl#listBuildSequence()
" ============================================================================
function! vimhdl#viewBuildSequence() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call vimhdl#postWarning("Not a HDL file, can't restart server")
        return
    endif
    let l:sequence = vimhdl#pyEval('vimhdl_client.getBuildSequence()')
    for l:line in split(l:sequence, "\n")
        echom l:line
    endfor
endfunction
"}

" { vimhdl#createProjectFile
" ============================================================================
function! vimhdl#createProjectFile(...) abort
  call vimhdl#startServer()

  let b:local_arg = a:000
  call vimhdl#pyEval('vimhdl_client.updateHelperWrapper()')
endfunction
"}

" { s:onVimhdlTempQuit() Handles leaving the temporary config file edit
" ============================================================================
function! s:onVimhdlTempQuit()
  call vimhdl#pyEval('vimhdl_client.helper_wrapper.onVimhdlTempQuit()')
endfunction
"}

" { vimhdl#setup() Main vim-hdl setup
" ============================================================================
function! vimhdl#setup() abort
  if !(exists('g:vimhdl_loaded') && g:vimhdl_loaded)
    let g:vimhdl_loaded = 1
    call s:setupPython()
    call s:setupCommands()
    if ! vimhdl#useLspServer()
      call s:setupHooks('*.vhd', '*.vhdl', '*.v', '*.sv')
    endif

    if count(['vhdl', 'verilog', 'systemverilog'], &filetype)
      call s:startServer()
    endif

    if exists(':SyntasticInfo')
      call s:setupSyntastic('vhdl', 'verilog', 'systemverilog')
    end
    if exists(':ALEInfo')
      call vimhdl#ale#setup('vhdl', 'verilog', 'systemverilog')
    end
  endif

endfunction
" }

" { vimhdl#getServerAddress Fetches address and port used by the server
" ============================================================================
function! vimhdl#getServerAddress(buffer) abort
  let l:address = ''

  exec s:python_until_eof
try:
  vimhdl_client
  vim.command("let l:address = '%s'" % vimhdl_client.getServerAddress())
except NameError:
  _logger.exception("Unable to get address")
EOF

    return l:address
endfunction

"}

" { s:startServer() Starts hdlcc server
" ============================================================================
function! s:startServer() abort
  if (exists('g:vimhdl_server_started') && g:vimhdl_server_started)
    return
  endif

  call vimhdl#pyEval('vimhdl_client.startServer(vim.eval(''vimhdl#useLspServer()''))')
  let g:vimhdl_server_started = 1
endfunction
"}

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
