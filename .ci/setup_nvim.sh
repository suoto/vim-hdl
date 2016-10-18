#!/usr/bin/env bash

set -x

if [ -z "${NEOVIM_BUILD_DIR}" ]; then
  NEOVIM_BUILD_DIR=${HOME}
fi

if [ ! -d "${NEOVIM_BUILD_DIR}" ]; then
  mkdir -p "${NEOVIM_BUILD_DIR}"
fi

if [ "${VERSION}" == "master" ]; then
  if [ ! -f "${NEOVIM_BUILD_DIR}/neovim-master" ]; then
    git clone https://github.com/neovim/neovim --depth 1 "${NEOVIM_BUILD_DIR}/neovim-master"
  else
    cd "${NEOVIM_BUILD_DIR}/neovim-master" && git pull && cd -
  fi
elif [ ! -f "${NEOVIM_BUILD_DIR}/neovim-${VERSION}" ]; then
  wget "https://github.com/neovim/neovim/archive/v${VERSION}.tar.gz" \
    -O "${NEOVIM_BUILD_DIR}/neovim.tar.gz"
  cd "${NEOVIM_BUILD_DIR}"
  tar zxvf "neovim.tar.gz"
fi

if [ ! -f "${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin/nvim" ]; then
  cd "${NEOVIM_BUILD_DIR}/neovim-${VERSION}"
  make clean
  make CMAKE_BUILD_TYPE=Release -j4
fi

export PATH="${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin:${PATH}"
export VIM="${NEOVIM_BUILD_DIR}/neovim-${VERSION}/runtime"

cd "${TRAVIS_BUILD_DIR}"

# Ensure the binary being selected is the one we want
if [ ! "$(which nvim)" -ef "${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin/nvim" ]; then
  echo "Neovim binary points to \"$(which nvim)\" but it should point to \
        \"${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin/nvim\""
  exit -1
fi

set +x

nvim --version

