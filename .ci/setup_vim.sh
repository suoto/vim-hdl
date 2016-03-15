#!/usr/bin/env bash

set -x

# Clone repo if the cached folder doesn't exists
if [ ! -d "${CACHE}/vim-${VIM_VERSION}" ]; then
  git clone https://github.com/vim/vim ${CACHE}/vim-${VIM_VERSION}
fi


if [ ! -f "${CACHE}/vim-${VIM_VERSION}/src/vim" ]; then
  cd ${CACHE}/vim-${VIM_VERSION}
  if [ "${VIM_VERSION}" == "master" ]; then
    # If we're testing the latest Vim version, we only pull the latest changes
    git checkout master
    git pull
  else
    git checkout ${VIM_VERSION}
  fi
  ./configure --with-features=huge --enable-pythoninterp --enable-gui=auto --with-x

  make all -j4
fi

cd ${TRAVIS_BUILD_DIR}

$VIM_BINARY --version

