#!/usr/bin/env bash

set -x

# Save the folder travis expects us to start
CURRENT=$(pwd)

if [ ! -f "${CACHE}/ghdl/bin/ghdl" ]; then
  mkdir -p ${CACHE}/ghdl

  # Setup GHDL
  cd ${CACHE}/ghdl
  wget ${GHDL_URL} -O ghdl.tar.gz
  tar zxvf ghdl.tar.gz
fi

cd $CURRENT

