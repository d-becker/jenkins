#!/usr/bin/env python3

"""
This module provides functions to detect and run the Oozie examples. It should be run on the Oozie server, with the
Oozie examples uploaded to hdfs.

"""

import argparse
import json
import logging

from pathlib import Path

import pickle
import re
import subprocess
import sys
import time

from typing import Dict, Iterable, List, Optional, Tuple, Union

import urllib.request
import xml.etree.ElementTree as ET

import report

def get_all_example_dirs(example_dir: Path) -> Iterable[Path]:
    """
    Returns the directories within `example_dir` that contain Oozie examples.

    Args:
        example_dirs: The root directory of the Oozie examples.

    Returns:
        An iterable over the Oozie example directories.

    """

    condition = lambda path: path.is_dir() and (path / "job.properties").exists()
    return filter(condition, example_dir.iterdir())

def get_workflow_example_dirs(example_dir: Path) -> Iterable[Path]:
    """
    Returns the directories within `example_dir` that contain Oozie
    workflow examples, filtering out coordinator and bundle examples.

    Args:
        example_dirs: The root directory of the Oozie examples.

    Returns:
        An iterable over the Oozie workflow example directories.

    """
    condition = lambda path: (not (path / "coordinator.xml").exists()
                              and not (path / "bundle.xml").exists())

    return filter(condition, get_all_example_dirs(example_dir))

