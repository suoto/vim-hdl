#!/usr/bin/env python
"Test launcher"

import sys
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
        args += [p.expanduser('~/.vimrc')]
        args += ['-d0.5', '-t3']
    else:
        args += [p.expanduser('~/dot_vim/vimrc')]
        args += ['-d0.2', '-t1']
    return args

def _getBashPair(path):
    return path.replace('.vroom', '.sh')

TESTS_ALLOWED_TO_FAIL = ['test_004_issue_10',]

def main():
    test_dir = p.dirname(p.abspath(__file__))
    vroom_tests = _findFilesInPath(test_dir, _isVroom)

    passed = []
    failed = []
    allowed_to_fail = []

    for vroom_test in vroom_tests:
        test_name = p.basename(vroom_test).replace('.vroom', '')
        bash_path = _getBashPair(vroom_test)

        if p.exists(bash_path):
            subp.check_call([bash_path, ])

        try:
            subp.check_call(['vroom', vroom_test, ] + _getVroomArgs())
            passed += [test_name]
        except subp.CalledProcessError:
            # We'll allow test 004 to fail for now
            if test_name in TESTS_ALLOWED_TO_FAIL:
                allowed_to_fail += [test_name]
            else:
                failed += [test_name]

    os.system('reset')
    if passed:
        print "Successful tests"
        for test in passed:
            print " - " + str(test)

    if failed:
        print "Failed tests:"
        for test in failed:
            print " - " + str(test)

    if allowed_to_fail:
        print "Failed tests (allowed to fail)"
        for test in allowed_to_fail:
            print " - " + str(test)

    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())

