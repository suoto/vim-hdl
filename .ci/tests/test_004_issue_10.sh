#!/usr/bin/env bash

set -x
# We'll run hdlcc standalone executable, we should have installed this first
hdlcc .ci/test_projects/hdl_lib/ghdl.prj -cb -vvv
vroom "$@" .ci/tests/test_004_issue_10.vroom

