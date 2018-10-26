#!/usr/bin/env python3

import logging

from pathlib import Path

import unittest

import __main__

import docker_setup

def iterate_tests(test_suite_or_case):
    """
    Iterate through all of the test cases in 'test_suite_or_case'.

    Copied from https://stackoverflow.com/questions/15487587/python-unittest-get-testcase-ids-from-nested-testsuite.

    """
    try:
        suite = iter(test_suite_or_case)
    except TypeError:
        yield test_suite_or_case
    else:
        for test in suite:
            for subtest in iterate_tests(test):
                yield subtest

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="test_logs.txt")

    
    docker_setup.ensure_docker_daemon_running()

    this_directory = Path(__main__.__file__).expanduser().resolve().parent
    toplevel = this_directory.parent.parent
    suite = unittest.TestLoader().discover(this_directory)

    # tests = [".".join(test.id().split(".")[2:]) for test in iterate_tests(suite)]
    # tests = [test.id() for test in iterate_tests(suite)]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
