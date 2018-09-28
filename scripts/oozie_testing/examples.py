#!/usr/bin/env python3

"""
This module provides functionality to run the Oozie examples in the Oozie server docker container.
"""

import logging

from typing import List

import docker

def _command_with_whitelist_and_blacklist(cmd_base: str, whitelist: List[str], blacklist: List[str]) -> str:
    cmd_whitelist = "-w {}".format(" ".join(whitelist)) if whitelist else ""
    cmd_blacklist = "-b {}".format(" ".join(blacklist)) if blacklist else ""

    return " ".join([cmd_base, cmd_whitelist, cmd_blacklist])

def run_oozie_examples_with_dbd(oozieserver: docker.models.containers.Container,
                                logfile: str,
                                report_file: str,
                                whitelist: List[str],
                                blacklist: List[str]) -> int:
    """
    Runs the Oozie examples in the Oozie server docker container.

    Args:
        oozieserver: The object representing the Oozie server.
        logfile: The path on the container's file system to the logfile that will
            be written by the script that runs the examples within the container.
        report_file: The path on the container's file system to the report file that will
            be written by the script that runs the examples within the container.
        whitelist: A list of examples that should be run. If provided, only these examples
            will be run, otherwise all non-blacklisted examples will be run.
        blacklist: A list of examples that should not be run.

    Returns:
        The exit code of the process running the test, which is 1 if any tests failed.

    """

    logging.info("Running the Oozie examples.")
    cmd_base = "python3 /opt/oozie/inside_container/example_runner.py --logfile {} --report {}".format(logfile,
                                                                                                       report_file)

    cmd = _command_with_whitelist_and_blacklist(cmd_base, whitelist, blacklist)

    (errcode, _) = oozieserver.exec_run(cmd, workdir="/opt/oozie")

    logging.info("Testing finished with exit code %s.", errcode)
    return errcode
