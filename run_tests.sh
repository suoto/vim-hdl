#!/usr/bin/env bash
# This file is part of vim-hdl.
#
# vim-hdl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# vim-hdl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.

RUNNER_ARGS=

while [ -n "$1" ]; do
	case "$1" in
    -C) CLEAN_AND_QUIT="1";;
		-c) CLEAN="1";;
		*)	RUNNER_ARGS+=" $1"
	esac
  shift
done

# set -x
set +e

if [ -n "${CLEAN_AND_QUIT}${CLEAN}" ]; then
  git clean -fdx || exit -1
  git submodule foreach --recursive git clean -fdx || exit -1
  cd ./.ci/test_projects/hdl_lib && git reset HEAD --hard
  cd -
  [ -n "${CLEAN_AND_QUIT}" ] && exit
fi

if [ "${CI}" == "true" ]; then
  DOT_VIM="$HOME/.vim"
  DOT_VIMRC="$HOME/.vimrc"
else
  DOT_VIM="$HOME/dot_vim"
  DOT_VIMRC="$DOT_VIM/vimrc"
fi

export PATH=${HOME}/builders/ghdl/bin/:${PATH}

mkdir -p "$DOT_VIM"
if [ ! -d "$DOT_VIM/syntastic" ]; then
  git clone https://github.com/scrooloose/syntastic "$DOT_VIM/syntastic"
fi
if [ ! -d "$DOT_VIM/vim-hdl" ]; then
  ln -s "$PWD" "$DOT_VIM/vim-hdl"
fi

echo """
syntax on
filetype plugin indent on
set nocompatible

set shortmess=filnxtToO

set rtp+=${DOT_VIM}/syntastic
set rtp+=${DOT_VIM}/vim-hdl

let g:syntastic_always_populate_loc_list = 1
let g:syntastic_auto_loc_list = 1
let g:syntastic_check_on_open = 0
let g:syntastic_check_on_wq = 1

let g:syntastic_vhdl_vimhdl_sort = 0
let g:syntastic_vhdl_checkers = ['vimhdl']

python << EOF
import logging, os
import coverage


cov = coverage.Coverage(config_file='.coveragerc')
cov.start()

def onVimLeave():
    global cov
    cov.stop()
    cov.save()

def setupLogging():
    log_path = '../'
    log_file = os.path.join(log_path, 'vim.log')
    i = 0
    while True:
        try:
            open(log_file, 'a').close()
            break
        except IOError:
            print \"Error opening '%s'\" % log_file
            log_file = os.path.join(log_path, 'vim_log_%d_%d.log' % (os.getpid(), i))
            i += 1
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('nose2').setLevel(logging.INFO)
    logging.getLogger('hdlcc').setLevel(logging.WARNING)
    logging.getLogger('hdlcc.project_builder').setLevel(logging.WARNING)
    logging.getLogger('neovim').setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file)
    log_format = \"%(levelname)-8s || %(name)-30s || %(message)s\"
    file_handler.formatter = logging.Formatter(log_format)
    logging.root.addHandler(file_handler)
    logging.root.setLevel(logging.DEBUG)

setupLogging()
EOF

autocmd! VimLeavePre * :py onVimLeave()


""" > "$DOT_VIMRC"

RESULT=0

.ci/tests/run_all.py
RESULT=$(($? || ${RESULT}))

coverage combine
coverage html
exit ${RESULT}

