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

from __future__ import print_function

import sys
import os
import os.path as p
import logging
from nose2.tools import such

try:  # Python 3.x
    import unittest.mock as mock # pylint: disable=import-error, no-name-in-module
except ImportError:  # Python 2.x
    import mock

_CI = os.environ.get("CI", None) is not None

_logger = logging.getLogger(__name__)

def _setupPaths():
    base_path = p.abspath(p.join(p.dirname(__file__), '..', '..'))
    for path in (p.join(base_path, 'python'),
                 p.join(base_path, 'dependencies', 'requests')):
        print(path)
        assert p.exists(path), "Path '%s' doesn't exists!" % path
        sys.path.insert(0, path)

_setupPaths()

# pylint: disable=import-error,wrong-import-position
from vimhdl_tests.vim_mock import mockVim
mockVim()
import vim
import vimhdl  # pylint: disable=unused-import
import vimhdl.vim_helpers as vim_helpers
# pylint: enable=import-error,wrong-import-position

with such.A('vim_helpers module') as it:
    @it.should("return all buffer variables from the current buffer if "
               "neither buffer or variable are defined")
    def test():
        it.assertEquals(
            vim_helpers._getBufferVars(),
            {'current_buffer_var_0' : 'current_buffer_value_0',
             'current_buffer_var_1' : 'current_buffer_value_1'})

    @it.should("return the given buffer variable of the current buffer if "
               "only the first one is given")
    def test():
        it.assertEquals(vim_helpers._getBufferVars(var='current_buffer_var_0'),
                        'current_buffer_value_0')
        it.assertEquals(vim_helpers._getBufferVars(var='current_buffer_var_1'),
                        'current_buffer_value_1')

    @it.should("return all variables of other buffers")
    def test():
        it.assertEquals(
            vim_helpers._getBufferVars(vim.buffers[0]),
            {'buffer_0_var_0' : 'buffer_0_var_value_0',
             'buffer_0_var_1' : 'buffer_0_var_value_1',}
            )
        it.assertEquals(
            vim_helpers._getBufferVars(vim.buffers[1]),
            {'buffer_1_var_0' : 'buffer_1_var_value_0',
             'buffer_1_var_1' : 'buffer_1_var_value_1',}
            )

    @it.should("return a specific variable of a specific buffer")
    def test():
        it.assertEquals(
            vim_helpers._getBufferVars(vim.buffers[0], 'buffer_0_var_0'),
            'buffer_0_var_value_0',)

    @it.should("post vim info correctly formatted")
    def test():
        vim_helpers.postVimInfo("Some info")
        vim.command.assert_called_with(
            "redraw | echom 'Some info' | echohl None")

    @it.should("post vim warning correctly formatted")
    def test():
        vim_helpers.postVimWarning("Some warning")
        vim.command.assert_called_with(
            "redraw | echohl WarningMsg | echom 'Some warning' | echohl None")

    @it.should("post vim error correctly formatted")
    def test():
        vim_helpers.postVimError("Some error")
        vim.command.assert_called_with(
            "echohl ErrorMsg | echom 'Some error' | echohl None")

    with it.having("both global and local project files configured"):
        def deleteProjectFiles():
            for prj_filename in (it._global_prj_filename,
                                 it._local_prj_filename):
                if p.exists(prj_filename):
                    os.remove(prj_filename)

        @it.has_setup
        def setup():
            it._global_prj_filename = p.abspath(p.join(
                os.curdir, 'global_project.prj'))

            it._local_prj_filename = p.abspath(p.join(
                os.curdir, 'local_project.prj'))

            it._global_patch = mock.patch(
                'vim.vars', {'vimhdl_conf_file' : it._global_prj_filename})
            it._local_patch = mock.patch(
                'vim.current.buffer.vars', {'vimhdl_conf_file' : it._local_prj_filename})

            it._global_patch.start()
            it._local_patch.start()

        @it.has_teardown
        def teardown():
            deleteProjectFiles()
            it._global_patch.stop()
            it._local_patch.stop()

        @it.should("give precedence to local project file when both are "
                   "readable")
        def test():
            for prj_filename in (it._global_prj_filename,
                                 it._local_prj_filename):
                assert not p.exists(prj_filename)
                open(prj_filename, 'w').close()

            it.assertEqual(it._local_prj_filename,
                           vim_helpers.getProjectFile())

            deleteProjectFiles()

        @it.should("use the local project file even if the global is not "
                   "readable")
        def test():
            for prj_filename in (it._local_prj_filename, ):
                assert not p.exists(prj_filename)
                open(prj_filename, 'w').close()

            it.assertEqual(it._local_prj_filename,
                           vim_helpers.getProjectFile())

            deleteProjectFiles()

        @it.should("fallback to the global project file when the local "
                   "project file is not readable")
        def test():
            for prj_filename in (it._global_prj_filename, ):
                assert not p.exists(prj_filename)
                open(prj_filename, 'w').close()

            it.assertEqual(it._global_prj_filename,
                           vim_helpers.getProjectFile())

            deleteProjectFiles()

    with it.having("only a global project file configured"):
        def deleteProjectFiles():
            for prj_filename in (it._global_prj_filename,
                                 it._local_prj_filename):
                if p.exists(prj_filename):
                    os.remove(prj_filename)

        @it.has_setup
        def setup():
            it._global_prj_filename = p.abspath(p.join(
                os.curdir, 'global_project.prj'))

            it._local_prj_filename = p.abspath(p.join(
                os.curdir, 'local_project.prj'))

            it._global_patch = mock.patch(
                'vim.vars', {'vimhdl_conf_file' : it._global_prj_filename})

            it._global_patch.start()

        @it.has_teardown
        def teardown():
            deleteProjectFiles()
            it._global_patch.stop()

        @it.should("return the global project file when it's readable")
        def test():
            for prj_filename in (it._global_prj_filename, ):
                assert not p.exists(prj_filename)
                open(prj_filename, 'w').close()

            it.assertEqual(it._global_prj_filename,
                           vim_helpers.getProjectFile())

            deleteProjectFiles()

        @it.should("return None if the global project file is not readable")
        def test():
            it.assertIsNone(vim_helpers.getProjectFile())
            deleteProjectFiles()

    with it.having("only a local project file configured"):
        def deleteProjectFiles():
            for prj_filename in (it._global_prj_filename,
                                 it._local_prj_filename):
                if p.exists(prj_filename):
                    os.remove(prj_filename)

        @it.has_setup
        def setup():
            it._global_prj_filename = p.abspath(p.join(
                os.curdir, 'global_project.prj'))

            it._local_prj_filename = p.abspath(p.join(
                os.curdir, 'local_project.prj'))

            it._local_patch = mock.patch(
                'vim.current.buffer.vars', {'vimhdl_conf_file' : it._local_prj_filename})

            it._local_patch.start()

        @it.has_teardown
        def teardown():
            deleteProjectFiles()
            it._local_patch.stop()

        @it.should("give precedence to local project file when both are "
                   "readable")
        def test():
            for prj_filename in (it._global_prj_filename,
                                 it._local_prj_filename):
                assert not p.exists(prj_filename)
                open(prj_filename, 'w').close()

            it.assertEqual(it._local_prj_filename,
                           vim_helpers.getProjectFile())

            deleteProjectFiles()

        @it.should("use the local project file even if the global is not "
                   "readable")
        def test():
            for prj_filename in (it._local_prj_filename, ):
                assert not p.exists(prj_filename)
                open(prj_filename, 'w').close()

            it.assertEqual(it._local_prj_filename,
                           vim_helpers.getProjectFile())

            deleteProjectFiles()

        @it.should("return None if the local project file is not readable")
        def test():
            deleteProjectFiles()
            it.assertIsNone(vim_helpers.getProjectFile())
            deleteProjectFiles()

it.createTests(globals())
