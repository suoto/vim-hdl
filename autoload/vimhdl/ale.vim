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
let s:python_command = s:using_python2 ? 'py ' : 'py3 '

function! s:GetProjectRoot(buffer) abort "{{
  let l:project_root = ''

  if l:project_root is? ''
    let l:project_root = ale#path#FindNearestFile(a:buffer, 'msim.prj')

    let l:project_root = !empty(l:project_root) ? fnamemodify(l:project_root, ':h') : ''
  endif

  return l:project_root
endfunction
"}}

" {{ vimhdl#ale#setup() Setup ALE to use vimhdl in the given filetypes
" ============================================================================
function! vimhdl#ale#setup(...) abort

  let g:ale_vimhdl_options = {'config_file': 'msim.prj'}

  for l:filetype in a:000
    call vimhdl#pyEval('_logger.debug("Setting up ALE support for %s" % "' . l:filetype . '")')

    try
      call ale#linter#Define(l:filetype, {
            \ 'name': 'vimhdl',
            \ 'lsp': 'stdio',
            \ 'executable': 'python3',
            \ 'command': function('vimhdl#ale#getLspCommand'),
            \ 'language': l:filetype,
            \ 'project_root': function('s:GetProjectRoot'),
            \ 'initialization_options': {b -> ale#Var(b, 'vimhdl_options')},
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
"
function! vimhdl#ale#getLspCommand(buffer) " {{
  let l:python = s:using_python2 ? 'python2' : 'python3'
  let l:hdlcc_server = vimhdl#basePath() 
              \ . '/dependencies/hdlcc/hdlcc/hdlcc_server.py'

  return join([
              \ l:python,
              \ l:hdlcc_server,
              \ '--stderr', '/tmp/hdlcc-stderr.log',
              \ '--log-level', 'DEBUG',
              \ '--log-stream', '/tmp/hdlcc.log',
              \ '--lsp'
              \ ],
              \ ' ')
endfunction

" vim: set foldmarker={{,}} foldlevel=10 foldmethod=marker :
