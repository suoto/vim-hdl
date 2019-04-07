#!/usr/bin/env bash

set -x

# Neovim working path defaults to home
if [ -z "${NEOVIM_BUILD_DIR}" ]; then NEOVIM_BUILD_DIR=${HOME}/neovim-build; fi

if [ ! -d "${NEOVIM_BUILD_DIR}" ]; then mkdir -p "${NEOVIM_BUILD_DIR}"; fi

if [ "${VERSION}" == "master" ]; then
  # Get the master version from git
  git clone --quiet https://github.com/neovim/neovim --depth 1 "${NEOVIM_BUILD_DIR}/neovim-master"
elif [ ! -f "${NEOVIM_BUILD_DIR}/neovim-${VERSION}" ]; then
  # Other release tags we get from Neovim's releases archive
  wget --quiet "https://github.com/neovim/neovim/archive/v${VERSION}.tar.gz" \
    -O "${NEOVIM_BUILD_DIR}/neovim.tar.gz"
  pushd "${NEOVIM_BUILD_DIR}" || exit
  tar zxvf "neovim.tar.gz"
  popd || exit
fi

if [ ! -f "${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin/nvim" ]; then
  pushd "${NEOVIM_BUILD_DIR}/neovim-${VERSION}" || exit
  make clean
  make CMAKE_BUILD_TYPE=Release -j
  popd || exit
fi

export PATH="${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin:${PATH}"
export VIM="${NEOVIM_BUILD_DIR}/neovim-${VERSION}/runtime"

# Ensure the binary being selected is the one we want
if [ ! "$(which nvim)" -ef "${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin/nvim" ]; then
  echo "Neovim binary points to \"$(which nvim)\" but it should point to \
        \"${NEOVIM_BUILD_DIR}/neovim-${VERSION}/build/bin/nvim\""
  exit -1
fi

set +x

nvim --version

