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
let s:vimhdl_path = simplify(escape(expand('<sfile>:p:h'), '\') . '/../')

function! vimhdl#basePath()
  return s:vimhdl_path
endfunction

" FIXME: Test with other LSP clients in the future

function! s:usingLspServer() abort
  if exists(':ALEInfo') != 0
    return 1
  endif
  if exists(':LspStatus') != 0
    return 1
  endif
  if exists(':LanguageClientStart') != 0
    return 1
  endif
  return 0
endfunction

function! vimhdl#usingPython2() abort "{{ Inspired on YCM
  if has('python3')
    return 0
  elseif has('python')
    return 1
  endif
  throw 'Unable to identify Python version'
endfunction
"}}

" Inspired on YCM
let s:using_python2 = vimhdl#usingPython2()
let s:python_until_eof = s:using_python2 ? 'python << EOF' : 'python3 << EOF'
let s:python_command = s:using_python2 ? 'py ' : 'py3 '

" Trusty version of Vim (7.4.52) can't convert None to a Vim object, so need
" to wrap calls with bool()
function! vimhdl#pyEval( eval_string ) abort "{{ Inspired on YCM
  if s:using_python2
    return pyeval( a:eval_string )
  endif
  return py3eval( a:eval_string )
endfunction
"}}

function! vimhdl#postWarning(msg) abort "{{
  redraw | echohl WarningMsg | echom a:msg | echohl None"
endfunction "}}

function! vimhdl#postInfo(msg) abort "{{ function!
  redraw | echom a:msg | echohl None
endfunction "}}

"{{ vimhdl#setupPython() Setup Vim's Python environment to call vim-hdl within Vim
" ============================================================================
function! vimhdl#setupPython() abort
  let l:setup_script = join([s:vimhdl_path, 'python', 'setup.py'], '/')

  if s:using_python2
    exec 'pyfile ' . l:setup_script
  else
    exec 'py3file ' . l:setup_script
  end
endfunction
"}}

" {{ vimhdl#getLspCommand(...) Gets the command to start the LSP in a list
function! vimhdl#getLspCommand(...) abort
  " let l:python = s:using_python2 ? 'python2' : 'python3'
  let l:server = 'hdlcc'

  return [
        \ l:server,
        \ '--stderr', '/tmp/hdlcc-stderr.log',
        \ '--log-level', 'DEBUG',
        \ '--log-stream', '/tmp/hdlcc.log',
        \ '--lsp'
        \ ]
endfunction "}}

"{{ vimhdl#setupCommands() Setup Vim commands to interact with vim-hdl
" ============================================================================
function! vimhdl#setupCommands() abort
  command! VimhdlInfo              call vimhdl#printInfo()

  if ! s:usingLspServer()
    command! VimhdlViewDependencies  call vimhdl#viewDependencies()
    command! VimhdlRebuildProject    call vimhdl#pyEval('bool(vimhdl_client.rebuildProject())')
    command! VimhdlRestartServer     call vimhdl#restartServer()
    command! VimhdlViewBuildSequence call vimhdl#viewBuildSequence()
    command! -nargs=* -complete=dir 
          \ VimhdlCreateProjectFile call vimhdl#createProjectFile(<f-args>)

  else
    command! VimhdlRestartServer   echoerr 'LSP does not (yet?) support ' .
                                         \ 'restarting servers, restarting failed'

    command! VimhdlViewDependencies  echoerr 'Command not supported when in LSP mode'
    command! VimhdlRebuildProject    echoerr 'Command not supported when in LSP mode'
    command! VimhdlViewBuildSequence echoerr 'Command not supported when in LSP mode'
    command! VimhdlCreateProjectFile echoerr 'Command not supported when in LSP mode'
  endif

endfunction
"}}

"{{ vimhdl#setupHooks() Setup filetype hooks
" ============================================================================
function! vimhdl#setupHooks(...) abort
  augroup vimhdl
    for l:ext in a:000
      " Setup hooks for retrieving UI messages. At some point this could be
      " moved to used an async API and avoid this constant polling
      for l:event in ['BufWritePost', 'FocusGained', 'CursorMoved',
            \'CursorMovedI', 'CursorHold', 'CursorHoldI',
            \'InsertEnter']
        execute('autocmd! ' . l:event . ' ' . l:ext . ' ' .
              \':' . s:python_command . ' ' . 
              \'vimhdl_client.requestUiMessages(''' . l:event . ''')')
      endfor

      " Setup hooks for onBufferVisit
      for l:event in ['BufEnter', 'FocusGained', 'InsertLeave']
        execute('autocmd! ' . l:event . ' ' . l:ext . ' ' .
              \':call vimhdl#onBufferVisit()')
      endfor

    endfor
  augroup END
endfunction
"}}

"{{ vimhdl#onBufferVisit() Starts hdlcc server and calls vimhdl client method for the event
function! vimhdl#onBufferVisit() abort
  call vimhdl#startServer()
  return vimhdl#pyEval('bool(vimhdl_client.onBufferVisit())')
endfunction " }}

"{{ vimhdl#setupSyntastic() Setup Syntastic to use vimhdl in the given filetypes
" ============================================================================
function! vimhdl#setupSyntastic(...) abort
  call vimhdl#pyEval('bool(_logger.info("Setting up Syntastic support"))')
  for l:filetype in a:000
    if !exists('g:syntastic_' . l:filetype . '_checkers')
      execute('let g:syntastic_' . l:filetype . '_checkers = ["vimhdl"]')
    else
      execute('let g:syntastic_' . l:filetype . '_checkers += ["vimhdl"]')
    end
    augroup vimhdl
      execute('autocmd! Filetype ' . l:filetype . ' :call vimhdl#onBufferVisit()')
    augroup END
  endfor
endfunction
"}}

"{{ vimhdl#printInfo() Handle for VimHdlInfo command
" ============================================================================
function! vimhdl#printInfo() abort
  echom 'vimhdl debug info'
  if s:usingLspServer()
    echom '- vimhdl version: ' . vimhdl#pyEval('vimhdl.__version__')
    echom '- hdlcc version: ' . vimhdl#pyEval('hdlcc.__version__') .
          \ ' (hdlcc running in LSP mode)'
  else
    let l:debug_info = vimhdl#pyEval('vimhdl_client.getVimhdlInfo()')
    for l:line in split( l:debug_info, '\n' )
      echom l:line
    endfor
  endif
endfunction
"}}

"{{ vimhdl#restartServer() Handle for VimHdlRestartServer command
" ============================================================================
function! vimhdl#restartServer() abort

  if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
    call vimhdl#postWarning("Not a HDL file, can't restart server")
    return
  endif

  echom 'Restarting hdlcc server'
  call vimhdl#pyEval('bool(vimhdlRestartServer())')
endfunction
"}}

" { vimhdl#getMessagesForCurrentBuffer()
" ============================================================================
function! vimhdl#getMessagesForCurrentBuffer() abort
  return vimhdl#pyEval('vimhdl_client.getMessages()')
endfunction
"}

"{{ vimhdl#listDependencies()
" ============================================================================
function! vimhdl#viewDependencies() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call vimhdl#postWarning('Can''t retrieve dependencies of filetype '
                            \ . &filetype)
        return
    endif
    let l:dependencies = vimhdl#pyEval('vimhdl_client.getDependencies()')
    for l:line in split(l:dependencies, "\n")
        echom l:line
    endfor
endfunction
"}}

"{{ vimhdl#listBuildSequence()
" ============================================================================
function! vimhdl#viewBuildSequence() abort
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call vimhdl#postWarning('Don''t know how to check build sequence of '
                            \ . 'filetype ' . &filetype)
        return
    endif
    let l:sequence = vimhdl#pyEval('vimhdl_client.getBuildSequence()')
    for l:line in split(l:sequence, "\n")
        echom l:line
    endfor
endfunction
"}}

"{{ vimhdl#createProjectFile
" ============================================================================
function! vimhdl#createProjectFile(...) abort
  call vimhdl#startServer()

  let b:local_arg = a:000
  call vimhdl#pyEval('bool(vimhdl_client.updateHelperWrapper())')
endfunction
"}}

"{{ vimhdl#onVimhdlTempQuit() Handles leaving the temporary config file edit
" ============================================================================
function! vimhdl#onVimhdlTempQuit() abort
  call vimhdl#pyEval('bool(vimhdl_client.helper_wrapper.onVimhdlTempQuit())')
endfunction
"}}

"{{ vimhdl#setup() Main vim-hdl setup
" ============================================================================
function! vimhdl#setup() abort
  if !(exists('g:vimhdl_loaded') && g:vimhdl_loaded)
    let g:vimhdl_loaded = 1
    call vimhdl#setupPython()
    call vimhdl#setupCommands()

    if ! s:usingLspServer()
      call vimhdl#setupHooks('*.vhd', '*.vhdl', '*.v', '*.sv')
    endif

    if exists(':SyntasticInfo')
      call vimhdl#setupSyntastic('vhdl', 'verilog', 'systemverilog')
    end
    if exists(':ALEInfo')
      call vimhdl#ale#setup('vhdl', 'verilog', 'systemverilog')
    end
  endif
endfunction
"}}

"{{ vimhdl#getServerAddress Fetches address and port used by the server
" ============================================================================
function! vimhdl#getServerAddress(...) abort
  return vimhdl#pyEval('vimhdl_client.getServerAddress()')
endfunction

"}}

"{{ vimhdl#startServer() Starts hdlcc server
" ============================================================================
function! vimhdl#startServer() abort
  if s:usingLspServer()
    return
  endif

  if (exists('g:vimhdl_server_started') && g:vimhdl_server_started)
    return
  endif

  call vimhdl#pyEval('bool(vimhdl_client.startServer())')
  let g:vimhdl_server_started = 1
endfunction
"}}

" vim: set foldmarker={{,}} foldlevel=10 foldmethod=marker :
