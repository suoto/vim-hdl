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
"VHDL static checking to find unused signals, ports and constants."

import re
import logging

__logger__ = logging.getLogger(__name__)

__SCANNER__ = re.compile('|'.join([
    r"^\s*(\w+)\s*:\s*entity\s+\w+",
    r"^\s*(\w+)\s*:\s*\w+\s*$",
    r"^\s*constant\s+(\w+)\s*:",
    r"^\s*signal\s+(\w+)\s*:",
    #  r"^\s*type\s+(\w+)\s+is",
    r"^\s*(\w+)\s*:\s*in\s+\w+",
    r"^\s*(\w+)\s*:\s*out\s+\w+",
    r"^\s*(\w+)\s*:\s*inout\s+\w+",
    r"^\s*(\w+)\s*:\s*\w+[^:]*:=",
    #  r"^\s*library\s+(\w+)",
    #  r"^\s*attribute\s+(\w+)\s*:",
]), flags=re.I)

__SCANNER_INDEX_TO_TYPE_MAP__ = {
    3  : 'Constant',
    4  : 'Signal',
    5  : 'Type',
    6  : 'Input port',
    7  : 'Output port',
    8  : 'IO port',
    9  : 'Generic',
    10 : 'Library',
    11 : 'Attribute',
}

__END_OF_SCAN__ = re.compile('|'.join([
    r"\bport\s+map",
    r"\bgenerate\b",
    r"\w+\s*:\s*entity",
    r"\bprocess\b",
    ]))

def _getObjectsFromText(text_buffer):
    """Returns a dict containing the objects found at the given text
    buffer"""
    objects = {}
    lnum = 0
    for _line in text_buffer:
        line = re.sub(r"\s*--.*", "", _line)
        scan = __SCANNER__.scanner(line)
        while True:
            match = scan.match()
            if not match:
                break
            start = match.start(match.lastindex)
            end = match.end(match.lastindex)
            text = match.group(match.lastindex)
            __logger__.info("%d, %d => %s", lnum, match.lastindex, \
                    repr(match.group(match.lastindex)))

            if match.lastindex >= 3:
                if text not in objects.keys():
                    objects[text] = {}
                objects[text]['lnum'] = lnum
                objects[text]['start'] = start
                objects[text]['end'] = end

            if match.lastindex in __SCANNER_INDEX_TO_TYPE_MAP__.keys():
                objects[text]['type'] = __SCANNER_INDEX_TO_TYPE_MAP__[match.lastindex]

        lnum += 1

        if __END_OF_SCAN__.findall(line):
            break

    return objects

def _getUnusedObjects(text_buffer, objects):
    """Generator that yields objects that are only found once at the
    given buffer and thus are considered unused (i.e., we only found
    its declaration"""

    text = ''
    for line in text_buffer:
        text += re.sub(r"\s*--.*", "", line) + ' '

    for _object in objects:
        r_len = 0
        single = True
        for _ in re.finditer(r"\b%s\b" % _object, text):
            r_len += 1
            if r_len > 1:
                single = False
                break
        if single:
            yield _object

def vhdStaticCheck(text_buffer=None):
    "VHDL static checking"
    try:
        import vim
    except ImportError:
        return
    text_buffer = text_buffer or vim.current.buffer
    objects = _getObjectsFromText(text_buffer)

    result = []

    for _object in _getUnusedObjects(text_buffer, objects.keys()):
        obj_dict = objects[_object]
        vim_fmt_dict = vim.Dictionary({
            'lnum'     : obj_dict['lnum'] + 1,
            'bufnr'    : vim.current.buffer.number,
            'filename' : vim.current.buffer.name,
            'valid'    : '1',
            'text'     : "{obj_type} '{obj_name}' is never used".format(
                obj_type=obj_dict['type'], obj_name=_object),
            'nr'       : '0',
            'type'     : 'W',
            'subtype'  : 'Style',
            'col'      : obj_dict['start'] + 1
        })

        result.append(vim_fmt_dict)

    vim.vars['vimhdl_static_check_result'] = vim.List(result)


