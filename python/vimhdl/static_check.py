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

__AREA_SCANNER__ = re.compile('|'.join([
    r"^\s*entity\s+(?P<entity_name>\w+)\s+is\b",
    r"^\s*architecture\s+(?P<architecture_name>\w+)\s+of\s+(?P<arch_entity>\w+)",
    r"^\s*package\s+(?P<package_name>\w+)\s+is\b",
    r"^\s*package\s+body\s+(?P<package_body_name>\w+)\s+is\b",
    ]), flags=re.I)

__NO_AREA_SCANNER__ = re.compile('|'.join([
    r"^\s*library\s+(?P<library>\w+)",
    r"^\s*attribute\s+(?P<attribute>\w+)\s*:",
    ]), flags=re.I)

__ENTITY_SCANNER__ = re.compile('|'.join([
    r"^\s*(?P<port>\w+)\s*:\s*(in|out|inout)\s+\w+",
    r"^\s*(?P<generic>\w+)\s*:\s*\w+[^:]*:=",
    ]), flags=re.I)

__ARCH_SCANNER__ = re.compile('|'.join([
    r"^\s*constant\s+(?P<constant>\w+)\s*:",
    r"^\s*signal\s+(?P<signal>\w+)\s*:",
    r"^\s*type\s+(?P<type>\w+)\s*:",
    r"^\s*shared\s+variable\s+(?P<shared_variable>\w+)\s*:",
    ]), flags=re.I)

__END_OF_SCAN__ = re.compile('|'.join([
    r"\bport\s+map",
    r"\bgenerate\b",
    r"\w+\s*:\s*entity",
    r"\bprocess\b",
    ]))

def _getObjectsFromText(vbuffer):
    """Returns a dict containing the objects found at the given text
    buffer"""
    objects = {}
    lnum = 0
    area = None
    for _line in vbuffer:
        line = re.sub(r"\s*--.*", "", _line)
        for match in __AREA_SCANNER__.finditer(line):
            _dict = match.groupdict()
            if _dict['entity_name'] is not None:
                area = 'entity'
            elif _dict['architecture_name'] is not None:
                area = 'architecture'
            elif _dict['package_name'] is not None:
                area = 'package'
            elif _dict['package_body_name'] is not None:
                area = 'package_body'

        matches = []
        if area is None:
            for match in __NO_AREA_SCANNER__.finditer(line):
                matches += [match]
        elif area == 'entity':
            for match in __ENTITY_SCANNER__.finditer(line):
                matches += [match]
        elif area == 'architecture':
            for match in __ARCH_SCANNER__.finditer(line):
                matches += [match]

        for match in matches:
            for key, value in match.groupdict().items():
                if value is None: continue
                start = match.start(match.lastindex)
                end = match.end(match.lastindex)
                text = match.group(match.lastindex)
                if text not in objects.keys():
                    objects[text] = {}
                objects[text]['lnum'] = lnum
                objects[text]['start'] = start
                objects[text]['end'] = end
                objects[text]['type'] = key
        lnum += 1
        if __END_OF_SCAN__.findall(line):
            break

    return objects

def _getUnusedObjects(vbuffer, objects):
    """Generator that yields objects that are only found once at the
    given buffer and thus are considered unused (i.e., we only found
    its declaration"""

    text = ''
    for line in vbuffer:
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

def vhdStaticCheck(vbuffer=None):
    "VHDL static checking"
    objects = _getObjectsFromText(vbuffer)

    result = []

    for _object in _getUnusedObjects(vbuffer, objects.keys()):
        obj_dict = objects[_object]
        message = {
            'checker'        : 'vim-hdl/static',
            'line_number'    : obj_dict['lnum'] + 1,
            'column'         : obj_dict['start'] + 1,
            'filename'       : None,
            'error_number'   : '0',
            'error_type'     : 'W',
            'error_subtype'  : 'Style',
            'error_message'  : "{obj_type} '{obj_name}' is never used".format(
                obj_type=obj_dict['type'], obj_name=_object),
            }

        result.append(message)

    return result

def standalone():
    import sys
    for arg in sys.argv[1:]:
        print arg
        for message in vhdStaticCheck(open(arg, 'r').read().split('\n')):
            print message
        print "="*10

if __name__ == '__main__':
    standalone()

