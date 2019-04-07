#!/usr/bin/env bash

set -x

# Save the folder travis expects us to start
if [ ! -f "${CACHE}/ghdl/bin/ghdl" ]; then
  mkdir -p "${CACHE}/ghdl"

  # Setup GHDL
  pushd "${CACHE}/ghdl" || exit
  wget --quiet "${GHDL_URL}" -O ghdl.tar.gz
  tar zxvf ghdl.tar.gz
  popd || exit

fi
