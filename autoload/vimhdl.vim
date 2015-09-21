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

" Setup Vim's Python environment to call vim-hdl within Vim
function! vimhdl#setup()
python << EOF
import sys, os, vim
vimhdl_path = os.path.join(vim.eval( 's:vimhdl_path' ), 'python')
if vimhdl_path not in sys.path:
    sys.path.insert(0, vimhdl_path)
EOF
endfunction

function! vimhdl#rebuildProject()
    let conf_file = get(g:, 'vimhdl_conf_file', '')
    echom "Rebuilding project " . conf_file
    call vimhdl#setup()

    python << EOF
import sys, os, vim
vimhdl_path = os.path.join(vim.eval( 's:vimhdl_path' ), 'python')
sys.path.insert(0, vimhdl_path)
try:
    from project_builder import ProjectBuilder
except ImportError:
    print "\n".join(sys.path)
ProjectBuilder.clean(vim.eval('conf_file'))
EOF

endfunction

" vim: set sw=4 sts=4 et fdm=marker:
