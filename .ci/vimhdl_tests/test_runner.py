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

import glob
import logging
import os
import os.path as p
import re
import shutil
import subprocess as subp
import tempfile
from contextlib import contextmanager

import mock

from nose2.tools import such
from nose2.tools.params import params

_logger = logging.getLogger(__name__)

PATH_TO_TESTS = p.join(".ci", "vroom")
HDLCC_CI = p.abspath(p.join("..", "hdlcc_ci"))
PATH_TO_HDLCC = p.join("dependencies", "hdlcc")
ON_CI = os.environ.get("CI", None) is not None
NEOVIM_TARGET = os.environ.get("CI_TARGET", "vim") == "neovim"
VROOM_EXTRA_ARGS = os.environ.get("VROOM_EXTRA_ARGS", None)

def getTestCommand(test_name):
    args = ['python3', '-m', 'vroom']
    args += ['-u', p.expanduser('~/.vimrc' if ON_CI else '~/dot_vim/vimrc')]
    if ON_CI:
        args += ['--nocolor']
    if ON_CI and not NEOVIM_TARGET:
        args += ['-d', '0.5']
    if NEOVIM_TARGET:
        args += ['--neovim']
    if VROOM_EXTRA_ARGS is not None:
        args += re.split(r"\s+", VROOM_EXTRA_ARGS)

    args += [test_name]

    _logger.info("$ %s", " ".join(args))
    return args

@contextmanager
def pushd(path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)

def mockMsim():
    """
    Creates a temporary path and vcom/vlog empty executables just so that hdlcc
    reports them as existing
    """
    temp_path = tempfile.mkdtemp()

    for bin_name in 'vcom', 'vlog':
        bin_path = p.join(temp_path, bin_name)
        open(bin_path, 'w').write('#/usr/bin/env sh')
        os.chmod(bin_path, int('755', 8))

    # Add the builder path to the environment so we can call it
    new_path = os.pathsep.join([temp_path + '/', os.environ['PATH']])
    return mock.patch.dict('os.environ', {'PATH' : new_path})

