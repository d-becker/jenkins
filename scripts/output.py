#!/usr/bin/env python3

"""
This module provides functionality for generating junit style reports from the test results.
"""

import io

from pathlib import Path
from typing import Dict, List, Tuple

import xml.etree.ElementTree as ET

# pylint: disable=useless-import-alias

import oozie_testing.inside_container.report as report

# pylint: enable=useless-import-alias

def get_logs_for_yarn_application(application_id: str, report_and_log_dir: Path) -> Dict[str, Tuple[str, str]]:
    """
    Returns the logs for the given yarn application. The returned object is a dict, where the keys are the names of the
    containers corresponding to the yarn application and the values are tuples the first elements of which are the
    stdout and the second elements are the stderr outputs of their respective containers.

    Args:
        application_id: The id of the yarn application.
        report_and_log_dir: The directory on the local file system where the yarn logs are located.

    Returns:
        A dictionary with the results. For details, see above.

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
    Returns a pair of strings, the first element of which is the aggregated stdout output of all containers
    and applications corresponding to the given Oozie job, the second is the stderr output.

    Args:
        record: The record containing information about the Oozie job.
        report_and_log_dir: The directory on the local file system where the yarn logs are located.

    Returns:
        A pair of strings, the first element of which is the aggregated stdout output of all containers
        and applications corresponding to the given Oozie job, the second is the stderr output.

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

def generate_report(report_records: List[report.ReportRecord],
                    report_and_log_dir: Path) -> ET.ElementTree:
    """
    Generates a junit style xml from the test results.

    Args:
        report_records: A list of `ReportRecord` objects describing the results of the tests.
        report_and_log_dir: The directory on the local file system where the yarn logs are located.

    Returns:
        An `ElementTree` object representing the xml document.

    """

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
            assert result == report.Result.SUCCEEDED

        # Aggregate the Yarn logs of the containers and add them to system-out and system-err elements.
        (yarn_stdout, yarn_stderr) = printable_logs_for_oozie_job(record, report_and_log_dir)
        stdout_element = ET.SubElement(testcase, "system-out")
        stdout_yarn_part = "\n\nYarn stdout:\n\n" + yarn_stdout
        stdout_element.text = record.stdout + stdout_yarn_part if record.stdout is not None else stdout_yarn_part

        stderr_element = ET.SubElement(testcase, "system-err")
        stderr_yarn_part = "\n\nYarn stderr:\n\n" + yarn_stderr
        stderr_element.text = record.stderr + stderr_yarn_part if record.stderr is not None else stderr_yarn_part

        testsuite.append(testcase)

    return ET.ElementTree(testsuite)
