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
  cd ./.ci/test_projects/vim-hdl-examples && git reset HEAD --hard
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

cp ./.ci/vimrc "$DOT_VIMRC"

RESULT=0

# .ci/tests/run_all.py ${RUNNER_ARGS}
set -x
nose2 -s .ci/ ${RUNNER_ARGS}
RESULT=$(($? || ${RESULT}))

coverage combine
coverage html
exit ${RESULT}

