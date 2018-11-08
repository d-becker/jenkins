#!/usr/bin/env python3

"""
This module contains functions that can be used to set up the docker environment for integration testing.
"""

import errno
import logging
import subprocess
import sys
import time

from typing import List

def _is_command_available(command: str) -> bool:
    try:
        subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        if error.errno == errno.ENOENT:
            return False

        raise

    return True

def is_docker_command_available() -> bool:
    """
    Checks whether the `docker` command is available on the machine.

    Returns:
        True if the `docker` command is available on the machine; false otherwise.

    """

    return _is_command_available("docker")

def is_docker_compose_command_available() -> bool:
    """
    Checks whether the `docker-compose` command is available on the machine.

    Returns:
        True if the `docker-compose` command is available on the machine; false otherwise.

    """

    return _is_command_available("docker-compose")

def is_docker_daemon_running() -> bool:
    """
    Checks whether the docker daemon is running.

    Returns:
        True if the docker daemon is running; false otherwise.

    """

    command = ["docker", "version"]
    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return process_result.returncode == 0

class DockerError(Exception):
    """
    An exception used in the integration tests for problems concerning Docker.
    """
    pass

def _wait_for_docker_daemon_to_start(timeout: int) -> None:
    logging.info("Waiting for docker daemon to start.")

    start = time.time()
    while not is_docker_daemon_running() and (time.time() - start) < timeout:
        time.sleep(1)

    if not is_docker_daemon_running():
        msg = "Timed out waiting for docker daemon to start."
        logging.error(msg)
        raise DockerError(msg)

    logging.info("Docker daemon is running.")

def start_docker_daemon() -> None:
    """
    Starts the docker daemon.

    Raises:
        DockerError: Raised if this function is called on an unsupported
            operating system. Only Linux and MacOS are supported.

    """

    logging.info("Starting docker daemon.")

    command: List[str]
    if sys.platform.startswith("linux"):
        command = ["sudo", "systemctl", "start", "docker"]
    elif sys.platform.startswith("darwin"):
        command = ["open", "--background", "-a", "Docker"]
    else:
        msg = "Unsupported operating system: {}.".format(sys.platform)
        logging.error(msg)
        raise DockerError(msg)

    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process_result.returncode != 0:
        msg = ("Error starting the docker daemon: process returned {}.\n"
               + "****************\n"
               + "**** Stdout ****\n{}\n"
               + "**** Stderr ****\n{}"
               + "****************").format(process_result.returncode,
                                            process_result.stdout.decode(),
                                            process_result.stderr.decode())
        logging.error(msg)
        raise DockerError(msg)

    _wait_for_docker_daemon_to_start(120)

def ensure_docker_daemon_running() -> None:
    """
    Ensures that the docker daemon is running, starting it if it is not.

    Raises:
        DockerError: Raised if this function is called on an unsupported
            operating system. Only Linux and MacOS are supported.

    """

    if is_docker_daemon_running():
        logging.info("Docker daemon is running.")
        return

    if not is_docker_command_available():
        msg = "Docker does not seem to be installed: missing command `docker`."
        logging.error(msg)
        raise DockerError(msg)

    start_docker_daemon()
