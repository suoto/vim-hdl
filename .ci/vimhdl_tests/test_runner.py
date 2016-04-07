# This file is part of vim-hdl.
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

# pylint: disable=function-redefined, missing-docstring, protected-access

import os
import os.path as p
import logging
import subprocess as subp

from nose2.tools import such

_PATH_TO_TESTS = p.join(".ci", "vroom")
_CI = os.environ.get("CI", None) is not None

_logger = logging.getLogger(__name__)

def _getVroomArgs():
    args = ['-u']
    if _CI:
        args += [p.expanduser('~/.vimrc')]
        args += ['-d0.5', '-t3']
    else:
        args += [p.expanduser('~/dot_vim/vimrc')]
        args += ['-d0.2', '-t1']

    return args

with such.A('vim-hdl test') as it:

    def _gitClean(path=None):
        if path is None:
            path = "."
        start_path = p.abspath(".")
        dest_path = p.abspath(path)
        if start_path != dest_path:
            _logger.info("Changing from '%s' to '%s'", start_path, dest_path)
            os.chdir(dest_path)

        _logger.info("Cleaning up non-git files")
        for line in subp.check_output(['git', 'clean', '-fdx']).splitlines():
            _logger.info("> " + line)

        if start_path != dest_path:
            _logger.info("Changing back to '%s'", start_path)
            os.chdir(start_path)

    def _cleanHdlLib():
        _logger.info("Resetting hdl_lib")
        start_path = p.abspath(".")
        dest_path = p.join(".ci", "test_projects", "hdl_lib")
        os.chdir(dest_path)
        for line in \
            subp.check_output(['git', 'reset', 'HEAD', '--hard']).splitlines():

            _logger.info("> " + line)

        _gitClean()

        _logger.info("git status")
        for line in \
            subp.check_output(['git', 'status', '--porcelain']).splitlines():

            _logger.info("> " + line)

        os.chdir(start_path)

    @it.has_setup
    def setup():
        _gitClean()
        _cleanHdlLib()

    @it.has_teardown
    def teardown():
        #  _gitClean()
        _cleanHdlLib()

    with it.having("a session with multiple files to edit"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS,
                                "test_001_editing_multiple_files.vroom")
            try:
                subp.check_call(['vroom', vroom_test, ] + _getVroomArgs())
            except subp.CalledProcessError:
                it.fail("Test failed")

    with it.having("no project configured"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS,
                                'test_002_no_project_configured.vroom')
            try:
                subp.check_call(['vroom', vroom_test, ] + _getVroomArgs())
            except subp.CalledProcessError:
                it.fail("Test failed")

    with it.having("a project file but no builder working"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS,
                                'test_003_with_project_without_builder.vroom')
            try:
                subp.check_call(['vroom', vroom_test, ] + _getVroomArgs())
            except subp.CalledProcessError:
                it.fail("Test failed")

    with it.having("built project with hdlcc standalone before editing"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS, 'test_004_issue_10.vroom')
            cmd = ['hdlcc', '.ci/test_projects/hdl_lib/ghdl.prj', '-cb', '-vvv']

            _logger.info(cmd)
            exc = None
            try:
                output = subp.check_output(cmd).splitlines()
            except subp.CalledProcessError as exc:
                output = list(exc.output.splitlines())

            if exc is None:
                for line in output:
                    _logger.info("> " + line)
            else:
                for line in output:
                    _logger.warning("> " + line)

            try:
                subp.check_call(['vroom', vroom_test, ] + _getVroomArgs())
            except subp.CalledProcessError:
                it.fail("Test failed")

it.createTests(globals())

