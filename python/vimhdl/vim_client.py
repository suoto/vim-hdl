# This file is part of vim-hdl.
#
# Copyright (c) 2015-2016 Andre Souto
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
"Wrapper for vim-hdl usage within Vim's Python interpreter"

import atexit
import logging
import os
import os.path as p
import subprocess as subp
import sys
import time
from multiprocessing import Queue
from pprint import pformat
from tempfile import NamedTemporaryFile

import vim  # type: ignore # pylint: disable=import-error
import vimhdl
import vimhdl.vim_helpers as vim_helpers
from vimhdl.base_requests import (BaseRequest, GetBuildSequence,
                                  GetDependencies, RequestHdlCheckerInfo,
                                  RequestMessagesByPath, RequestProjectRebuild,
                                  RequestQueuedMessages, RunConfigGenerator)
from vimhdl.config_gen_wrapper import ConfigGenWrapper

_ON_WINDOWS = sys.platform == "win32"

_logger = logging.getLogger(__name__)


def _sortKey(record):
    """
    Key for sorting records
    """
    return (
        1 if "Error" in record["type"] else 2,
        record["lnum"] if isinstance(record["lnum"], int) else 0,
        record["col"] if isinstance(record["col"], int) else 0,
        record["nr"] if isinstance(record["nr"], int) else 0,
    )


def _sortBuildMessages(records):
    """
    Sorts the build messages using Vim's terminology
    """
    for record in records:
        for key in ("lnum", "nr", "col"):
            try:
                record[key] = int(record[key])
            except ValueError:
                pass
    records.sort(key=_sortKey)
    return records


# pylint:disable=inconsistent-return-statements


