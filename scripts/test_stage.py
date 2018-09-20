#!/usr/bin/env python3

import argparse
import io

from pathlib import Path

import logging
import pickle
import subprocess
import sys
import time

from typing import Dict, Iterable, List, Tuple

import xml.etree.ElementTree as ET

import docker
import __main__

sys.path.append(str(Path(__main__.__file__).parent / "inside_container"))

import report

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

def _get_first_container_of_service(service_name: str) -> docker.models.containers.Container:
    docker_client = docker.from_env()

    filters = {"name" : ".*{}.*".format(service_name)}
    return docker_client.containers.list(filters=filters)[0]

def get_oozieserver() -> docker.models.containers.Container:
    return _get_first_container_of_service("oozieserver")

def get_nodemanager() -> docker.models.containers.Container:
    return _get_first_container_of_service("nodemanager")

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

def test_oozie_with_dbd(oozieserver: docker.models.containers.Container,
                        logfile: str,
                        report_file: str,
                        whitelist: List[str],
                        blacklist: List[str]) -> Tuple[int, str]:
    logging.info("Running the Oozie tests.")
    cmd_base = "python3 /opt/oozie/inside_container/example_runner.py --logfile {} --report {}".format(logfile, report_file)
    cmd_whitelist = "-w {}".format(" ".join(whitelist)) if whitelist else ""
    cmd_blacklist = "-b {}".format(" ".join(blacklist)) if blacklist else ""

    cmd = " ".join([cmd_base, cmd_whitelist, cmd_blacklist])
    
    (errcode, _) = oozieserver.exec_run(cmd, workdir="/opt/oozie")

    logging.info("Testing finished with exit code %s.", errcode)
    return errcode

def write_to_file(text: str, path: Path) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w") as file:
        file.write(text)

def copy_oozie_logs(oozieserver_name: str, output: Path) -> None:
    logging.info("Copying the Oozie logs.")
    command = ["docker", "cp", "{}:/opt/oozie/logs".format(oozieserver_name), str(output)]
    subprocess.run(command, check=True)

def copy_yarn_logs(nodemanager_name: str, output: Path) -> None:
    logging.info("Copying the Yarn logs.")

    output.mkdir(parents=True, exist_ok=True)
    
    command_copy_nm_local_dir = ["docker", "cp", "{}:/tmp/hadoop-hadoop/nm-local-dir".format(nodemanager_name),
                                 str(output / "nm-local-dir")]
    subprocess.run(command_copy_nm_local_dir, check=True)

    command_copy_hadoop_logs = ["docker", "cp", "{}:/opt/hadoop/logs/userlogs".format(nodemanager_name),
                                str(output / "hadoop-logs")]
    subprocess.run(command_copy_hadoop_logs, check=True)

def get_logs_for_yarn_application(application_id: str, report_and_log_dir: Path) -> Dict[str, Tuple[str, str]]:
    """
    Returns the logs for the given yarn application. The returned object is a dict, where the keys are the names of the
    containers corresponding to the yarn application and the values are tuples the first element of which is the stdout
    and the second is the stderr output of the container.

    Args:
        application_id: The id of the yarn application.

    Returns:
        A dictionary with the results described above.
    """

    application_path = (report_and_log_dir / "hadoop-logs" / application_id).expanduser().resolve()

    if not application_path.exists():
        return {}

    res: Dict[str, Tuple[str, str]] = {}
    containers = filter(lambda dir_path: dir_path.is_dir() and dir_path.name.startswith("container"),
                        application_path.iterdir())
    for container in containers:
        stdout_file = container / "stdout"
        stdout_text: str

        with stdout_file.open() as stdout:
            stdout_text = stdout.read()

        stderr_file = container / "stderr"
        stderr_text: str

        with stderr_file.open() as stderr:
            stderr_text = stderr.read()

        res[container.name] = (stdout_text, stderr_text)

    return res

