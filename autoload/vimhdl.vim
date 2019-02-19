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
endfunction
"}
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
    for path in (p.join(vim.eval('s:vimhdl_path'), 'python'),
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
    vimhdl_client = vimhdl.VimhdlClient(python=vim.eval('l:python'))
EOF

endfunction
" }
" { s:setupCommands() Setup Vim commands to interact with vim-hdl
" ============================================================================
function! s:setupCommands() abort
    command! VimhdlInfo              call s:printInfo()
    command! VimhdlPrintDependencies call s:printDependencies()
    command! VimhdlRebuildProject    call s:pyEval('bool(vimhdl_client.rebuildProject())')
    command! VimhdlRestartServer     call s:restartServer()
    command! VimhdlViewBuildSequence call s:printBuildSequence()
    command! -nargs=* -complete=dir 
                \ VimhdlCreateProjectFile call s:createProjectFile(<f-args>)
endfunction
" }
" { s:setupHooks() Setup filetype hooks
" ============================================================================
function! s:setupHooks(...) abort
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
    echom 'Restarting hdlcc server'
    let l:python = s:using_python2 ? 'python2' : 'python3'
    exec s:python_until_eof
_logger.info("Restarting hdlcc server")
vimhdl_client.shutdown()
del vimhdl_client
vimhdl_client = vimhdl.VimhdlClient(python=vim.eval('l:python'))
vimhdl_client.startServer()
_logger.info("hdlcc restart done")
EOF
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
function! s:printDependencies() abort
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
function! s:printBuildSequence() abort
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
    if !(count(['vhdl', 'verilog', 'systemverilog'], &filetype))
        call s:postWarning(
                    \"Can't create vim-hdl project file for this file type")
        return
    endif

    let b:local_arg = a:000
    let l:result = split(s:pyEval('vimhdl_client.createProjectFile()'), '\n', 1)

    let l:backup_file = ''

    if filewritable(g:vimhdl_conf_file) == 1
        let l:backup_file = g:vimhdl_conf_file . '.backup'

        " Warn if the backup already exists in the text
        if filereadable(l:backup_file)
            echohl WarningMsg | 
                        \ echom 'Overwriting existing backup file' | 
                        \ echohl None"
        end

        call rename(g:vimhdl_conf_file, l:backup_file)

    end

    let l:info = [
        \ '# This is the resulting project file, please review and save when done. The',
        \ '# g:vimhdl_conf_file variable has been temporarily changed to point to this',
        \ '# file should you wish to open HDL files and test the results. When finished,',
        \ '# close this buffer; you''ll be prompted to either use this file or revert to',
        \ '# the original one.',
        \ '#',
        \ '# ---- Everything up to this line will be automatically removed ----',
        \ '',
        \ ]

    " Open the file
    call execute('call writefile(l:info, "' . g:vimhdl_conf_file . '", "b")')
    call execute('call writefile(l:result, "' . g:vimhdl_conf_file . '", "ba")')
    call execute('new ' . g:vimhdl_conf_file)
    set filetype=vimhdltemp

endfunction
"}
" { vimhdl#onVimhdlTempQuit() Handles leaving the temporary config file edit
" ============================================================================
function! vimhdl#onVimhdlTempQuit()
    " Query if user if the current buffer should be indeed used as the config
    " file. If yes, remove the the backup, if not, rename the backup file back
    " to what g:vimhdl_conf_file points
    if &filetype != 'vimhdltemp'
        return
    end

    let l:lnum = 0
	let l:has_match = 0
	for l:line in getline('1', '$')
        let l:lnum += 1
        if l:line ==? '# ---- Everything up to this line will be automatically removed ----'
			let l:lnum += 1
			let l:has_match = 1
            echom 'Breaking at line ' . l:lnum
            break
        end
    endfor

	if l:has_match
		let l:actual_content = getline(l:lnum, '$')
	else
		let l:actual_content = getline('1', '$')
	end

    call execute('call writefile(l:actual_content, "' . g:vimhdl_conf_file . '", "b")')

endfunction
"}
" { vimhdl#setup() Main vim-hdl setup
" ============================================================================
function! vimhdl#setup() abort
    if !(exists('g:vimhdl_loaded') && g:vimhdl_loaded)
        let g:vimhdl_loaded = 1
        call s:setupPython()
        call s:setupCommands()
        augroup vimhdl
            call s:setupHooks('*.vhd', '*.vhdl', '*.v', '*.sv')
        augroup END
    endif

    if count(['vhdl', 'verilog', 'systemverilog'], &filetype)
        if !(exists('g:vimhdl_server_started') && g:vimhdl_server_started)
            let g:vimhdl_server_started = 1
            call s:pyEval('bool(vimhdl_client.startServer())')
        endif
    endif

endfunction
" }

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
