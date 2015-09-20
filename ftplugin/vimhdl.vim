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

if exists("g:loaded_syntastic_vhdl_vimhdl_checker")
    finish
endif
let g:loaded_syntastic_vhdl_vimhdl_checker = 1

let s:save_cpo = &cpo
set cpo&vim

let s:vimhdl_path = escape(expand('<sfile>:p:h'), '\') . "/../"

function! s:setup()
python << EOF
import sys, os, vim
vimhdl_path = os.path.join(vim.eval( 's:vimhdl_path' ), 'python')
print "vimhdl_path = " + vimhdl_path
if vimhdl_path not in sys.path:
    sys.path.insert(0, vimhdl_path)
EOF
endfunction

call s:setup()

function! SyntaxCheckers_vhdl_vimhdl_GetLocList() dict
    let conf_file = get(g:, 'vimhdl_conf_file', '')
    let makeprg = self.makeprgBuild({'args': s:vimhdl_path . '/python/runner.py -l ' . conf_file . ' -t '})

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

call g:SyntasticRegistry.CreateAndRegisterChecker({
    \ 'exec'     : '/usr/bin/python2',
    \ 'filetype' : 'vhdl',
    \ 'name'     : 'vimhdl'})

let &cpo = s:save_cpo
unlet s:save_cpo

function! s:RebuildProject()
let conf_file = get(g:, 'vimhdl_conf_file', '')
echom "Rebuilding project " . conf_file
python << EOF
from project_builder import ProjectBuilder
ProjectBuilder.clean(vim.eval('conf_file'))
EOF
endfunction

command! HdlCheckOMaticRebuild call s:RebuildProject()

" vim: set sw=4 sts=4 et fdm=marker:
