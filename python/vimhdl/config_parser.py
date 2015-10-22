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
"""Extended version of ConfigParser.SafeConfigParser to add a method to return
a list split at multiple whitespaces"""

import re
import ConfigParser

_RE_LEADING_AND_TRAILING_WHITESPACES = re.compile(r"^\s*|\s*$")
_RE_MULTIPLE_WHITESPACES = re.compile(r"\s+")

class ExtendedConfigParser(ConfigParser.SafeConfigParser):
    def getlist(self, section, option):
        entry = self.get(section, option)
        entry = _RE_LEADING_AND_TRAILING_WHITESPACES.sub("", entry)
        if entry:
            return _RE_MULTIPLE_WHITESPACES.split(entry)
        else:
            return []

