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

import os
import os.path as p
import subprocess as subp
import sys
import logging
import time
import re

from multiprocessing import Queue

import vim  # pylint: disable=import-error
import vimhdl
import vimhdl.vim_helpers as vim_helpers
from vimhdl.base_requests import (RequestCheck, RequestQueuedMessages,
                                  RequestHdlccInfo, RequestProjectRebuild,
                                  OnBufferVisit, OnBufferLeave)

_ON_WINDOWS = sys.platform == 'win32'
_COMMENT_SCAN = re.compile('--.*').search

_logger = logging.getLogger(__name__)

def _sortBuildMessages(records):
    """
    Sorts the build messages using Vim's terminology
    """
    for record in records:
        for key in ('lnum', 'nr', 'col'):
            try:
                record[key] = int(record[key])
            except ValueError:
                pass
    records.sort(key=lambda x: (x['type'], x['lnum'], x['col'], x['nr']))
    return records

class CursorPosition(object):
    def __init__(self):
        self.line = None
        self.column = None

    def clear(self):
        """
        Clears the line and column fields
        """
        self.line = None
        self.column = None

    def __repr__(self):
        return "(line %s, column %s)" % (str(self.line), str(self.column))

    def __eq__(self, other):
        if other is None:
            return self.line is None and self.column is None
        return (self.line, self.column) == (other[0], other[1])

    def __iter__(self):
        yield self.line
        yield self.column

    def __getitem__(self, i):
        return tuple(iter(self))[i]

