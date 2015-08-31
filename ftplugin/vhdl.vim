" This file is part of hdl-check-o-matic.
"
" hdl-check-o-matic is free software: you can redistribute it and/or modify
" it under the terms of the GNU General Public License as published by
" the Free Software Foundation, either version 3 of the License, or
" (at your option) any later version.
"
" hdl-check-o-matic is distributed in the hope that it will be useful,
" but WITHOUT ANY WARRANTY; without even the implied warranty of
" MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
" GNU General Public License for more details.
"
" You should have received a copy of the GNU General Public License
" along with hdl-check-o-matic.  If not, see <http://www.gnu.org/licenses/>.
"
"============================================================================
" For Syntastic license, check http://sam.zoy.org/wtfpl/COPYING
"============================================================================

if exists("g:loaded_syntastic_vhdl_python_checker")
    finish
endif
let g:loaded_syntastic_vhdl_python_checker = 1

let s:save_cpo = &cpo
set cpo&vim

function! SyntaxCheckers_vhdl_python_GetLocList() dict
    let makeprg = self.makeprgBuild({ 'args': '/home/souto/utils/vim/vim/bundle/hdl-check-o-matic/python/runner.py -t'})

    let errorformat =
        \ '** %trror:\\s\*%f(%l):\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %trror:\\s\*%f(%l):\\s\*%m,' .
        \ '** %tarning:\\s\*%f\\s\*(%l)\\s\*:\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %tarning:\\s\*%f(%l):\\s\*%m,' .
        \ '** %trror:\\s\*(vcom-%n)\\s\*%m,' .
        \ '** %trror: %m,' .
        \ '** %tarning: %m,'

    return SyntasticMake({
        \ 'makeprg': makeprg,
        \ 'errorformat': errorformat })
endfunction

call g:SyntasticRegistry.CreateAndRegisterChecker({
    \ 'filetype': 'vhdl',
    \ 'name': 'python'})

let &cpo = s:save_cpo
unlet s:save_cpo

" vim: set sw=4 sts=4 et fdm=marker:
