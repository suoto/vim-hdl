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

" Inspired on YCM
let s:using_python2 = vimhdl#usingPython2()
let s:python_until_eof = s:using_python2 ? 'python << EOF' : 'python3 << EOF'
let s:default_config_file = 'vimhdl.prj'

" Gets the path to the nearest g:vimhdl_conf_file
function! s:GetProjectRoot(buffer) abort
  let l:project_root = ''
  let l:config_file = ale#Var(a:buffer, 'vimhdl_config')['project_file']

  if l:project_root is? ''
    let l:project_root = ale#path#FindNearestFile(a:buffer, l:config_file)

    let l:project_root = !empty(l:project_root) ? fnamemodify(l:project_root, ':h') : ''
  endif

  return l:project_root
endfunction

" Setup ALE to use vimhdl in the given filetypes
function! vimhdl#ale#setup(...) abort

  " Use the value set by g:vimhdl_conf_file if exists, otheriwise use the
  " default
  call ale#Set('vimhdl_config', 
        \ {'project_file': get(g:, 'vimhdl_conf_file', s:default_config_file)})

  for l:filetype in a:000
    try
      call ale#linter#Define(l:filetype, {
            \ 'name': 'vimhdl',
            \ 'lsp': 'stdio',
            \ 'language': l:filetype,
            \ 'executable': {b -> vimhdl#getLspCommand()[0]},
            \ 'command': {b -> join(vimhdl#getLspCommand(), ' ')},
            \ 'project_root': function('s:GetProjectRoot'),
            \ 'lsp_config': {b -> ale#Var(b, 'vimhdl_config')},
            \ })

      if exists('g:ale_linters')
        let l:existing = get(g:ale_linters, l:filetype, [])
        let g:ale_linters[l:filetype] = l:existing + ['vimhdl', ]
      else
        let g:ale_linters = { l:filetype : ['vimhdl', ] }
      endif

    catch /^Vim\%((\a\+)\)\=:E117/
      " If setting up ALE didn't work, just bail
      return
    endtry
  endfor
endfunction
"}}
