#!/usr/bin/env python3

"""
This module provides functions that can be used to interact with the dockerised cluster from the local host.
"""

from pathlib import Path

import logging
import subprocess

import docker

import oozie_testing.inside_container

class DockerSubprocessException(Exception):
    """
    An exception that is thrown when subprocesses related to Docker fail.
    """

    def __init__(self,
                 message: str,
                 process_result: subprocess.CompletedProcess) -> None:
        """
        Creates a `DockerSubprocessException`.

        Args:
            message: A user-defined message - it can be used to describe the concrete situation.
            process_result: The `subprocess.CompletedProcess` object returned by the process running function.

        """

        self.message = message
        self.returncode = process_result.returncode
        self.stdout = process_result.stdout
        self.stderr = process_result.stderr

        exception_message = "{}\nReturn code:\n{}\nStdout:\n{}\nStderr:\n{}".format(self.message,
                                                                                    self.returncode,
                                                                                    self.stdout,
                                                                                    self.stderr)
        super().__init__(exception_message)

def _get_first_container_of_service(service_name: str) -> docker.models.containers.Container:
    docker_client = docker.from_env()

    filters = {"name" : ".*{}.*".format(service_name)}
    return docker_client.containers.list(filters=filters)[0]

def get_oozieserver() -> docker.models.containers.Container:
    """
    Returns the Oozie server in the dockerised cluster. If there are multiple Oozie servers, returns one of them.

    Returns:
        The Oozie server in the dockerised cluster.

    """

    return _get_first_container_of_service("oozieserver")

def get_nodemanager() -> docker.models.containers.Container:
    """
    Returns the node manager in the dockerised cluster. If there are multiple node managers, returns one of them.

    Returns:
        The node manager in the dockerised cluster, or one of them if there are several.

    """

    return _get_first_container_of_service("nodemanager")

def docker_compose_up(directory: Path) -> None:
    """
    Starts a docker-compose cluster.

    Args:
        directory: The docker-compose directory in which the docker-compose.yaml file
            and any additional resources are located.

    """

    logging.info("Starting the dockerised cluster.")
    command_up = ["docker-compose", "up", "-d"]
    process_result = subprocess.run(command_up, cwd=directory.expanduser().resolve(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process_result.returncode != 0:
        raise DockerSubprocessException("Error: `docker-compose up` failed.", process_result)

def docker_compose_down(directory: Path) -> None:
    """
    Brings down a docker-compose cluster.

    Args:
        directory:The docker-compose directory in which the docker-compose.yaml file
            and any additional resources are located.

    """

    logging.info("Stopping the dockerised cluster.")
    command_down = ["docker-compose", "down"]
    process_result = subprocess.run(command_down, cwd=directory.expanduser().resolve(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process_result.returncode != 0:
        raise DockerSubprocessException("Error: `docker-compose down` failed.", process_result)

def docker_cp_to_container(container_name: str, source: str, dest: str) -> None:
    """
    Copies a file or directory from the local file system to a running docker container.

    Args:
        container_name: The name of the docker container to copy to.
        source: The path on the local file system of the source file or directory that should be copied.
        dest: The path on the container's file system to which the source should be copied.

    """

    command = ["docker", "cp", source, "{}:{}".format(container_name, dest)]
    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process_result.returncode != 0:
        raise DockerSubprocessException("Error: docker copy to container failed.", process_result)

def docker_cp_from_container(container_name: str, source: str, dest: str) -> None:
    """
    Copies a file or directory from a running docker container to the local file system.

    Args:
        container_name: The name of the docker container to copy from.
        source: The path on the file system of the container of the source file or directory that should be copied.
        dest: The path on the local file system to which the source should be copied.

    """

    command = ["docker", "cp", "{}:{}".format(container_name, source), dest]
    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process_result.returncode != 0:
        raise DockerSubprocessException("Error: docker copy from container failed.", process_result)

def copy_test_script_files_to_container(oozieserver_name: str) -> None:
    """
    Copies the script files that will be run within the container to test Oozie.

    Args:
        oozieserver_name: The name of the Oozie server container, to which the scripts will be copied.

    """

    inside_container = Path(oozie_testing.inside_container.__file__).parent.expanduser().resolve()

    logging.info("Copying files to the container.")
    docker_cp_to_container(oozieserver_name, str(inside_container), "/opt/oozie/")

def upload_examples_to_hdfs(oozieserver: docker.models.containers.Container) -> None:
    """
    Uploads the Oozie examples from the Oozie server's local file system to HDFS.

    Args:
        oozieserver: The object representing the Oozie server.

    """

    logging.info("Uploading the tests to hdfs.")
    (errcode, _) = oozieserver.exec_run("/bin/bash /opt/oozie/inside_container/prepare_examples.sh",
                                        workdir="/opt/oozie")
    logging.info("Uploading the tests finished with exit code: %s.", errcode)

def setup_testing_env_in_container(oozieserver: docker.models.containers.Container) -> None:
    """
    Prepares the Oozie server for running the examples by copying the necessary
    scripts to the Oozie server container and uploading the examples to HDFS.

    Args:
        oozieserver: The object representing the Oozie server.

    """

    copy_test_script_files_to_container(oozieserver.name)
    upload_examples_to_hdfs(oozieserver)

def copy_oozie_logs(oozieserver_name: str, output: Path) -> None:
    """
    Copies the Oozie log directory from the Oozie server to the local file system.

    Args:
        oozieserver_name: The name of the Oozie server.
        output: The path on the local file system to which the logs will be copied.

    """

    logging.info("Copying the Oozie logs to %s.", output)

    docker_cp_from_container(oozieserver_name, "/opt/oozie/logs", str(output))

def copy_yarn_logs(nodemanager_name: str, output: Path) -> None:
    """
    Copies the Yarn logs from the node manager to the local file system.

    Args:
        nodemanager_name: The name of the node manager container.
        output: The path on the local file system to which the logs will be copied.

    """

    logging.info("Copying the Yarn logs to %s.", output)

    output.mkdir(parents=True, exist_ok=True)

    docker_cp_from_container(nodemanager_name, "/tmp/hadoop-hadoop/nm-local-dir", str(output / "nm-local-dir"))
    docker_cp_from_container(nodemanager_name, "/opt/hadoop/logs/userlogs", str(output / "hadoop-logs"))

def copy_logfile_and_report_records(oozieserver_name: str, logfile: str, report_file: str, output: Path) -> None:
    """
    Copies the logfile and report file of the script that has run the
    Oozie examples on the Oozie server to the local file system.

    Args:
        oozieserver_name: The name of the Oozie server container.
        logfile: The path on the Oozie server container's file system to
            the logfile that was produced by the example runner script.
        report_file: The path on the Oozie server container's file system to
            the report file that was produced by the example runner script.
        output: The directory on the local file system to which the logfile and the report file will be copied.

    """

    logging.info("Copying the example running logfile and report.")

    output.mkdir(parents=True, exist_ok=True)

    docker_cp_from_container(oozieserver_name, "/opt/oozie/{}".format(logfile), str(output))
    docker_cp_from_container(oozieserver_name, "/opt/oozie/{}".format(report_file), str(output))
