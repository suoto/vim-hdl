#!/usr/bin/env bash
# This file is part of vim-hdl.
#
# Copyright (c) 2015 - 2019 suoto (Andre Souto)
#
# vim-hdl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# vim-hdl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.

set -xe

DOCKER_TAG="${DOCKER_TAG:-latest}"
PATH_TO_THIS_SCRIPT=$(readlink -f "$(dirname "$0")")
DOCKERFILE=$PATH_TO_THIS_SCRIPT/Dockerfile
CONTEXT=$(git -C "$(PATH_TO_THIS_SCRIPT)" rev-parse --show-toplevel)

docker build -t suoto/vim_hdl_test:"$DOCKER_TAG" -f "$DOCKERFILE" "$CONTEXT"
