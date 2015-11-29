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

call vimhdl#setup()

if !exists("g:syntastic_vhdl_vimhdl_sort")
    let g:syntastic_vhdl_vimhdl_sort = 0 " vim-hdl returns sorted messages
endif

let s:save_cpo = &cpo
set cpo&vim

" { vimhdl location list assembler
function! SyntaxCheckers_vhdl_vimhdl_GetLocList() dict
    let loclist = []

py <<EOF
loclist = vim.bindeval('loclist')
loclist.extend(vimhdl.vim_client.getMessages(vim.current.buffer))
EOF
    return loclist

endfunction
" }

" { Register vimhdl within Syntastic
call g:SyntasticRegistry.CreateAndRegisterChecker({
    \ 'exec'     : '',
    \ 'filetype' : 'vhdl',
    \ 'name'     : 'vimhdl'})
" }

let &cpo = s:save_cpo
unlet s:save_cpo

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
