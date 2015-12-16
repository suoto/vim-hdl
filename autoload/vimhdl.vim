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
import sys, os, vim
import threading
vimhdl_path = os.path.join(vim.eval('s:vimhdl_path'), 'python')
if vimhdl_path not in sys.path:
    sys.path.insert(0, vimhdl_path)
import vimhdl
from vimhdl.project_builder import ProjectBuilder
from vimhdl.static_check import vhdStaticCheck
from vimhdl.config import Config
Config._setupToolchain()
import vimhdl
EOF
endfunction
" }

" { vimhdl#getConfFile()
" ============================================================================
" Gets the configuration file giving preference to the buffer version
function! vimhdl#getConfFile()
    if exists("b:vimhdl_conf_file")
        let conf_file = b:vimhdl_conf_file
    else
        let conf_file = get(g:, 'vimhdl_conf_file', '')
    endif
    if !filereadable(conf_file)
        let conf_file = ''
    endif
    return conf_file

endfunction
" }

" { vimhdl#rebuildProject()
" ============================================================================
" Rebuilds the current project by running ProjectBuilder.clean method
function! vimhdl#rebuildProject()
    let conf_file = vimhdl#getConfFile()
    echom "Rebuilding project " . conf_file

    python << EOF
ProjectBuilder.clean(vim.eval('conf_file'))
EOF

endfunction
" }

" { vimhdl#listLibraries()
" ============================================================================
" List libraries found
function! vimhdl#listLibraries()

python << EOF
print "%d libraries:" % len(project.libraries)
print "\n".join(project.libraries.keys())
EOF

endfunction
" }

" { vimhdl#listLibrariesAndSources()
" ============================================================================
" List libraries and their respective sources
function! vimhdl#listLibrariesAndSources()

python << EOF
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
print "\n".join(open('/tmp/build.log').read().split("\n")[-30:])
EOF

endfunction
" }

" { vimhdl#cleanCache()
" Clean internal vim-hdl cache
function! vimhdl#cleanProjectCache()

python << EOF
project.cleanCache()
EOF

endfunction
" }

" { vimhdl#addSourceToLibrary(library, source=<current>)
" Adds <source> to library <library>. If source is not defined, use the
" current buffer name
function! vimhdl#addSourceToLibrary(...)
    let library = a:1
    if a:0 == 1
        let source = expand('%:p')
    elseif a:0 == 2
        let source = a:2
    endif


python << EOF
_source = vim.eval('source')
_library = vim.eval('library')
try:
    project.libraries[_library].addSources(_source)
    project.saveCache()

    vim.command("echom \"Added source '%s' to library '%s'\"" % \
        (_source, _library))
except Exception as e:
    vim.command("echom \"Error adding source '%s' to library '%s': '%s'\"" % \
        (_source, _library, str(e)))
finally:
    del _source, _library
EOF



endfunction
" }

" { vimhdl#removeSourceFromLibrary(library, source=<current>)
" Adds <source> to library <library>. If source is not defined, use the
" current buffer name
function! vimhdl#removeSourceFromLibrary(...)
    let library = a:1
    if a:0 == 1
        let source = expand('%:p')
    elseif a:0 == 2
        let source = a:2
    endif

    let conf_file = vimhdl#getConfFile()

python << EOF
_source = vim.eval('source')
_library = vim.eval('library')
try:
    project = ProjectBuilder(library_file=vim.eval('conf_file'))
    project.libraries[_library].removeSources(_source)
    project.saveCache()

    vim.command("echom \"Removed source '%s' from library '%s'\"" % \
        (_source, _library))
except Exception as e:
    vim.command("echom \"Error removing source '%s' from library '%s': '%s'\"" % \
        (_source, _library, str(e)))
finally:
    del _source, _library
EOF

endfunction
" }

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
