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
"
augroup vimhdl
    autocmd! BufEnter *             :call vimhdl#setup()
    autocmd! Filetype vhdl          :call vimhdl#setup()
    autocmd! Filetype verilog       :call vimhdl#setup()
    autocmd! Filetype systemverilog :call vimhdl#setup()
augroup END

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
