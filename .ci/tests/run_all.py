#!/usr/bin/env python
"Test launcher"

import os
import os.path as p
import subprocess as subp

def _findFilesInPath(path, f=None):
    for filename in os.listdir(path):
        if filename.startswith('.'):
            continue
        file_with_path = p.join(path, filename)
        if f is None:
            yield file_with_path
        elif f(file_with_path):
            yield file_with_path

def _isVroom(path):
    return str(path).lower().endswith('vroom')

def _getVroomArgs():
    args = ['-u']
    if os.environ.get("CI", None) == "true":
        args += [p.expanduser('~/.vim/vimrc')]
    else:
        args += [p.expanduser('~/dot_vim/vimrc')]
    return args

def _getBashPair(path):
    return path.replace('.vroom', '.sh')

def main():
    test_dir = p.dirname(p.abspath(__file__))
    vroom_tests = _findFilesInPath(test_dir, _isVroom)
    for vroom_test in vroom_tests:
        bash_path = _getBashPair(vroom_test)
        if p.exists(bash_path):
            subp.check_call([bash_path, ])

        subp.check_call(['vroom', vroom_test, ] + _getVroomArgs())

if __name__ == '__main__':
    main()

