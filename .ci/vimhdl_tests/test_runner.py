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
PATH_TO_HDLCC = p.join("dependencies", "hdlcc")
_CI = os.environ.get("CI", None) is not None

_logger = logging.getLogger(__name__)

def getTestCommand(test_name):
    #  base_log_name = test_name + ".{0}"

    args = []
    args += ['vroom', ]
    #  args += ['--out',           base_log_name.format('out.log')]
    #  args += ['--dump-messages', base_log_name.format('msg.log')]
    #  args += ['--dump-commands', base_log_name.format('cmd.log')]
    #  args += ['--dump-syscalls', base_log_name.format('sys.log')]
    args += ['-u', p.expanduser('~/.vimrc' if _CI else '~/dot_vim/vimrc')]
    args += ['-d0.5', '-t3'] if _CI else ['-d0.2', '-t1']

    args += [test_name]

    return args

with such.A('vim-hdl test') as it:

    def gitClean(path=None):
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

    def cleanHdlLib():
        _logger.info("Resetting hdl_lib")
        start_path = p.abspath(".")
        dest_path = p.join(".ci", "test_projects", "hdl_lib")
        os.chdir(dest_path)
        for line in \
            subp.check_output(['git', 'reset', 'HEAD', '--hard']).splitlines():

            _logger.info("> " + line)

        gitClean()

        _logger.info("git status")
        for line in \
            subp.check_output(['git', 'status', '--porcelain']).splitlines():

            _logger.info("> " + line)

        os.chdir(start_path)

    def pipInstallHdlcc():
        cmd = ['pip', 'install', '-e', PATH_TO_HDLCC, '-U',]
        if not _CI:
            cmd += ['--user']
        _logger.info("Installing HDLCC via pip with command:")
        _logger.info(cmd)
        subp.check_call(cmd)

        _logger.info("We should be able to call it now")
        subp.check_call(['hdlcc', '-V'])

    def pipUninstallHdlcc():
        subp.check_call(['pip', 'uninstall', 'hdlcc', '-y'])

    @it.has_setup
    def setup():
        #  gitClean()
        cleanHdlLib()
        pipInstallHdlcc()

    @it.has_teardown
    def teardown():
        #  gitClean()
        cleanHdlLib()
        pipUninstallHdlcc()

    with it.having("a session with multiple files to edit"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS,
                                "test_001_editing_multiple_files.vroom")
            try:
                subp.check_call(getTestCommand(vroom_test))
            except subp.CalledProcessError:
                _logger.exception("Excepion caught while testing")
                it.fail("Test failed")

    with it.having("no project configured"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS,
                                'test_002_no_project_configured.vroom')
            try:
                subp.check_call(getTestCommand(vroom_test))
            except subp.CalledProcessError:
                _logger.exception("Excepion caught while testing")
                it.fail("Test failed")

    with it.having("a project file but no builder working"):
        @it.should("pass")
        def test():
            vroom_test = p.join(_PATH_TO_TESTS,
                                'test_003_with_project_without_builder.vroom')
            try:
                subp.check_call(getTestCommand(vroom_test))
            except subp.CalledProcessError:
                _logger.exception("Excepion caught while testing")
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
                _logger.exception("Excepion caught while testing")
                output = list(exc.output.splitlines())

            if exc is None:
                for line in output:
                    _logger.info("> " + line)
            else:
                for line in output:
                    _logger.warning("> " + line)

            try:
                subp.check_call(getTestCommand(vroom_test))
            except subp.CalledProcessError:
                _logger.exception("Excepion caught while testing")
                it.fail("Test failed")

it.createTests(globals())

