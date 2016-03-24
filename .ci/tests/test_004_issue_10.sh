#!/usr/bin/env bash

set -x
./dependencies/hdlcc/hdlcc/runner.py .ci/test_projects/hdl_lib/ghdl.prj -cb -vvv

