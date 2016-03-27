#!/usr/bin/env bash

set -x
./dependencies/hdlcc/hdlcc/runner.py .ci/test_projects/hdl_lib/ghdl.prj -cb -vvv
vroom "$@" .ci/tests/test_004_issue_10.vroom

