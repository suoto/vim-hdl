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
"============================================================================
" For Syntastic license, check http://sam.zoy.org/wtfpl/COPYING
"============================================================================

" { Pre setup
if exists("g:loaded_syntastic_vhdl_vimhdl_checker")
    finish
endif
let g:loaded_syntastic_vhdl_vimhdl_checker = 1

if exists("g:syntastic_vhdl_checkers")
    let g:syntastic_vhdl_checkers += ['vimhdl']
else
    let g:syntastic_vhdl_checkers = ['vimhdl']
endif
let s:save_cpo = &cpo
set cpo&vim
" }

let s:vimhdl_path = escape(expand('<sfile>:p:h'), '\') . "/../"
call vimhdl#setup()

" { vimhdl Syntastic definition
function! SyntaxCheckers_vhdl_vimhdl_GetLocList() dict
    let conf_file = vimhdl#getConfFile()
    let makeprg = self.makeprgBuild({
                \ 'exe'       : s:vimhdl_path . '/python/vimhdl/runner.py ' . conf_file,
                \ 'args'      : '--sources',
                \ 'post_args' : '--build'})

    let errorformat =
        \ '** %tarning:\\s\*[\\d\\+]\\s\*%f(%l):\\s\*%m,' .
        \ '** %tarning:\\s\*[\\d\\+]\\s\*%f(%l):\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %trror:\\s\*%f(%l):\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %trror:\\s\*%f(%l):\\s\*%m,' .
        \ '** %tarning:\\s\*%f\\s\*(%l)\\s\*:\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %tarning:\\s\*%f(%l):\\s\*%m,' .
        \ '** %trror:\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %trror: %m,' .
        \ '** %tarning: %m'

    return SyntasticMake({
        \ 'makeprg': makeprg,
        \ 'errorformat': errorformat })
endfunction
" }

" { Register vimhdl within Syntastic
call g:SyntasticRegistry.CreateAndRegisterChecker({
    \ 'exec'     : 'python',
    \ 'filetype' : 'vhdl',
    \ 'name'     : 'vimhdl'})
" }

let &cpo = s:save_cpo
unlet s:save_cpo

" { Vimhdl commands
command! VimhdlRebuildProject                  call vimhdl#rebuildProject()
command! VimhdlListLibraries                   call vimhdl#listLibraries()
command! VimhdlListLibrariesAndSources         call vimhdl#listLibrariesAndSources()
command! VimhdlViewLog                         call vimhdl#viewLog()
command! VimhdlCleanProjectCache               call vimhdl#cleanProjectCache()

command! -nargs=? VimhdlAddSourceToLibrary call vimhdl#addSourceToLibrary(<f-args>)
command! -nargs=? VimhdlRemoveSourceFromLibrary call vimhdl#removeSourceFromLibrary(<f-args>)
" }
"
" { Autocommands
autocmd! BufRead     *.vhd :py vimhdl.vim_client.onBufRead()
autocmd! BufWrite    *.vhd :py vimhdl.vim_client.onBufWrite()
autocmd! BufEnter    *.vhd :py vimhdl.vim_client.onBufEnter()
autocmd! BufLeave    *.vhd :py vimhdl.vim_client.onBufLeave()
autocmd! BufWinEnter *.vhd :py vimhdl.vim_client.onBufWinEnter()
autocmd! BufWinLeave *.vhd :py vimhdl.vim_client.onBufWinLeave()
autocmd! FocusGained *.vhd :py vimhdl.vim_client.onFocusGained()
autocmd! FocusLost   *.vhd :py vimhdl.vim_client.onFocusLost()
autocmd! CursorHold  *.vhd :py vimhdl.vim_client.onCursorHold()
autocmd! CursorHoldI *.vhd :py vimhdl.vim_client.onCursorHoldI()
autocmd! WinEnter    *.vhd :py vimhdl.vim_client.onWinEnter()
autocmd! WinLeave    *.vhd :py vimhdl.vim_client.onWinLeave()
autocmd! TabEnter    *.vhd :py vimhdl.vim_client.onTabEnter()
autocmd! TabLeave    *.vhd :py vimhdl.vim_client.onTabLeave()


" autocmd! BufWrite *.vhd :call vimhdl#onBufWrite()
" autocmd! BufEnter *.vhd :call vimhdl#onBufEnter()
" autocmd! BufWrite *.vhd :call vimhdl#onBufWrite()
" }

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