with such.A('vim-hdl test') as it:

    def gitClean(path=None):
        with pushd(path or '.'):
            _logger.info("Cleaning up non-git files")
            for line in subp.check_output(['git', 'clean', '-fdx']).splitlines():
                _logger.info("> %s", line)

    def cleanHdlLib():
        _logger.info("Resetting hdl_lib")

        with pushd(p.join(HDLCC_CI, "hdl_lib")):

            for line in \
                subp.check_output(['git', 'reset', 'HEAD', '--hard']).splitlines():

                _logger.info("> %s", line)

            gitClean()

            _logger.info("git status")
            for line in \
                subp.check_output(['git', 'status', '--porcelain']).splitlines():

                _logger.info("> %s", line)

    def pipInstallHdlcc():
        cmd = ['pip', 'install', '-e', PATH_TO_HDLCC, '-U',]
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

        for vroom_test in glob.glob(p.join(PATH_TO_TESTS, '*.vroom')):
            vroom_post = p.join(p.dirname(vroom_test),
                                'alt_' + p.basename(vroom_test))
            if p.exists(vroom_post):
                os.remove(vroom_post)

        if p.exists('source.vhd'):
            os.remove('source.vhd')

    @it.should("handle session with multiple files to edit")
    def test(case):
        vroom_test = p.join(PATH_TO_TESTS,
                            "test_001_editing_multiple_files.vroom")
        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("run only static checks if no project was configured")
    def test(case):
        vroom_test = p.join(PATH_TO_TESTS,
                            'test_002_no_project_configured.vroom')
        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("warn when unable to create the configured builder")
    def test(case):
        #  gitClean('../hdlcc_ci/hdl_lib')
        gitClean(p.join(HDLCC_CI, "hdl_lib"))
        vroom_test = p.join(PATH_TO_TESTS,
                            'test_003_with_project_without_builder.vroom')
        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("allow building via hdlcc standalone before editing")
    def test(case):
        vroom_test = p.join(PATH_TO_TESTS, 'test_004_issue_10.vroom')
        cmd = ['hdlcc', HDLCC_CI + '/hdl_lib/ghdl.prj', '-cvv', '-s',
               HDLCC_CI + '/hdl_lib/common_lib/edge_detector.vhd']

        _logger.info(cmd)
        exc = None
        try:
            output = subp.check_output(cmd).splitlines()
        except subp.CalledProcessError as exc:
            _logger.exception("Excepion caught while testing")
            output = list(exc.output.splitlines())
            raise

        if exc is None:
            for line in output:
                _logger.info("> %s", line)
        else:
            for line in output:
                _logger.warning("> %s", line)

        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("not result on E926 when jumping from quickfix")
    def test(case):
        if p.exists('source.vhd'):
            os.remove('source.vhd')

        vroom_test = p.join(PATH_TO_TESTS,
                            'test_005_issue_15_quickfix_jump.vroom')
        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            it.fail("Test failed: %s" % case)

    @it.should("print vimhdl diagnose info")
    def test(case):
        import sys
        sys.path.insert(0, 'python')
        sys.path.insert(0, p.join('dependencies', 'hdlcc'))
        import vimhdl
        import hdlcc

        vroom_test = p.join(PATH_TO_TESTS,
                            'test_006_get_vim_info.vroom')
        lines = open(vroom_test, 'r').read()

        lines = lines.replace("__vimhdl__version__", vimhdl.__version__)
        lines = lines.replace("__hdlcc__version__", hdlcc.__version__)
        sys.path.remove('python')
        sys.path.remove(p.join('dependencies', 'hdlcc'))

        del sys.modules['vimhdl']
        del sys.modules['hdlcc']

        vroom_post = vroom_test.replace('test_006', 'alt_test_006')
        open(vroom_post, 'w').write(lines)

        try:
            subp.check_call(getTestCommand(vroom_post))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("only start hdlcc server when opening a hdl file")
    @params('vhdl', 'verilog', 'systemverilog')
    def test(case, filetype):
        vroom_test = p.join(
            PATH_TO_TESTS,
            'test_007_server_should_start_only_when_opening_hdl_file.vroom')

        import sys
        sys.path.insert(0, 'python')
        sys.path.insert(0, p.join('dependencies', 'hdlcc'))
        import vimhdl
        import hdlcc

        lines = open(vroom_test, 'r').read()

        lines = lines.replace("__vimhdl__version__", vimhdl.__version__)
        lines = lines.replace("__hdlcc__version__", hdlcc.__version__)

        lines = lines.replace("__filetype__", filetype)

        sys.path.remove('python')
        sys.path.remove(p.join('dependencies', 'hdlcc'))

        del sys.modules['vimhdl']
        del sys.modules['hdlcc']


        vroom_post = vroom_test.replace('test_007', 'alt_test_007')
        open(vroom_post, 'w').write(lines)

        try:
            subp.check_call(getTestCommand(vroom_post))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("get dependencies and build sequence")
    def test(case):
        vroom_test = p.join(PATH_TO_TESTS,
                            "test_008_get_dependencies_and_build_sequence.vroom")
        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("run config helper without g:vimhdl_conf_file set")
    def test(case):
        vroom_test = p.join(
            PATH_TO_TESTS, "test_009_create_project_file_with_clear_setup.vroom")

        # Remove all project files before running
        for path in glob.glob(p.join(HDLCC_CI, '*.prj')):
            _logger.info("Removing '%s'", path)
            os.remove(path)
        try:
            subp.check_call(getTestCommand(vroom_test))
        except subp.CalledProcessError:
            _logger.exception("Excepion caught while testing")
            it.fail("Test failed: %s" % case)

    @it.should("find include paths when running the config helper")
    def test(case):
        vroom_test = p.abspath(p.join(
            PATH_TO_TESTS, "test_010_create_project_file_with_conf_file_set.vroom"))

        # Remove all project files before running
        for path in glob.glob(p.join(HDLCC_CI, '*.prj')):
            _logger.info("Removing '%s'", path)
            os.remove(path)

        # Needs to agree with vroom test file
        dummy_test_path = p.expanduser('~/dummy_test_path')

        # Create a dummy arrangement of sources
        if p.exists(dummy_test_path):
            shutil.rmtree(dummy_test_path)

        os.mkdir(dummy_test_path)

        with pushd(dummy_test_path):
            os.mkdir('path_a')
            os.mkdir('path_b')
            os.mkdir('v_includes')
            os.mkdir('sv_includes')
            # Create empty sources
            for path in (p.join('path_a', 'some_source.vhd'),
                         p.join('path_a', 'header_out_of_place.vh'),
                         p.join('path_a', 'source_tb.vhd'),
                         p.join('path_b', 'some_source.vhd'),
                         p.join('path_b', 'a_verilog_source.v'),
                         p.join('path_b', 'a_systemverilog_source.sv'),
                         # Create headers for both extensions
                         p.join('v_includes', 'verilog_header.vh'),
                         p.join('sv_includes', 'systemverilog_header.svh'),
                         # Make the tree 'dirty' with other source types
                         p.join('path_a', 'not_hdl_source.log'),
                         p.join('path_a', 'not_hdl_source.py'),
                         ):
                _logger.info("Writing to %s", path)
                open(path, 'w').write('')

        # This shouldn't run under pushd context otherwise we won't get the
        # coverage reports
        with mockMsim():
            try:
                subp.check_call(getTestCommand(vroom_test))
            except subp.CalledProcessError:
                _logger.exception("Excepion caught while testing")
                it.fail("Test failed: %s" % case)

    @it.should("find files in specified paths")
    def test(case):
        vroom_test = p.abspath(p.join(
            PATH_TO_TESTS, "test_011_create_project_file_with_args.vroom"))

        with pushd(p.join(HDLCC_CI, "hdl_lib")):
            try:
                subp.check_call(getTestCommand(vroom_test))
            except subp.CalledProcessError:
                _logger.exception("Excepion caught while testing")
                it.fail("Test failed: %s" % case)


it.createTests(globals())
