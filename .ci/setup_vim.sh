#!/usr/bin/env bash

set -x

if [ "${VERSION}" == "latest" ]; then
  sudo bash -c 'apt-get update && apt-get upgrade vim-gnome'
elif [ "${VERSION}" == "master" ]; then
  # Clone repo if the cached folder doesn't exists
  if [ ! -d "${CACHE}/vim-${VERSION}" ]; then
    git clone --quiet https://github.com/vim/vim "${CACHE}/vim-${VERSION}"
  fi

  pushd "${CACHE}/vim-${VERSION}" || exit
  git clean -fdx
  git checkout "${VERSION}"

  if [[ ${TRAVIS_PYTHON_VERSION} == 3* ]]; then
    ./configure --with-features=huge       \
                --prefix="$HOME/.local"    \
                --enable-python3interp=yes \
                --enable-gui=auto          \
                --with-x
  else
    ./configure --with-features=huge      \
                --prefix="$HOME/.local"   \
                --enable-pythoninterp=yes \
                --enable-gui=auto         \
                --with-x
  fi

  make -j
  make install
  popd || exit

fi

set +x

vim --version
