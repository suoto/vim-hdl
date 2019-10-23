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

PATH_TO_TESTS = p.abspath(p.join(".ci", "vroom"))
HDLCC_CI = p.abspath(p.join("..", "hdlcc_ci"))
ON_CI = os.environ.get("CI", None) is not None
NEOVIM_TARGET = os.environ.get("CI_TARGET", "vim") == "neovim"
VROOM_EXTRA_ARGS = os.environ.get("VROOM_EXTRA_ARGS", None)


@contextmanager
def pushd(path):
    prev = os.getcwd()
    _logger.debug("%s => %s", repr(prev), repr(path))
    os.chdir(path)
    try:
        yield
    finally:
        _logger.debug("%s => %s", repr(os.getcwd()), repr(prev))
        os.chdir(prev)


def runShell(cmd, shell=False, cwd=None):
    _logger.info("$ %s", " ".join([str(x) for x in cmd]))
    for line in subp.check_output(cmd, shell=shell, cwd=cwd).splitlines():
        _logger.info("> %s", line.decode())


with such.A("vim-hdl test") as it:

    @contextmanager
    def mockMsim():
        """
        Creates a temporary path and vcom/vlog empty executables just so that hdlcc
        reports them as existing
        """
        with tempfile.TemporaryDirectory(prefix="vimhdl_test_") as temp_path:
            for bin_name in "vcom", "vlog":
                bin_path = p.join(temp_path, bin_name)
                open(bin_path, "w").write("#/usr/bin/env sh")
                os.chmod(bin_path, int("755", 8))

            # Add the builder path to the environment so we can call it
            new_path = os.pathsep.join([temp_path + "/", os.environ["PATH"]])
            with mock.patch.dict("os.environ", {"PATH": new_path}) as vsim_mock:
                yield vsim_mock

    def runVroom(test_name):
        cmd = ["vroom", "-u", p.expanduser("~/.vimrc" if ON_CI else "~/dot_vim/vimrc")]

        output = p.join("/tmp", "vroom_%s.log" % p.basename(test_name))

        cmd += ["--out", output]

        if ON_CI:
            cmd += ["--nocolor"]

        # This has been weird at a times, adding a bit of extra delay between
        # commands seems to help
        cmd += ["-d", "0.5" if ON_CI else "0.2"]

        if NEOVIM_TARGET:
            cmd += ["--neovim"]
        if VROOM_EXTRA_ARGS is not None:
            cmd += re.split(r"\s+", VROOM_EXTRA_ARGS)

        cmd += [test_name]

        _logger.info("$ %s", " ".join(cmd))
        if os.system(" ".join(cmd)) != 0:
            _logger.error("Test failed: %s", test_name)
            for line in open(output).readlines():
                line = line[:-1]
                if line:
                    _logger.error(">> %s", line)
            it.fail("Test failed: %s" % test_name)

    def dbgFindCoverage():
        cnt = 0
        for report in glob.glob(".coverage.*"):
            cnt += 1
            _logger.warning("Coverage report: %s", p.abspath(report))

        it.assertEqual(cnt, 0, "Found stuff!!!")

    def gitClean(path):
        _logger.debug("Cleaning up non-git files")
        runShell(["git", "clean", "-fd"], cwd=path or ".")

    def cleanHdlLib():
        _logger.debug("Resetting hdl_lib")

        runShell(["git", "reset", "HEAD", "--hard"], cwd=p.join(HDLCC_CI, "hdl_lib"))

        gitClean(p.join(HDLCC_CI, "hdl_lib"))

        runShell(["git", "status", "--porcelain"], cwd=p.join(HDLCC_CI, "hdl_lib"))

    def pipInstallHdlcc():
        cmd = ["pip", "install", "hdl_checker", "-U"]
        _logger.debug("Installing HDLCC via pip with command:")
        runShell(cmd)

        _logger.debug("We should be able to call it now")
        runShell(["hdl_checker", "-V"])

    def pipUninstallHdlcc():
        runShell(["pip", "uninstall", "hdl_checker", "-y"])

    @it.has_setup
    def setup():
        pipInstallHdlcc()

    @it.has_teardown
    def teardown():
        pipUninstallHdlcc()

        for vroom_test in glob.glob(p.join(PATH_TO_TESTS, "*.vroom")):
            vroom_post = p.join(p.dirname(vroom_test), "alt_" + p.basename(vroom_test))
            if p.exists(vroom_post):
                os.remove(vroom_post)

        if p.exists("source.vhd"):
            os.remove("source.vhd")

    @it.has_test_setup
    def testSetup():
        cleanHdlLib()

    @it.has_test_teardown
    def testTeardown():
        cleanHdlLib()

    @it.should("handle session with multiple files to edit")
    def test():
        vroom_test = p.join(PATH_TO_TESTS,
                            "test_001_editing_multiple_files.vroom")
        runVroom(vroom_test)

    @it.should("run only static checks if no project was configured")
    def test():
        vroom_test = p.join(PATH_TO_TESTS,
                            'test_002_no_project_configured.vroom')
        runVroom(vroom_test)

    @it.should("warn when unable to create the configured builder")
    def test():
        gitClean(p.join(HDLCC_CI, "hdl_lib"))
        vroom_test = p.join(PATH_TO_TESTS,
                            'test_003_with_project_without_builder.vroom')
        runVroom(vroom_test)

    @it.should("not result on E926 when jumping from quickfix")
    def test():
        if p.exists("source.vhd"):
            os.remove("source.vhd")

        vroom_test = p.join(PATH_TO_TESTS, "test_005_issue_15_quickfix_jump.vroom")
        runVroom(vroom_test)

    @it.should("print vimhdl diagnose info")
    def test():
        import sys

        sys.path.insert(0, "python")
        sys.path.insert(0, p.join("dependencies", "hdlcc"))
        import vimhdl  # pylint: disable=import-error
        import hdl_checker  # pylint: disable=import-error

        vroom_test = p.join(PATH_TO_TESTS, "test_006_get_vim_info.vroom")
        lines = open(vroom_test, "r").read()

        lines = lines.replace("__vimhdl__version__", vimhdl.__version__)
        lines = lines.replace("__hdl_checker__version__", hdl_checker.__version__)
        sys.path.remove("python")
        sys.path.remove(p.join("dependencies", "hdlcc"))

        del sys.modules["vimhdl"]
        del sys.modules["hdl_checker"]

        vroom_post = vroom_test.replace("test_006", "alt_test_006")
        open(vroom_post, "w").write(lines)

        runVroom(vroom_post)

    @it.should("only start hdlcc server when opening a hdl file")
    @params("vhdl", "verilog", "systemverilog")
    def test(case, filetype):  # pylint: disable=unused-argument
        vroom_test = p.join(
            PATH_TO_TESTS,
            "test_007_server_should_start_only_when_opening_hdl_file.vroom",
        )

        import sys

        sys.path.insert(0, "python")
        sys.path.insert(0, p.join("dependencies", "hdlcc"))
        import vimhdl  # pylint: disable=import-error
        import hdl_checker  # pylint: disable=import-error

        lines = open(vroom_test, "r").read()

        lines = lines.replace("__vimhdl__version__", vimhdl.__version__)
        lines = lines.replace("__hdl_checker__version__", hdl_checker.__version__)

        lines = lines.replace("__filetype__", filetype)

        sys.path.remove("python")
        sys.path.remove(p.join("dependencies", "hdlcc"))

        del sys.modules["vimhdl"]
        del sys.modules["hdl_checker"]

        vroom_post = vroom_test.replace("test_007", "alt_test_007")
        open(vroom_post, "w").write(lines)

        runVroom(vroom_post)

    @it.should("get dependencies and build sequence")
    def test():
        vroom_test = p.join(
            PATH_TO_TESTS, "test_008_get_dependencies_and_build_sequence.vroom"
        )
        runVroom(vroom_test)

    #  @it.should("run config helper without g:vimhdl_conf_file set")
    #  def test():
    #      vroom_test = p.join(
    #          PATH_TO_TESTS, "test_009_create_project_file_with_clear_setup.vroom"
    #      )

    #      # Remove all project files before running
    #      for path in glob.glob(p.join(HDLCC_CI, "*.prj")):
    #          _logger.info("Removing '%s'", path)
    #          os.remove(path)

    #      target_path = p.join(HDLCC_CI, "hdl_lib", "common_lib")

    #      with pushd(target_path):
    #          runVroom(vroom_test)
    #          dbgFindCoverage()

    #  @it.should("find include paths when running the config helper")
    #  def test():
    #      vroom_test = p.abspath(
    #          p.join(
    #              PATH_TO_TESTS, "test_010_create_project_file_with_conf_file_set.vroom"
    #          )
    #      )

    #      # Remove all project files before running
    #      for path in glob.glob(p.join(HDLCC_CI, "*.prj")):
    #          _logger.info("Removing '%s'", path)
    #          os.remove(path)

    #      # Needs to agree with vroom test file
    #      dummy_test_path = p.expanduser("~/dummy_test_path")

    #      # Create a dummy arrangement of sources
    #      if p.exists(dummy_test_path):
    #          shutil.rmtree(dummy_test_path)

    #      os.mkdir(dummy_test_path)

    #      with pushd(dummy_test_path):
    #          os.mkdir("path_a")
    #          os.mkdir("path_b")
    #          os.mkdir("v_includes")
    #          os.mkdir("sv_includes")
    #          # Create empty sources
    #          for path in (
    #              p.join("path_a", "some_source.vhd"),
    #              p.join("path_a", "header_out_of_place.vh"),
    #              p.join("path_a", "source_tb.vhd"),
    #              p.join("path_b", "some_source.vhd"),
    #              p.join("path_b", "a_verilog_source.v"),
    #              p.join("path_b", "a_systemverilog_source.sv"),
    #              # Create headers for both extensions
    #              p.join("v_includes", "verilog_header.vh"),
    #              p.join("sv_includes", "systemverilog_header.svh"),
    #              # Make the tree 'dirty' with other source types
    #              p.join("path_a", "not_hdl_source.log"),
    #              p.join("path_a", "not_hdl_source.py"),
    #          ):
    #              _logger.info("Writing to %s", path)
    #              open(path, "w").write("")

    #      # This shouldn't run under pushd context otherwise we won't get the
    #      # coverage reports
    #      with mockMsim():
    #          runVroom(vroom_test)

    #  @it.should("find files in specified paths")
    #  def test():
    #      vroom_test = p.abspath(
    #          p.join(PATH_TO_TESTS, "test_011_create_project_file_with_args.vroom")
    #      )

    #      with pushd(p.join(HDLCC_CI, "hdl_lib")):
    #          runVroom(vroom_test)
    #          dbgFindCoverage()


it.createTests(globals())
