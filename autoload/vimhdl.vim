" This file is part of vim-hdl.
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

" { vimhdl#setupPython()
" ============================================================================
" Setup Vim's Python environment to call vim-hdl within Vim
function! vimhdl#setupPython()
python << EOF
try:
    vimhdl_client
    _logger.warning("vimhdl client already exists, skiping")
except NameError:
    import sys, vim
    import os.path as p
    import logging

    # Add a null handler for issue #19
    logging.root.addHandler(logging.NullHandler())

    _logger = logging.getLogger(__name__)
    for path in (p.join(vim.eval('s:vimhdl_path'), 'python'),
                 p.join(vim.eval('s:vimhdl_path'), 'dependencies', 'requests'),
                 p.join(vim.eval('s:vimhdl_path'), 'dependencies', 'hdlcc')
             ):
        if path not in sys.path:
            path = p.abspath(path)
            if p.exists(path):
                sys.path.insert(0, path)
                _logger.info("Adding %s", path)
            else:
                _logger.warning("Path '%s' doesn't exists!", path)
    import vimhdl
    vimhdl_client = vimhdl.VimhdlClient()
EOF
endfunction
" }
"
" { vimhdl#setupCommands()
" ============================================================================
" Setup Vim's Python environment to call vim-hdl within Vim
function! vimhdl#setupCommands()
    command! VimhdlInfo call s:PrintInfo()

    " command! VimhdlListLibraries                   call vimhdl#listLibraries()
    " command! VimhdlListLibrariesAndSources         call vimhdl#listLibrariesAndSources()
    " command! VimhdlViewLog                         call vimhdl#viewLog()
    " command! VimhdlCleanProjectCache               call vimhdl#cleanProjectCache()

    " command! -nargs=? VimhdlAddSourceToLibrary call vimhdl#addSourceToLibrary(<f-args>)
    " command! -nargs=? VimhdlRemoveSourceFromLibrary call vimhdl#removeSourceFromLibrary(<f-args>)
endfunction
" }
"
" { vimhdl#setupHooks()
" ============================================================================
" Setup Vim's Python environment to call vim-hdl within Vim
function! vimhdl#setupHooks()
    autocmd! BufWritePost *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! BufEnter     *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! BufLeave     *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! FocusGained  *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! CursorMoved  *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! CursorMovedI *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! CursorHold   *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! CursorHoldI  *.vhd :py vimhdl_client.requestUiMessages()
    autocmd! InsertLeave  *.vhd :py vimhdl_client.requestUiMessages()
endfunction
" }
"
" { vimhdl#setup()
" ============================================================================
" Setup Vim's Python environment to call vim-hdl within Vim
function! vimhdl#setup()
    if exists('g:vimhdl_loaded') && g:vimhdl_loaded 
        return
    endif

    let g:vimhdl_loaded = 1

    call vimhdl#setupPython()
    call vimhdl#setupCommands()
    call vimhdl#setupHooks()

endfunction
" }
" { vimhdl#setupHooks()
" ============================================================================
" Setup Vim's Python environment to call vim-hdl within Vim
function! s:PrintInfo()
  echom "vimhdl debug info"
  let debug_info = pyeval('vimhdl_client.getVimhdlInfo()')
  for line in split( debug_info, "\n" )
    echom '- ' . line
  endfor
endfunction
" }
"
" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
