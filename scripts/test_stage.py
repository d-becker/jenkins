#!/usr/bin/env python3

from pathlib import Path

import logging
import subprocess
import sys
import time

from typing import Iterable, Tuple

import docker
import __main__

def build_configs_with_dbd(configurations: Path,
                           output_dir: Path,
                           dbd_path: Path,
                           cache: Path) -> None:
    logging.info("Building the configurations with dbd.")
    for configuration in configurations.expanduser().resolve().iterdir():
        if not configuration.is_dir():
            logging.info("Building configuration with filename %s.", str(configuration))
            command = [str(dbd_path), str(configuration), str(output_dir), "-c", str(cache)]
            subprocess.run(command, check=True)

def get_output_subdirs(output_dir: Path) -> Iterable[Path]:
    return output_dir.expanduser().resolve().iterdir()

def copy_files_to_container(container_name: str) -> None:
    script_path = Path(__main__.__file__)
    inside_container = script_path.expanduser().resolve().parent / "inside_container"

    logging.info("Copying files to the container.")
    command = ["docker", "cp", str(inside_container), "{}:/opt/oozie/".format(container_name)]
    subprocess.run(command, check=True)

def get_oozieserver() -> docker.models.containers.Container:
    docker_client = docker.from_env()

    filters = {"name" : ".*oozieserver.*"}
    return docker_client.containers.list(filters=filters)[0]

def docker_compose_up(directory: Path) -> None:
    logging.info("Starting the dockerised cluster.")
    command_up = ["docker-compose", "up", "-d"]
    subprocess.run(command_up, cwd=directory.expanduser().resolve())

def docker_compose_down(directory: Path) -> None:
    logging.info("Stopping the dockerised cluster.")
    command_down = ["docker-compose", "down"]
    subprocess.run(command_down, cwd=directory)

def upload_examples_to_hdfs(oozieserver: docker.models.containers.Container) -> None:
    logging.info("Uploading the tests to hdfs.")
    (errcode, _) = oozieserver.exec_run("/bin/bash /opt/oozie/inside_container/prepare_examples.sh",
                                        workdir="/opt/oozie")
    logging.info("Uploading the tests finished with exit code: %s.", errcode)

def test_oozie_with_dbd(oozieserver: docker.models.containers.Container) -> Tuple[int, str]:
    logging.info("Running the Oozie tests.")
    cmd = "python3 /opt/oozie/inside_container/example_runner.py -w map-reduce hive2" # TODO: Remove the whitelist.
    (errcode, output) = oozieserver.exec_run(cmd, workdir="/opt/oozie")

    logging.info("Testing finished with exit code %s.", errcode)
    return (errcode, output.decode())

def write_to_file(text: str, path: Path) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w") as file:
        file.write(text)

def copy_oozie_logs(oozieserver_name: str, output: Path) -> None:
    logging.info("Copying the Oozie logs.")
    command = ["docker", "cp", "{}:/opt/oozie/logs".format(oozieserver_name), str(output)]
    subprocess.run(command, check=True)

def main() -> None:
    configurations_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    reports_dir = Path("testing/reports")
    dbd_path = Path("testing/dbd/dbd/dbd.py")
    cache_dir = Path("./dbd_cache")

    build_configs_with_dbd(configurations_dir, output_dir, dbd_path, cache_dir)

    build_ok = True
    build_config_dirs = get_output_subdirs(output_dir)
    for build_config_dir in build_config_dirs:
        try:
            docker_compose_up(build_config_dir)
            oozieserver = get_oozieserver()

            copy_files_to_container(oozieserver.name)
            upload_examples_to_hdfs(oozieserver)

            exit_code, report = test_oozie_with_dbd(oozieserver)
            current_report_dir = reports_dir / build_config_dir.name
            report_file = current_report_dir / "report.txt"
            write_to_file(report, report_file)
            logging.info("Written test report file %s.", str(report_file))

            copy_oozie_logs(oozieserver.name, current_report_dir / "oozieserver")
            
            if exit_code != 0:
                build_ok = False

        except Exception as ex:
            print("An exception has occured: {}.".format(ex))
        finally:
            docker_compose_down(build_config_dir)

    if not build_ok:
        sys.exit(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

