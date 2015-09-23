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
python << EOF
import sys, os, vim
vimhdl_path = os.path.join(vim.eval('s:vimhdl_path'), 'python')
if vimhdl_path not in sys.path:
    sys.path.insert(0, vimhdl_path)
from project_builder import ProjectBuilder
EOF
endfunction
" }

" { vimhdl#getConfFile()
" ============================================================================
" Gets the configuration file giving preference to the buffer version
function! vimhdl#getConfFile()
    if exists("b:vimhdl_conf_file")
        return b:vimhdl_conf_file
    else
        return get(g:, 'vimhdl_conf_file', '')
    endif
endfunction
" }

" { vimhdl#rebuildProject()
" ============================================================================
" Rebuilds the current project by running ProjectBuilder.clean method
function! vimhdl#rebuildProject()
    let conf_file = vimhdl#getConfFile()
    echom "Rebuilding project " . conf_file
    call vimhdl#setup()

    python << EOF
import sys, os, vim
vimhdl_path = os.path.join(vim.eval('s:vimhdl_path'), 'python')
sys.path.insert(0, vimhdl_path)
from project_builder import ProjectBuilder
ProjectBuilder.clean(vim.eval('conf_file'))
EOF

endfunction
" }

" { vimhdl#listLibraries()
" ============================================================================
" List libraries found
function! vimhdl#listLibraries()
    let conf_file = vimhdl#getConfFile()

python << EOF
project = ProjectBuilder(library_file=vim.eval('conf_file'))
print "%d libraries:" % len(project.libraries)
print "\n".join(project.libraries.keys())
EOF

endfunction
" }

" { vimhdl#listLibrariesAndSources()
" ============================================================================
" List libraries and their respective sources
function! vimhdl#listLibrariesAndSources()
    let conf_file = vimhdl#getConfFile()

python << EOF
project = ProjectBuilder(library_file=vim.eval('conf_file'))
for lib in project.libraries.values():
    print "Library: %s (%d sources)" % (lib.name, len(lib.sources))
    for source in lib.sources:
        print " - %s" % source
EOF

endfunction
" }

" { vimhdl#viewLog()
" Shows vim-hdl log
function! vimhdl#viewLog()
python << EOF
print open('/tmp/build.log').read()
EOF

endfunction
" }

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
