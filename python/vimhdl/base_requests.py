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

import logging
import requests
import threading

_logger = logging.getLogger(__name__)

class BaseRequest(object):
    "Base request object"
    _meth = ''
    timeout = 3
    _lock = threading.Lock()

    def __init__(self, host, port, **kwargs):
        if host.startswith('http://'): # pragma: no cover
            self.url = '%s:%s' % (host, port)
        else:
            self.url = 'http://%s:%s' % (host, port)

        self.payload = kwargs
        _logger.debug("Creating request for '%s' with payload '%s'",
                      self._meth, self.payload)

    def sendRequestAsync(self, func):
        """Processes the request in a separate thread and puts the
        received request on queue Q"""
        if self._lock.locked():
            return
        def asyncRequest():
            "Simple asynchronous request wrapper"
            try:
                with self._lock:
                    func(self.sendRequest())
            except: # pragma: no cover
                _logger.exception("Error sending request")
                raise
        threading.Thread(target=asyncRequest).start()

    def sendRequest(self):
        """Blocking send request. Returns a response object should the
        server respond. It only catches a ConnectionError exception
        (this means the server could not be reached). In this case,
        return is None"""
        try:
            response = requests.post(self.url + '/' + self._meth,
                                     data=self.payload,
                                     timeout=self.timeout)
            if not response.ok: # pragma: no cover
                _logger.warning("Server response error: '%s'", response.text)
                response = None
        except requests.exceptions.ConnectionError:
            _logger.warning("Error connecting to server")
            return

        return response

class RequestMessagesByPath(BaseRequest):
    "Request messages for the quickfix list"
    _meth = 'get_messages_by_path'

    def __init__(self, host, port, project_file, path):
        super(RequestMessagesByPath, self).__init__(
            host, port,
            project_file=project_file, path=path)

class RequestQueuedMessages(BaseRequest):
    "Request UI messages"
    _meth = 'get_ui_messages'

    def __init__(self, host, port, project_file):
        super(RequestQueuedMessages, self).__init__(host, port,
                                                    project_file=project_file)

class RequestHdlccInfo(BaseRequest):
    "Request UI messages"
    _meth = 'get_diagnose_info'

    def __init__(self, host, port, project_file):
        super(RequestHdlccInfo, self).__init__(host, port,
                                               project_file=project_file)