def printable_logs_for_oozie_job(record: report.ReportRecord, report_and_log_dir: Path) -> Tuple[str, str]:
    """
    Returns a pair of strings, the first element of which is the aggregated stdout output of all
    containers and applications corresponding to the job, the second is the stderr output. 
    """

    stdout = io.StringIO()
    stderr = io.StringIO()

    for application_id in record.applications:
        application_header = "{asterisks}\n**{id}**\n{asterisks}\n\n".format(asterisks="*" * (len(application_id) + 4),
                                                                             id=application_id)
        stdout.write(application_header)
        stderr.write(application_header)
        
        container_logs = get_logs_for_yarn_application(application_id, report_and_log_dir / "nodemanager")
        for (container_id, (out, err)) in container_logs.items():
            container_header = "**{}**\n\n".format(container_id)
            stdout.write(container_header + out + "\n\n")
            stderr.write(container_header + err + "\n\n")

    return (stdout.getvalue(), stderr.getvalue())
        

def copy_logfile_and_report_records(oozieserver_name: str, logfile: str, report_file: str, output: Path) -> None:
    logging.info("Copying the example running logfile and report.")

    output.mkdir(parents=True, exist_ok=True)

    command_copy_logfile = ["docker", "cp", "{}:/opt/oozie/{}".format(oozieserver_name, logfile),
                            str(output)]
    subprocess.run(command_copy_logfile, check=True)

    command_copy_report_file = ["docker", "cp", "{}:/opt/oozie/{}".format(oozieserver_name, report_file),
                                str(output)]
    subprocess.run(command_copy_report_file, check=True)

def generate_report(report_records: List[report.ReportRecord], report_and_log_dir: Path) -> ET.ElementTree:
    testsuite = ET.Element("testsuite", attrib={"tests" : str(len(report_records))})

    for record in report_records:
        testcase = ET.Element("testcase", attrib={"classname" : "OozieExamples", "name" : record.name})
        result = record.result
        if result == report.Result.SKIPPED:
            ET.SubElement(testcase, "skipped")
        elif result == report.Result.TIMED_OUT:
            ET.SubElement(testcase, "failure", attrib={"type" : "timeout"})
        elif result == report.Result.KILLED:
            ET.SubElement(testcase, "failure", attrib={"type" : "killed"})
        elif result == report.Result.FAILED:
            ET.SubElement(testcase, "failure", attrib={"type" : "failed"})
        elif result == report.Result.ERROR:
            ET.SubElement(testcase, "error", attrib={"type" : "error"})
        else:
            assert(result == report.Result.SUCCEEDED)

        # Aggregate the Yarn logs of the containers and add them to system-out and system-err elements.
        (stdout, stderr) = printable_logs_for_oozie_job(record, report_and_log_dir)
        stdout_element = ET.SubElement(testcase, "system-out")
        stdout_element.text = stdout
        stderr_element = ET.SubElement(testcase, "system-err")
        stderr_element.text = stderr

        testsuite.append(testcase)

    return ET.ElementTree(testsuite)

def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generates the dbd configuration directories and runs "
                                     + "the Oozie examples within the resulting dockerised clusters.")
    parser.add_argument("configurations_dir", help="The directory in which the BuildConfiguration files are located.")
    parser.add_argument("output_dir", help="The directory in which the output of the build will be generated.")
    parser.add_argument("-w", "--whitelist",
                        metavar="WHITELIST", nargs="*",
                        help="Only run the whitelisted examples. Otherwise, all detected examples are run.")
    parser.add_argument("-b", "--blacklist",
                        metavar="BLACKLIST", nargs="*",
                        help="Do not run the blacklisted examples.")

    return parser

def main() -> None:
    parser = get_argument_parser()
    args = parser.parse_args()
    
    configurations_dir = Path(args.configurations_dir)
    output_dir = Path(args.output_dir)
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

            logfile = "example_runner.log"
            report_records_file = "report_records.pickle"
            
            exit_code = test_oozie_with_dbd(oozieserver, logfile, report_records_file, args.whitelist, args.blacklist)

            current_report_dir = reports_dir / build_config_dir.name

            copy_logfile_and_report_records(oozieserver.name, logfile, report_records_file, current_report_dir)
            copy_oozie_logs(oozieserver.name, current_report_dir / "oozieserver")

            nodemanager = get_nodemanager()
            copy_yarn_logs(nodemanager.name, current_report_dir / "nodemanager")

            # Generate report.
            report_records: List[report.ReportRecord]
            local_report_records_file = current_report_dir / report_records_file
            with (local_report_records_file).open("rb") as file:
                report_records = pickle.load(file)

            local_report_records_file.unlink()
            
            xml_report = generate_report(report_records, current_report_dir)
            xml_report_file = current_report_dir / "report.xml"
            xml_report.write(str(xml_report_file))
            
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