def query_job(job_id: str) -> str:
    """
    Queries and returns the status of an Oozie job.

    Args:
        job_id: The job_id of the Oozie job.

    Returns:
        The status of the Oozie job with the given job_id.

    """

    query_command = ["/opt/oozie/bin/oozie",
                     "job",
                     "-info",
                     job_id]

    query_process_result = subprocess.run(query_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    query_output = query_process_result.stdout.decode()

    match = re.search("Status.*:(.*)\n", query_output)
    if match is None:
        raise ValueError("The status could not be determined for job id {}".format(job_id))

    status = match.group(1).strip()

    return status

def kill_job(job_id: str) -> int:
    """
    Kills an Oozie job.

    Args:
        job_id: The job_id of the Oozie job.

    Returns:
        The exit status of the subprocess that kills the Oozie job.

    """

    kill_command = ["/opt/oozie/bin/oozie",
                    "job",
                    "-kill",
                    job_id]

    process_result = subprocess.run(kill_command, stderr=subprocess.PIPE)
    return process_result.returncode

def wait_for_job_to_finish(job_id: str, poll_time: int = 1, timeout: int = 60) -> report.Result:
    """
    Waits for an Oozie job to finish, polling it regularly with a period of `poll_time`.
    If the job does not finish before the given timeout is elapsed, it is killed.

    Args:
        job_id : The job_id of the Oozie job.
        poll_time: The interval at which the job will be polled, in seconds.
        timeout: The timeout value after which the job is killed, in seconds.

    Returns:
        The job result.

    """

    start_time = time.time()

    status = query_job(job_id)
    while status == "RUNNING" and (time.time() - start_time) < timeout:
        time.sleep(poll_time)
        status = query_job(job_id)

    # pylint: disable=no-else-return
    if status == "RUNNING":
        logging.info("Timed out waiting for example %s to finish, killing it.", EXAMPLE_DIR.name)
        kill_job(job_id)
        return report.Result.TIMED_OUT
    else:
        logging.info("Status: %s.", status)
        return report.Result[status]

def launch_example(example_dir: Path, cli_options: List[str]) -> Union[str, int]:
    """
    Launches the Oozie example contained in `example_dir`.

    Args:
        example_dir: The directory containing the Oozie example.
        cli_options: The CLI options to use when launching the example.

    Returns:
        The job_id of the launched Oozie example if launching it was successful;
        otherwise the error code of the launch subprocess.

    """

    command = ["/opt/oozie/bin/oozie",
               "job",
               "-config",
               str(example_dir / "job.properties"),
               "-run"]
    command.extend(cli_options)

    logging.info("Running command: %s.", " ".join(command))
    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return_code = process_result.returncode
    if return_code != 0:
        return return_code

    output = process_result.stdout.decode()

    match = re.search("job:(.*)", output)
    if match is None:
        raise ValueError("The job id could not be determined for example {}".format(example_dir.name))

    job_id = match.group(1).strip()

    return job_id

def run_examples(examples: Iterable[Path],
                 whitelist: Optional[List[str]],
                 blacklist: List[str],
                 cli_options: Dict[str, List[str]],
                 poll_time: int = 1,
                 timeout: int = 60) -> List[report.ReportRecord]:
    """
    Runs the Oozie examples contained in the directories in `examples`. Returns a dictionary of the results.

    Args:
        examples: An iterable of paths to directories containing individual Oozie examples.
        blacklist: A list with directory names of the examples that should not be run.
        cli_options: A dictionary in which the keys are the names of the example directories and the values are lists of
            command line options to use when launching the examples. If the dictionary contains the key 'all', the value
            will be applied to all examples. If an example directory name is not among the keys, no additional CLI
            options will be added.
        poll_time: The interval at which the jobs will be polled, in seconds.
        timeout: The timeout value after which the jobs are killed, in seconds.

    Returns:
        A list of ReportRecord objects holding the results of running the examples.

    """

    results: List[report.ReportRecord] = []

    for example_dir in examples:
        report_record: report.ReportRecord
        if example_dir.name in blacklist:
            logging.info("Skipping blacklisted example: %s.", example_dir.name)
            report_record = report.ReportRecord(example_dir.name, report.Result.SKIPPED, None, [])
        elif whitelist is not None and example_dir.name not in whitelist:
           logging.info("Skipping non-whitelisted example: %s.", example_dir.name)
           report_record = report.ReportRecord(example_dir.name, report.Result.SKIPPED, None, [])
        else:
            logging.info("Running example %s.", example_dir.name)

            options = (cli_options.get("all", []))
            options.extend(cli_options.get(example_dir.name, []))
            launch_result = launch_example(example_dir, options)

            if isinstance(launch_result, int):
                logging.info("Starting example %s failed with exit code %s.", example_dir.name, launch_result)
                report_record = report.ReportRecord(example_dir.name, report.Result.ERROR, None, [])
            else:
                logging.info("Oozie job id: %s.", launch_result)

                final_status = wait_for_job_to_finish(launch_result, poll_time, timeout)
                applications = get_yarn_applications_of_job(launch_result)
                report_record = report.ReportRecord(example_dir.name, final_status, launch_result, applications)
        results.append(report_record)

    return results

def _get_application_name_from_external_id(external_id: str) -> str:
    if external_id.startswith("application"):
        return external_id
    else:
        index = external_id.find("_")
        return "application{}".format(external_id[index:])

def get_yarn_applications_of_job(job_id: str) -> List[str]:
    url = "http://localhost:11000/oozie/v1/job/{}?show=info".format(job_id)
    response: str
    with urllib.request.urlopen(url) as connection:
        response = connection.read().decode()

    json_dict = json.loads(response)
    actions = json_dict["actions"]

    yarn_actions = filter(lambda action: action["externalId"] != "-", actions)
    return list(map(lambda yarn_action: _get_application_name_from_external_id(yarn_action["externalId"]),
                    yarn_actions))

def default_cli_options() -> Dict[str, List[str]]:
    """
    Returns a dictionary with the default CLI options for the examples.
    """

    cli_options = dict()
    cli_options["all"] = ["-DnameNode=hdfs://namenode:9000",
                          "-DjobTracker=resourcemanager:8032",
                          "-DresourceManager=resourcemanager:8032"]
    cli_options["hive2"] = ["-DjdbcURL=jdbc:hive2://hiveserver2:10000/default"]

    return cli_options

BLACKLIST: List[str] = ["hcatalog"]
EXAMPLE_DIR = Path("~/examples/apps").expanduser()

def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Oozie examples.\n" +
                                     "If no whitelist is provided, the examples are discovered automatically.\n" +
                                     "If both a whitelist and a blacklist are specified, only those examples " +
                                     "will be run that are on the whitelist but not on the blacklist.")
    parser.add_argument("-w", "--whitelist",
                        metavar="WHITELIST", nargs="*",
                        help="Only run the whitelisted examples. Otherwise, all detected examples are run.")
    parser.add_argument("-b", "--blacklist",
                        metavar="BLACKLIST", nargs="*",
                        help="Do not run the blacklisted examples.")
    parser.add_argument("-l", "--logfile", help="The logfile.")
    parser.add_argument("-r", "--report_records",
                        help="The file to which the report records will be written, as a pickled Python object.")

    return parser

def main() -> None:
    """
    The entry point of the script.
    """

    parser = get_argument_parser()
    args = parser.parse_args()

    logfile = args.logfile if args.logfile is not None else "example_runner.log"
    LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=LOGGING_FORMAT,
                        level=logging.INFO,
                        filename=logfile)
    
    example_dirs = get_all_example_dirs(EXAMPLE_DIR)
    report_records = run_examples(example_dirs,
                                  args.whitelist,
                                  args.blacklist if args.blacklist is not None else BLACKLIST,
                                  default_cli_options(),
                                  1,
                                  120)

    report_and_log_dir = Path("report_and_logs")

    report_records_file = args.report_records if args.report_records is not None else "report_records.pickle"
    with open(report_records_file, "wb") as file:
        pickle.dump(report_records, file)

    if not all(map(lambda r: r.result == report.Result.SUCCEEDED or r.result == report.Result.SKIPPED, report_records)):
        sys.exit(1)

if __name__ == "__main__":
    main()