class VimhdlClient:  # pylint: disable=too-many-instance-attributes
    """
    Point of entry of Vim commands
    """

    # If the user hasn't already set vimhdl_conf_file in g: or b:, we'll use
    # this instead
    _default_conf_filename = "vimhdl.prj"

    def __init__(self, **options):
        self._logger = logging.getLogger(__name__ + "." + self.__class__.__name__)
        self._logger.info("Creating vimhdl client object: %s", options)

        self._server = None
        # Store constructor args
        self._host = options.get("host", "localhost")
        self._port = options.get("port", vim_helpers.getUnusedLocalhostPort())
        self._log_level = str(options.get("log_level", "DEBUG"))
        self._log_file = (
            options.get("log_target", None)
            or NamedTemporaryFile(
                prefix="vimhdl_log_pid{}_".format(os.getpid()), suffix=".log"
            ).name
        )

        self._stdout = (
            options.get("stdout", None)
            or NamedTemporaryFile(
                prefix="vimhdl_stdout_pid{}_".format(os.getpid()), suffix=".log"
            ).name
        )

        self._stderr = (
            options.get("stderr", None)
            or NamedTemporaryFile(
                prefix="vimhdl_stderr_pid{}_".format(os.getpid()), suffix=".log"
            ).name
        )

        self._posted_notifications = []

        self._ui_queue = Queue()
        self.helper_wrapper = ConfigGenWrapper()

        # Set url on the BaseRequest class as well
        BaseRequest.url = "http://{}:{}".format(self._host, self._port)

    def startServer(self):
        """
        Starts the hdl_checker server, waits until it responds and register
        server shutdown when exiting Vim's Python interpreter
        """
        self._startServerProcess()
        self._waitForServerSetup()

        atexit.register(self.shutdown)

    def _postError(self, msg):
        """
        Post errors to the user once
        """
        if ("error", msg) not in self._posted_notifications:
            self._posted_notifications += [("error", msg)]
            vim_helpers.postVimError(msg)

    def _postWarning(self, msg):
        """
        Post warnings to the user once
        """
        if ("warn", msg) not in self._posted_notifications:
            self._posted_notifications += [("warn", msg)]
            vim_helpers.postVimWarning(msg)

    def _isServerAlive(self):
        """
        Checks if the the server is alive
        """
        if self._server is None:
            return False
        is_alive = self._server.poll() is None
        if not is_alive:
            self._postWarning("hdl_checker server is not running")
        return is_alive

    def _startServerProcess(self):
        """
        Starts the hdl_checker server
        """
        self._logger.info("Running vim_hdl client setup")

        hdl_checker_executable = "hdl_checker"

        # Try to get the version before to catch potential issues
        try:
            _cmd = [hdl_checker_executable, "--version"]
            self._logger.debug("Will run %s", " ".join(map(str, _cmd)))
            self._logger.info(
                "version: %s", subp.check_output(_cmd, stderr=subp.STDOUT)
            )
        except (subp.CalledProcessError, FileNotFoundError) as exc:
            #  self._postError()
            vim_helpers.postVimError("Error while starting server: {}".format(exc))
            return

        cmd = [
            hdl_checker_executable,
            "--host",
            self._host,
            "--port",
            str(self._port),
            "--stdout",
            self._stdout,
            "--stderr",
            self._stderr,
            "--attach-to-pid",
            str(os.getpid()),
            "--log-level",
            self._log_level,
            "--log-stream",
            self._log_file,
        ]

        self._logger.info(
            "Starting hdl_checker server with '%s'", " ".join(map(str, cmd))
        )

        try:
            if _ON_WINDOWS:
                self._server = subp.Popen(
                    cmd,
                    stdout=subp.PIPE,
                    stderr=subp.PIPE,
                    creationflags=subp.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                self._server = subp.Popen(
                    cmd,
                    stdout=subp.PIPE,
                    stderr=subp.PIPE,
                    preexec_fn=os.setpgrp,
                )

            if not self._isServerAlive():
                self._postError("Failed to launch hdl_checker server")
        except subp.CalledProcessError:
            self._logger.exception("Error calling '%s'", " ".join(cmd))

    def _waitForServerSetup(self):
        """
        Wait for ~10s until the server is actually responding
        """
        for _ in range(10):
            time.sleep(0.2)
            request = RequestHdlCheckerInfo()
            response = request.sendRequest()
            self._logger.debug(response)
            if response:
                self._logger.info("Ok, server is really up")
                return
            self._logger.info("Server is not responding yet")

        self._postError("Unable to talk to server")

    def shutdown(self):
        """
        Kills the hdl_checker server
        """
        if not self._isServerAlive():
            self._logger.warning("Server is not running")
            return
        self._logger.debug("Sending shutdown signal")
        os.kill(self._server.pid, 9)
        self._server.terminate()
        self._logger.debug("Done")

    def _handleAsyncRequest(self, response):
        """
        Callback passed to asynchronous requests
        """
        if response is not None:
            self._ui_queue.put(response)

    def _postQueuedMessages(self):
        """
        Empty our queue in a single message
        """
        while not self._ui_queue.empty():
            messages = self._ui_queue.get()
            for severity, message in messages.json().get("ui_messages", []):
                if severity == "info":
                    vim_helpers.postVimInfo(message)
                elif severity == "warning":
                    self._postWarning(message)
                elif severity == "error":
                    self._postError(message)
                else:
                    vim_helpers.postVimError(
                        "Unknown severity '%s' for message '%s'" % (severity, message)
                    )

    def getMessages(self, vim_buffer=None, vim_var=None):
        """
        Returns a list of messages to populate the quickfix list. For
        more info, check :help getqflist()
        """
        if not self._isServerAlive():
            self._logger.warning("Server is not alive, can't get messages")
            return

        if vim_buffer is None:
            vim_buffer = vim.current.buffer

        if vim_var is not None:
            vim.command("let {0} = []".format(vim_var))

        project_file = vim_helpers.getProjectFile()
        path = p.abspath(vim_buffer.name)

        request = RequestMessagesByPath(project_file=project_file, path=path)

        response = request.sendRequest()
        if response is None:
            return

        messages = []
        for msg in response.json().get("messages", []):
            _logger.info("msg:\n%s", pformat(msg))
            text = str(msg["text"]) if msg["text"] else ""
            vim_fmt_dict = {
                "lnum": int(msg.get("line_number", 0)) + 1,
                "bufnr": str(vim_buffer.number),
                "filename": msg.get("filename", None) or vim_buffer.name,
                "valid": "1",
                "text": text,
                "nr": msg.get("error_code", None) or "0",
                "type": msg.get("severity", None) or "E",
                "col": int(msg.get("column_number", 0)) + 1,
            }
            try:
                vim_fmt_dict["subtype"] = str(msg["error_subtype"])
            except KeyError:
                pass

            _logger.info(vim_fmt_dict)
            messages.append(vim_fmt_dict)

        self.requestUiMessages("getMessages")

        if vim_var is None:
            return _sortBuildMessages(messages)

        for msg in _sortBuildMessages(messages):
            vim_helpers.toVimDict(msg, "_dict")
            vim.command("let {0} += [{1}]".format(vim_var, "_dict"))
            vim.command("unlet! _dict")

    def requestUiMessages(self, event):
        """Retrieves UI messages from the server and post them with the
        appropriate severity level"""
        self._logger.info(
            "Handling event '%s'. Filetype is %s", event, vim.eval("&filetype")
        )
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = RequestQueuedMessages(project_file=project_file)

        request.sendRequestAsync(self._handleAsyncRequest)

    def getVimhdlInfo(self):
        """
        Gets info about the current project and hdl_checker server
        """
        project_file = vim_helpers.getProjectFile()
        request = RequestHdlCheckerInfo(project_file=project_file)

        response = request.sendRequest()

        info = ["vimhdl version: %s" % vimhdl.__version__]

        if response is not None:
            # The server has responded something, so just print it
            self._logger.info("Response: %s", str(response.json()["info"]))

            info += response.json()["info"]
        else:
            info += ["hdl_checker server is not running"]

        info += [
            "Server logs: " + self._log_file,
            "Server stdout: " + self._stdout,
            "Server stderr: " + self._stderr,
        ]

        _logger.info("info: %s", info)
        return "\n".join(["- " + str(x) for x in info])

    def rebuildProject(self):
        """
        Rebuilds the current project
        """
        if vim.eval("&filetype") not in ("vhdl", "verilog", "systemverilog"):
            vim_helpers.postVimWarning("Not a VHDL file, can't rebuild")
            return

        vim_helpers.postVimInfo("Rebuilding project...")
        project_file = vim_helpers.getProjectFile()
        request = RequestProjectRebuild(project_file=project_file)

        response = request.sendRequest()

        if response is None:
            return "hdl_checker server is not running"

        self._logger.info("Response: %s", repr(response))

    def getDependencies(self):
        """
        Gets the dependencies for a given path
        """
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = GetDependencies(
            project_file=project_file, path=vim.current.buffer.name
        )

        response = request.sendRequest()
        if response is not None:
            self._logger.debug("Response: %s", str(response.json()["dependencies"]))

            return "\n".join(
                ["Dependencies for %s" % vim.current.buffer.name]
                + ["- %s" % x for x in sorted(response.json()["dependencies"])]
            )

        return "Source has no dependencies"

    def getBuildSequence(self):
        """
        Gets the build sequence for the current path
        """
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = GetBuildSequence(
            project_file=project_file, path=vim.current.buffer.name
        )

        response = request.sendRequest()
        if response is not None:
            self._logger.debug("Response: %s", str(response.json()["sequence"]))

            sequence = response.json()["sequence"]
            if sequence:
                i = 1
                msg = ["Build sequence for %s\n" % vim.current.buffer.name]
                for i, item in enumerate(sequence, 1):
                    msg += ["%d: %s" % (i, item)]
                return "\n".join(msg)

            return "Build sequence is empty"

        return ""

    def updateHelperWrapper(self):
        """
        Requests the config file content from the server and return the wrapper
        class
        """
        paths = vim.eval("b:local_arg") or ["."]

        request = RunConfigGenerator(generator="SimpleFinder", paths=paths)
        response = request.sendRequest()
        if response is None:
            return

        self.helper_wrapper.run(response.json()["content"])
