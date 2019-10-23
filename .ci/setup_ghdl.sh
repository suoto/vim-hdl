#!/usr/bin/env bash

set -x
set +e

CACHE_DIR="${HOME}/cache/"
GHDL_TAR_GZ="${CACHE_DIR}/ghdl.tar.gz"
INSTALLATION_DIR="${HOME}/builders/ghdl/"

mkdir -p "${CACHE_DIR}"
mkdir -p "${INSTALLATION_DIR}"
# CWD=$(pwd)

if [ ! -f "${GHDL_TAR_GZ}" ]; then
  wget "${GHDL_URL}" -O "${GHDL_TAR_GZ}"
fi

if [ ! -d "${INSTALLATION_DIR}/bin" ]; then
  mkdir -p "${INSTALLATION_DIR}"
  tar zxvf "${GHDL_TAR_GZ}" --directory "${INSTALLATION_DIR}"
fi

"${INSTALLATION_DIR}"/bin/ghdl --version
