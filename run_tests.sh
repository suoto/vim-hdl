#!/usr/bin/env bash
# This file is part of vim-hdl.
#
# Copyright (c) 2015-2016 Andre Souto
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

##############################################################################
# Parse CLI arguments ########################################################
##############################################################################
RUNNER_ARGS=()

while [ -n "$1" ]; do
  case "$1" in
    -C) CLEAN_AND_QUIT="1";;
    -c) CLEAN="1";;
    *)	RUNNER_ARGS+=($1)
  esac
  shift
done

##############################################################################
# If we're not running inside CI, adjust some variables to mimic it ##########
##############################################################################
if [ -z "${CI}" ]; then
  if [ -z "${CI_TARGET}" ]; then
    CI_TARGET=vim
  fi

  if [ -z "${NVIM_TUI_ENABLE_CURSOR_SHAPE}" ]; then
    export NVIM_TUI_ENABLE_CURSOR_SHAPE=0
  fi

  VIRTUAL_ENV_DEST=~/dev/vimhdl_venv
  # if [ -z "${TRAVIS_PYTHON_VERSION}" ]; then
  #   TRAVIS_PYTHON_VERSION=3.5
  #   PYTHON=python${TRAVIS_PYTHON_VERSION}
  # else
  #   PYTHON=python
  # fi

  if [ -z "${VERSION}" ]; then
    if [ "${CI_TARGET}" == "neovim" ]; then
      VERSION=0.1.5
    else
      VERSION=master
    fi
  fi

  VROOM_DIR=~/dev/vroom/

fi

##############################################################################
# Common definitions for setting up the tests ################################
##############################################################################
if [ -n "${CI}" ]; then
  VROOM_DIR=${HOME}/vroom/
fi

##############################################################################
# Functions ##################################################################
##############################################################################
function _setup_vroom {
  if [ -d "$1" ]; then
    pushd "$1"
    git pull
  else
    git clone https://github.com/google/vroom \
      -b master --single-branch --depth 1 "$1"
    pushd "$1"
  fi

  python3 setup.py build

  set +e
  
  if [ "$(python3 setup.py install)" != "0" ]; then
    set -e
    python3 setup.py install --user
  fi

  popd
}

function _setup_ci_env {
  cmd="virtualenv --clear ${VIRTUAL_ENV_DEST}"

  if [ -n "${PYTHON}" ]; then
    cmd="$cmd --python=${PYTHON}"
  fi

  $cmd
  # shellcheck disable=SC1090
  source ${VIRTUAL_ENV_DEST}/bin/activate
}

function _install_packages {
  pip install git+https://github.com/suoto/rainbow_logging_handler
  pip install -r ./.ci/requirements.txt
  pip install -e ./dependencies/hdlcc/

  set +e

  if [ "$(pip3 install neovim)" != "0" ]; then
    pip3 install neovim --user
  fi

  
  if [ "$(pip install neovim)" != "0" ]; then
    pip install neovim --user
  fi

  set -e

}

function _cleanup_if_needed {
  if [ -n "${CLEAN_AND_QUIT}${CLEAN}" ]; then
    git clean -fdx || exit -1
    git submodule foreach --recursive git clean -fdx || exit -1
    pushd ../hdlcc_ci/hdl_lib
    git reset HEAD --hard
    popd
    pushd ../hdlcc_ci/vim-hdl-examples
    git reset HEAD --hard
    popd

    if [ -d "${VROOM_DIR}" ]; then rm -rf "${VROOM_DIR}"; fi

    if [ -n "${CLEAN_AND_QUIT}" ]; then exit; fi
  fi
}

function _setup_dotfiles {
  if [ "${CI}" == "true" ]; then
    DOT_VIM="$HOME/.vim"
    DOT_VIMRC="$HOME/.vimrc"
  else
    DOT_VIM="$HOME/dot_vim"
    DOT_VIMRC="$DOT_VIM/vimrc"
  fi

  mkdir -p "$DOT_VIM"
  if [ ! -d "$DOT_VIM/syntastic" ]; then
    git clone https://github.com/scrooloose/syntastic "$DOT_VIM/syntastic"
  fi
  if [ ! -d "$DOT_VIM/vim-hdl" ]; then
    ln -s "$PWD" "$DOT_VIM/vim-hdl"
  fi

  cp ./.ci/vimrc "$DOT_VIMRC"
}

##############################################################################
# Now to the script itself ###################################################
##############################################################################

set -e
set -x

# If we're not running on a CI server, create a virtual env to mimic its
# behaviour
if [ -z "${CI}" ]; then
  if [ -n "${CLEAN}" ] && [ -d "${VIRTUAL_ENV_DEST}" ]; then
    echo "Removing previous virtualenv"
    rm -rf ${VIRTUAL_ENV_DEST}
  fi

  _setup_ci_env
fi

_cleanup_if_needed
_install_packages
_setup_vroom "${VROOM_DIR}"

export PATH=${HOME}/builders/ghdl/bin/:${PATH}

_setup_dotfiles

if [ "${CI_TARGET}" == "vim" ]; then vim --version; fi
if [ "${CI_TARGET}" == "neovim" ]; then nvim --version; fi

echo "Terminal size is $COLUMNS x $LINES"

set +xe
python -m coverage run -m nose2 -s .ci/ "${RUNNER_ARGS[@]}"
RESULT=$?

python -m coverage combine
python -m coverage html

[ -z "${CI}" ] && [ -n "${VIRTUAL_ENV}" ] && deactivate

exit ${RESULT}

