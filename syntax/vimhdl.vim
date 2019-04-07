" Quit when a (custom) syntax file was already loaded
if exists('b:current_syntax')
  finish
endif
"
syn clear
syn case ignore

syn  match vimhdlProjectFileComment  "#.*"          
syn  match vimhdlProjectFileComment  "^\s*\zs#.*$"  
syn  match vimhdlProjectFileComment  "\s\zs#.*$"    

syn match vimhdlProjectFileLang      display '\(^\|\[\)\<\(vhdl\|verilog\|systemverilog\)\>\(\s\|\]\)'
syn match vimhdlProjectFileBuilders  display '\<\(msim\|xvhdl\|ghdl\|fallback\)\>'
syn match vimhdlProjectFileSrc       display ' [a-z./][^ ]\+\.\(svh\|vh\|sv\|v\|vhd\)\>\s*' 

syn  keyword  vimhdlProjectFileKeywords builder global_build_flags batch_build_flags
syn  keyword  vimhdlProjectFileKeywords single_build_flags 

hi def link vimhdlProjectFileComment   Comment
hi def link vimhdlProjectFileKeywords  Keyword
hi def link vimhdlProjectFileLang      Identifier
hi def link vimhdlProjectFileBuilders  Constant
hi def link vimhdlProjectFileSrc       String

let b:current_syntax = 'vimhdlProjectFile'

" vim: ts=8 sw=2
