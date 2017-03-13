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
"============================================================================
" For Syntastic license, check http://sam.zoy.org/wtfpl/COPYING
"============================================================================

" { Pre setup
if exists('g:loaded_syntastic_vhdl_vimhdl_checker')
    finish
endif
let g:loaded_syntastic_vhdl_vimhdl_checker = 1

if !exists('g:syntastic_vhdl_vimhdl_sort')
    let g:syntastic_vhdl_vimhdl_sort = 0 " vim-hdl returns sorted messages
endif

let s:save_cpo = &cpoptions
set cpoptions&vim
" }
" { vimhdl availability checker
function! SyntaxCheckers_vhdl_vimhdl_IsAvailable() dict
    if has('python') || has('python3')
        return 1
    endif
    return 0
endfunction

" { vimhdl location list assembler
function! SyntaxCheckers_vhdl_vimhdl_GetLocList() dict
    return vimhdl#getMessagesForCurrentBuffer()
endfunction
" }

" { Register vimhdl within Syntastic
call g:SyntasticRegistry.CreateAndRegisterChecker({
    \ 'filetype' : 'vhdl',
    \ 'name'     : 'vimhdl'})
" }

let &cpoptions = s:save_cpo
unlet s:save_cpo

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
