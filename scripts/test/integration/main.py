#!/usr/bin/env python3

import argparse
import logging

from pathlib import Path

import re

from typing import Any, Iterable, List, Optional

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

def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Oozie-dbd integration tests.")
    parser.add_argument("-t", "--tests", nargs="*", help="Only run tests that match any the provided regexes.")

    return parser

def any_regex_matches(string: str, regexes: List[str]) -> bool:
    return any(map(lambda regex: re.fullmatch(regex, string), regexes))

def filter_tests(tests: list, filter_test_regexes: Optional[List[str]]) -> Iterable[Any]:
    if filter_test_regexes is not None:
        regexes: List[str] = filter_test_regexes
        return filter(lambda test: any_regex_matches(test.id(), regexes), tests)

    return tests

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        filename="test_logs.txt")

    args = get_argument_parser().parse_args()

    docker_setup.ensure_docker_daemon_running()

    this_directory = Path(__main__.__file__).expanduser().resolve().parent
    toplevel = this_directory.parent.parent
    discovered = unittest.TestLoader().discover(str(this_directory))

    tests = filter_tests(iterate_tests(discovered), args.tests)

    # print("All discovered:", list(iterate_tests(discovered))) # TODO
    # print("Filtered:",list(tests)) # TODO
    
    suite = unittest.TestSuite(tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
