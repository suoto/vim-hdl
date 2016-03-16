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

" { vimhdl#setup()
" ============================================================================
" Setup Vim's Python environment to call vim-hdl within Vim
function! vimhdl#setup()

    if exists('b:vimhdl_loaded') && b:vimhdl_loaded 
        return
    endif

    let b:vimhdl_loaded = 1

python << EOF
import sys, vim
import os.path as p
import logging
_logger = logging.getLogger(__name__)
for path in (p.join(vim.eval('s:vimhdl_path'), 'python'),
             p.join(vim.eval('s:vimhdl_path'), 'dependencies', 'hdlcc')
         ):
    if path not in sys.path:
        _logger.info("Adding %s", path)
        sys.path.insert(0, path)
import vimhdl
EOF
endfunction
" }

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
