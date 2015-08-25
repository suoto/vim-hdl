"============================================================================
"File:        python.vim
"Description: Syntax checking plugin for syntastic.vim
"Maintainer:  Jan Wagner <jaydyou at janidom dot de>
"License:     This program is free software. It comes without any warranty,
"             to the extent permitted by applicable law. You can redistribute
"             it and/or modify it under the terms of the Do What The Fuck You
"             Want To Public License, Version 2, as published by Sam Hocevar.
"             See http://sam.zoy.org/wtfpl/COPYING for more details.
"
"============================================================================

if exists("g:loaded_syntastic_vhdl_python_checker")
    finish
endif
let g:loaded_syntastic_vhdl_python_checker = 1

let s:save_cpo = &cpo
set cpo&vim

function! SyntaxCheckers_vhdl_python_GetLocList() dict
    let makeprg = self.makeprgBuild({ 'args': '/home/souto/utils/vim/vim/bundle/hdl-syntax-checker/python/runner.py -t'})

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
