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

    " Prefer the local version of the config file
    if exists('b:vimhdl_conf_file')
        let l:config_file = b:vimhdl_conf_file
    elseif exists('g:vimhdl_conf_file')
        let l:config_file = g:vimhdl_conf_file
    else
        " If the configuration wasn't set, create a file and set
        " vimhdl_conf_file to point to it. Main idea here is give a headstart
        " to someone who just installed the plugin
        let l:config_file = 'vimhdl.prj'
        call s:postWarning('g:vimhdl_conf_file is not set. Will set it to '''.
                    \ l:config_file . ''' and use it to write the resulting' .
                    \ ' project file')
        let g:vimhdl_conf_file = l:config_file
        call writefile([''], g:vimhdl_conf_file, 'b')
    end

    if filewritable(l:config_file) == 1
        let l:backup_file = l:config_file . '.backup'

        " Warn if the backup already exists in the text
        if filereadable(l:backup_file)
            call s:postWarning('Overwriting existing backup file')
        end

        call rename(l:config_file, l:backup_file)

    else
        throw 'vim-hdl : Can''t create project file. Settings point to ''' .
                    \ l:config_file . ''' but the file is not writable; ' .
                    \ 'check file and/or directory permissions and try again.'
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
    call execute('call writefile(l:info, "' . l:config_file . '", "b")')
    call execute('call writefile(l:result, "' . l:config_file . '", "ba")')
    call execute('new ' . l:config_file)
    let b:config_file = l:config_file
    let b:backup_file = l:backup_file

    augroup vimhdl
        call execute('autocmd QuitPre ' . l:config_file . ' :call s:onVimhdlTempQuit()')
    augroup END

    set filetype=vimhdl

endfunction
"}
" { s:onVimhdlTempQuit() Handles leaving the temporary config file edit
" ============================================================================
function! s:onVimhdlTempQuit()
    " Query if user if the current buffer should be indeed used as the config
    " file. If yes, remove the the backup, if not, rename the backup file back
    " to what g:vimhdl_conf_file points

    " Disable autocmd, it's only set when we actually open the buffer for
    " editing
    autocmd! vimhdl QuitPre

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

    if filereadable(b:backup_file)
        let l:confirm_text = 'Replace the existing config file contents with' .
                    \ ' the contents of the current buffer or restore backup?'
        let choice = confirm(l:confirm_text, "&Update\n&Restore backup")
    else
        let l:confirm_text = 'Save current buffer as config file? (can''t '
                    \ 'restore backup because no backup file was found)'
        let choice = confirm(l:confirm_text, "&Yes\n&No")
    end

    call execute('call writefile(l:actual_content, "' . b:config_file . '", "b")')
    call s:postInfo('Updated contents of g:vimhdl_conf_file (' . b:config_file  . ')')

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