class VimhdlClient(object):
    """
    Point of entry of Vim commands
    """

    def __init__(self, **options):
        self._server = None
        self._host = options.get('host', 'localhost')
        self._port = options.get('port', vim_helpers.getUnusedLocalhostPort())
        self._log_level = str(options.get('log_level', 'DEBUG'))
        self._log_stream = options.get('log_target', '/tmp/hdlcc.log')

        self._prev_pos = CursorPosition()
        self._current_pos = CursorPosition()

        self._posted_notifications = []

        self._ui_queue = Queue()

    def startServer(self):
        """
        Starts the hdlcc server, waits until it responds and register
        server shutdown when exiting Vim's Python interpreter
        """
        self._startServerProcess()
        self._waitForServerSetup()

        import atexit
        atexit.register(self.shutdown)

    def _postError(self, msg):
        """
        Post errors to the user once
        """
        if ('error', msg) not in self._posted_notifications:
            self._posted_notifications += [('error', msg)]
            vim_helpers.postVimError(msg)

    def _postWarning(self, msg):
        """
        Post warnings to the user once
        """
        if ('warn', msg) not in self._posted_notifications:
            self._posted_notifications += [('warn', msg)]
            vim_helpers.postVimWarning(msg)

    def _isServerAlive(self):
        """
        Checks if the the server is alive
        """
        is_alive = self._server.poll() is None
        if not is_alive:
            self._postWarning("hdlcc server is not running")
        return is_alive

    def _startServerProcess(self):
        """
        Starts the hdlcc server
        """
        _logger.info("Running vim_hdl client setup")

        vimhdl_path = p.abspath(p.join(p.dirname(__file__), '..', '..'))

        hdlcc_server = p.join(vimhdl_path, 'dependencies', 'hdlcc', 'hdlcc',
                              'hdlcc_server.py')

        cmd = [hdlcc_server,
               '--host', self._host,
               '--port', str(self._port),
               '--stdout', '/tmp/hdlcc-stdout.log',
               '--stderr', '/tmp/hdlcc-stderr.log',
               '--attach-to-pid', str(os.getpid()),
               '--log-level', self._log_level,
               '--log-stream', self._log_stream]

        _logger.info("Starting hdlcc server with '%s'", " ".join(cmd))

        try:
            if _ON_WINDOWS:
                self._server = subp.Popen(
                    cmd, stdout=subp.PIPE, stderr=subp.PIPE,
                    creationflags=subp.CREATE_NEW_PROCESS_GROUP)
            else:
                self._server = subp.Popen(
                    cmd, stdout=subp.PIPE, stderr=subp.PIPE,
                    preexec_fn=os.setpgrp)

            if not self._isServerAlive():
                vim_helpers.postVimError("Failed to launch hdlcc server")
        except subp.CalledProcessError:
            _logger.exception("Error calling '%s'", " ".join(cmd))

    def _waitForServerSetup(self):
        """
        Wait for ~10s until the server is actually responding
        """
        for _ in range(10):
            time.sleep(0.1)
            request = RequestHdlccInfo(self._host, self._port)
            reply = request.sendRequest()
            _logger.debug(reply)
            if reply:
                _logger.info("Ok, server is really up")
                return
            else:
                _logger.info("Server is not responding yet")

        self._postError("Unable to talk to server")

    def shutdown(self):
        """
        Kills the hdlcc server
        """
        if not self._isServerAlive():
            _logger.warning("Server is not running")
            return
        _logger.debug("Sending shutdown signal")
        os.kill(self._server.pid, 9)
        self._server.terminate()
        _logger.debug("Done")

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
            for severity, message in messages.json().get('ui_messages', []):
                if severity == 'info':
                    vim_helpers.postVimInfo(message)
                elif severity == 'warning':
                    self._postWarning(message)
                elif severity == 'error':
                    self._postError(message)
                else:
                    vim_helpers.postVimError(
                        "Unknown severity '%s' for message '%s'" %
                        (severity, message))

    def checkBuffer(self, vim_buffer=None, vim_var=None):
        """
        Returns a list of messages to populate the quickfix list. For
        more info, check :help getqflist()
        """
        if not self._isServerAlive():
            _logger.warning("Server is not alive, can't get messages")
            return

        if vim_buffer is None:
            vim_buffer = vim.current.buffer

        messages = self._checkBuffer(vim_buffer, vim.eval('&modified') == "1")

        vim_messages = []
        for message in messages:
            vim_fmt_dict = {
                'lnum'     : str(message['line_number']) or '-1',
                'bufnr'    : str(vim_buffer.number),
                'filename' : str(message['filename']) or vim_buffer.name,
                'valid'    : '1',
                'text'     : str(message['error_message']) or '<none>',
                'nr'       : str(message['error_number']) or '0',
                'type'     : str(message['error_type']) or 'E',
                'col'      : str(message['column']) or '0'
            }
            try:
                vim_fmt_dict['subtype'] = str(message['error_subtype'])
            except KeyError:
                pass

            _logger.info(vim_fmt_dict)

            vim_messages.append(vim_fmt_dict)

        if vim_var is None:
            return _sortBuildMessages(vim_messages)

        vim.command('let {0} = {1}'.format(vim_var,
                                           _sortBuildMessages(vim_messages)))

    def _checkBuffer(self, vim_buffer, include_content):
        """
        Requests a syntax check for the hdlcc server. If include_content
        is True, the current buffer's content will be included in the
        request
        """
        project_file = vim_helpers.getProjectFile()
        path = p.abspath(vim_buffer.name)

        if include_content:
            content = '\n'.join(vim_buffer)
        else:
            content = None

        request = RequestCheck(host=self._host, port=self._port,
                               project_file=project_file, path=path,
                               content=content)

        response = request.sendRequest()

        return response.json().get('messages', [])

    def requestUiMessages(self, event):
        """Retrieves UI messages from the server and post them with the
        appropriate severity level"""
        _logger.info("Handling event '%s'. Filetype is %s",
                     event, vim.eval('&filetype'))
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = RequestQueuedMessages(self._host, self._port,
                                        project_file=project_file)

        request.sendRequestAsync(self._handleAsyncRequest)

    def getVimhdlInfo(self):
        """
        Gets info about the current project and hdlcc server
        """
        project_file = vim_helpers.getProjectFile()
        request = RequestHdlccInfo(host=self._host, port=self._port,
                                   project_file=project_file)

        response = request.sendRequest()

        if response is not None:
            # The server has responded something, so just print it
            _logger.info("Response: %s", str(response.json()['info']))

            return "\n".join(
                ["- %s" % x for x in
                 ["vimhdl version: %s\n" % vimhdl.__version__] +
                 response.json()['info']])
        else:
            return "\n".join(
                ["- %s" % x for x in
                 ["vimhdl version: %s\n" % vimhdl.__version__,
                  "hdlcc server is not running"]])

    def rebuildProject(self):
        """
        Rebuilds the current project
        """
        vim_helpers.postVimInfo("Rebuilding project...")
        project_file = vim_helpers.getProjectFile()
        request = RequestProjectRebuild(host=self._host, port=self._port,
                                        project_file=project_file)

        response = request.sendRequest()

        if response is None:
            return "hdlcc server is not running"

        _logger.info("Response: %s", repr(response))

    def _updateCursorTracking(self):
        """
        Updates the current and previous cursor position
        """
        if self._current_pos != None:
            self._prev_pos.line = self._current_pos.line
            self._prev_pos.column = self._current_pos.column

        line, column = vim.current.window.cursor
        line -= 1

        self._current_pos.line = line
        self._current_pos.column = column

        if self._current_pos == self._prev_pos:
            return

        _logger.debug("Moved from %s to %s", self._prev_pos, self._current_pos)

    def _cursorMoved(self):
        """
        Checks if the insert cursor has moved
        """
        if None in self._prev_pos:
            return False
        return self._current_pos != self._prev_pos

    def _getInsertedText(self):
        """
        Returns the last inserted character by the user or None when
        not applicable
        """
        if not self._cursorMoved():
            return

        # If the line has incremented by 1, the user has pressed Enter,
        # so fake this as a \n character
        if self._current_pos.line == self._prev_pos.line + 1:
            return '\n'

        current_line = vim.current.buffer[self._prev_pos.line]
        if not len(current_line) or self._prev_pos.column >= len(current_line):
            return

        return current_line[self._prev_pos.column]

    def _shouldCheckNow(self):
        """
        Evaluates the user input to decide if a check should be done
        """
        self._updateCursorTracking()
        _logger.debug("Change: %s", vim.eval('changenr()'))
        line = vim.current.buffer[self._current_pos.line]

        comment = _COMMENT_SCAN(line)
        if comment is not None:
            comment_start = comment.start()
            # Avoid checking if changes were made inside a comment
            if self._current_pos.column > comment_start:
                _logger.info("Insertion after comment")
                return False

        return self._getInsertedText() in (';', )

    ########################
    # Hooks for vim events #
    ########################

    def onInsertEnter(self):
        """
        Actions for vim's InsertEnter event
        """
        self._prev_pos.clear()

    def onInsertLeave(self):
        """
        Actions for vim's InsertLeave event
        """

    def onBufferVisit(self):
        """
        Notifies the hdlcc server that Vim user has entered the current
        buffer
        """
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = OnBufferVisit(self._host,
                                self._port,
                                project_file=project_file,
                                path=vim.current.buffer.name)

        request.sendRequestAsync(self._handleAsyncRequest)

    def onBufferLeave(self):
        """
        Notifies the hdlcc server that Vim user has left the current
        buffer
        """
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = OnBufferLeave(self._host,
                                self._port,
                                project_file=project_file,
                                path=vim.current.buffer.name)

        request.sendRequestAsync(self._handleAsyncRequest)

    def onTextChangedI(self):
        """
        Checks the characters being inserted to trigger as you type
        syntax checking
        """
        if self._shouldCheckNow():
            bufnum = vim.current.buffer.number
            vim.command("SyntasticCheck")
            vim.eval("setpos('.', [{0}, {1}, {2}])".format(
                bufnum, self._current_pos.line + 1, self._current_pos.column + 1))
            # Break the undo history so the user can undo until the point
            # where the check was triggered. This is now the ideal, but
            # it's the best so far :-\
            vim.eval('feedkeys("u")')


