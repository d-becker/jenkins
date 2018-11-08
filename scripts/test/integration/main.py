#!/usr/bin/env python3

"""
This script is the entry point to running the integration tests.
For more information, run the script with the "--help" switch.

"""

import argparse
import logging

from pathlib import Path

import re
import sys

from typing import Any, Iterable, List, Optional

import unittest

import __main__

import docker_setup

# We add the project root to the path to be able to access the project modules.
sys.path.append(str(Path("../..").resolve()))

def iterate_tests(test_suite_or_case: Iterable[Any]) -> Iterable[Any]:
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
    """
    Builds and returns an argument parser for the script entry point.

    Returns:
        An argument parser for the script entry point.

    """

    parser = argparse.ArgumentParser(description="Run the Oozie-dbd integration tests.")
    parser.add_argument("-t", "--tests", nargs="*", help="Only run tests that match any the provided regexes.")

    return parser

def any_regex_matches(string: str, regexes: List[str]) -> bool:
    """
    Checks whether any of the provided regexes matches the given string.

    Args:
        string: The string that will be checked agains the regexes.
        regexes: A list of regular expressions.

    Returns:
        True if any of `regexes` matches `string`; false otherwise.

    """

    return any(map(lambda regex: re.fullmatch(regex, string), regexes))

def filter_tests(tests: Iterable[Any], filter_test_regexes: Optional[List[str]]) -> Iterable[Any]:
    """
    Filters the provided tests by the given regular expressions. If `filter_test_regexes`
    is not None, only keeps the tests whoses name match any of the given regular expressions.
    If `filter_test_regexes` is None, keeps all tests.

    Args:
        tests: An iterable of tests.
        filter_test_regexes: An optional list of regular expressions.

    Returns:
        The iterable filtered as described above.

    """

    if filter_test_regexes is not None:
        regexes: List[str] = filter_test_regexes
        return filter(lambda test: any_regex_matches(test.id(), regexes), tests)

    return tests

def main() -> None:
    """
    The entry point of the script.
    """

    logging.basicConfig(level=logging.INFO,
                        filename="test_logs.txt")

    args = get_argument_parser().parse_args()

    docker_setup.ensure_docker_daemon_running()

    this_directory = Path(__main__.__file__).expanduser().resolve().parent
    discovered = unittest.TestLoader().discover(str(this_directory))

    tests = filter_tests(iterate_tests(discovered), args.tests)

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    main()
