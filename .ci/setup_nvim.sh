#!/usr/bin/env bash

set -x
# Clone repo if the cached folder doesn't exists
if [ ! -d "${CACHE}/nvim-${VERSION}" ]; then
  git clone https://github.com/neovim/neovim "${CACHE}/nvim-${VERSION}"
fi


if [ ! -f "${CACHE}/nvim-${VERSION}/src/vim" -o "${VERSION}" == "master" ]; then
  cd "${CACHE}/nvim-${VERSION}"
  if [ "${VERSION}" == "master" ]; then
    # If we're testing the latest Vim version, we only pull the latest changes
    git clean -fdx
    git checkout master
    git pull
  else
    git checkout "${VERSION}"
  fi
  ./configure --with-features=huge --enable-pythoninterp --enable-gui=auto --with-x

  make all -j4
fi

cd "${TRAVIS_BUILD_DIR}"

$VIM_BINARY --version


