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
"Wrapper for vim-hdl usage within Vim's Python interpreter"

import os.path as p
import logging
import subprocess as subp
import signal
import os
from multiprocessing import Queue

import vim # pylint: disable=import-error
import vimhdl.vim_helpers as vim_helpers
from vimhdl.base_requests import RequestMessagesByPath, RequestQueuedMessages

_logger = logging.getLogger(__name__)

def _sortBuildMessages(records):
    "Sorts the build messages using Vim's terminology"
    for record in records:
        for key in ('lnum', 'nr', 'col'):
            try:
                record[key] = int(record[key])
            except ValueError:
                pass
    records.sort(key=lambda x: (x['type'], x['lnum'], x['col'], x['nr']))
    return records

#############################################
# Functions that are actually called by Vim #
#############################################
class VimhdlClient(object):
    "Main vimhdl client class"

    def __init__(self, **options):
        self._logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self._logger.info("Creating vimhdl client object...")

        self._server = None
        self._host = options.get('host', 'localhost')
        self._port = options.get('port', vim_helpers.getUnusedLocalhostPort())
        self._log_level = options.get('log_level', 'DEBUG')
        self._log_target = options.get('log_target', '/tmp/hdlcc.log')

        self._ui_queue = Queue()
        self.setup()
        # FIXME: The server takes a while to start, find a clean way to
        # circumvent this
        import time
        time.sleep(0.3)

        import atexit
        atexit.register(self.shutdown)

    def _isServerAlive(self):
        "Checks if the the server is alive"
        return self._server.poll() is None

    def setup(self):
        "Launches the hdlcc server"
        self._logger.info("Running initial Vim setup")

        vimhdl_path = p.abspath(p.join(p.dirname(__file__), '..', '..'))

        hdlcc_server = p.join(vimhdl_path, 'dependencies', 'hdlcc', 'hdlcc',
                              'code_checker_server.py')

        cmd = [hdlcc_server,
               '--host', self._host,
               '--port', str(self._port),
               '--log-level', str(self._log_level),
               '--log-stream', self._log_target]

        self._logger.info(" ".join(cmd))

        try:
            self._server = subp.Popen(cmd, stdout=subp.PIPE)
        except subp.CalledProcessError:
            self._logger.exception("Error calling '%s'", " ".join(cmd))

    def shutdown(self):
        "Kills the hdlcc server"
        if not self._isServerAlive():
            self._logger.info("Server is not running")
            return
        self._logger.debug("Sending shutdown signal")
        os.kill(self._server.pid, signal.SIGHUP)
        self._logger.debug("Done")

    def requestUiMessages(self):
        """Retrieves UI messages from the server and post them with the
        appropriate severity level"""
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = RequestQueuedMessages(self._host, self._port,
                                        project_file=project_file)

        request.sendRequestAsync(self._handleAsyncRequest)

    def _handleAsyncRequest(self, response):
        "Callback passed to asynchronous requests"
        if response is not None:
            self._ui_queue.put(response)

    def _postQueuedMessages(self):
        "Empty our queue in a single message"
        while not self._ui_queue.empty():
            messages = self._ui_queue.get()
            for severity, message in messages.json().get('ui_messages', []):
                if severity == 'info':
                    vim_helpers.postVimInfo(message)
                elif severity == 'warning':
                    vim_helpers.postVimWarning(message)
                elif severity == 'error':
                    vim_helpers.postVimError(message)
                else:
                    vim_helpers.postVimError(
                        "Unknown severity '%s' for message '%s'" %
                        (severity, message))

    # More info on :help getqflist()
    def getMessages(self, vim_buffer=None):
        '''Returns a list (vim.List) of messages (vim.Dictionary) to
        populate the quickfix list'''
        if not self._isServerAlive():
            return

        if vim_buffer is None:
            vim_buffer = vim.current.buffer

        project_file = vim_helpers.getProjectFile()
        path = p.abspath(vim_buffer.name)

        request = RequestMessagesByPath(host=self._host, port=self._port,
                                        project_file=project_file, path=path)

        response = request.sendRequest()
        if response is None:
            return

        messages = []
        for message in response.json().get('messages', []):
            vim_fmt_dict = {
                'lnum'     : message['line_number'] or '-1',
                'bufnr'    : vim_buffer.number,
                'filename' : message['filename'] or vim_buffer.name,
                'valid'    : '1',
                'text'     : message['error_message'] or '<none>',
                'nr'       : message['error_number'] or '0',
                'type'     : message['error_type'] or 'E',
                'col'      : message['column'] or '0'
            }
            try:
                vim_fmt_dict['subtype'] = message['error_subtype']
            except KeyError:
                pass

            _logger.info(vim_fmt_dict)

            messages.append(vim_helpers.dict(vim_fmt_dict))

        self.requestUiMessages()

        return vim_helpers.list(_sortBuildMessages(messages))




