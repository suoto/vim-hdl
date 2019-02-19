setlocal bufhidden=delete
setlocal noswapfile

augroup vimhdl
  autocmd QuitPre * :call vimhdl#onVimhdlTempQuit()
augroup END
