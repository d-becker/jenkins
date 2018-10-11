#!/usr/bin/env python3

"""
This module provides functions to detect and run the Oozie examples.
It should be run on the Oozie server, with the Oozie examples uploaded to hdfs.

"""
from abc import ABCMeta, abstractmethod

import argparse
import io
import itertools
import json
import logging

from pathlib import Path

import pickle
import re
import subprocess
import sys
import tempfile
import time
import traceback

from typing import Dict, Iterable, List, Optional, Tuple, Union

import urllib.request

# pylint: disable=useless-import-alias

if __name__ == "__main__":
    # We are running the script inside the container.
    import report
else:
    import oozie_testing.inside_container.report as report

# pylint: enable=useless-import-alias

def _launch_oozie_job_by_command(command: List[str], example_name: str) -> Union[str, int]:
    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return_code = process_result.returncode
    if return_code != 0:
        return return_code

    output = process_result.stdout.decode()

    match = re.search("job:(.*)", output)
    if match is None:
        raise ValueError("The job id could not be determined for example {}".format(example_name))

    job_id = match.group(1).strip()

    return job_id

class Example(metaclass=ABCMeta):
    """
    A base class for Oozie examples.
    """

    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the Oozie example. This is not necessarily the same
        as the name of the Oozie job resulting from running the example.

        Returns:
            The name of the Oozie example.

        """

        pass

    @abstractmethod
    def launch(self, cli_options: List[str]) -> Union[str, int]:
        """
        Launches the Oozie example.

        Args:
            cli_options: The CLI options to use when launching the example.

        Returns:
            The job_id of the launched Oozie example if launching it was successful;
            otherwise the error code of the launch subprocess.

        """
        pass

class NormalExample(Example):
    """
    A class representing a normal (non-fluent job) Oozie example.
    """

    def __init__(self, path: Path) -> None:
        self._name = path.name
        self._path = path

    def name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
        """
        Returns the path that the Oozie example files are located in.

        Returns:
            The path that the Oozie example files are located in.

        """

        return self._path

    def launch(self, cli_options: List[str]) -> Union[str, int]:
        command = ["/opt/oozie/bin/oozie",
                   "job",
                   "-config",
                   str(self.path / "job.properties"),
                   "-run"]
        command.extend(map(lambda option: "-D" + option, cli_options))

        logging.info("Running command: %s.", " ".join(command))

        return _launch_oozie_job_by_command(command, self.name())

class FluentExample(Example):
    """
    A class representing a fluent job Oozie example.
    """

    def __init__(self,
                 oozie_version: str,
                 oozie_fluent_job_api_jar: Path,
                 example_dir: Path,
                 class_name: str) -> None:
        self._oozie_version = oozie_version
        self._oozie_fluent_job_api_jar = oozie_fluent_job_api_jar
        self._example_dir = example_dir
        self._class_name = class_name

    def name(self) -> str:
        return "Fluent_{}".format(self._class_name)

    @property
    def class_name(self) -> str:
        """
        Returns the name of the Oozie fluent job example main class.

        Returns:
            The name of the Oozie fluent job example main class.

        """

        return self._class_name

    def launch(self, cli_options: List[str]) -> Union[str, int]:
        with tempfile.TemporaryDirectory() as tmp:
            (jar_path, job_properties_file) = self._build_example(tmp, cli_options)
            cmd_run = ["/opt/oozie/bin/oozie", "job", "-runjar", str(jar_path), "-config", str(job_properties_file)]

            return _launch_oozie_job_by_command(cmd_run, self.name())

    def _build_example(self, tmp: str, cli_options: List[str]) -> Tuple[Path, Path]:
        packages = ["org", "apache", "oozie", "example", "fluentjob"]
        java_file_name = self._class_name + ".java"
        path_to_source_file = self._example_dir / "src" / "/".join(packages) / java_file_name
        cmd_compile = ["javac",
                       "-classpath", str(self._oozie_fluent_job_api_jar),
                       str(path_to_source_file),
                       "-d", tmp]
        logging.info("Building fluent job example with command: %s", cmd_compile)
        subprocess.run(cmd_compile, check=True)

        tmp_path = Path(tmp)
        jar_path = tmp_path / "fluent_{}.jar".format(self.class_name)
        class_file_name = self._class_name + ".class"
        path_to_class_file = Path("/".join(packages)) / class_file_name
        cmd_jar = ["jar", "cfe", str(jar_path), "{}.{}".format(".".join(packages), self._class_name),
                   "-C", tmp,
                   str(path_to_class_file)]

        logging.info("Creating fluent job jar file with command: %s", cmd_jar)
        subprocess.run(cmd_jar, check=True)

        job_properties_file = tmp_path / "job.properties"
        self._create_job_properties(job_properties_file, cli_options, self._oozie_version)

        return (jar_path, job_properties_file)

    @staticmethod
    def _create_job_properties(job_properties_file: Path, cli_options: List[str], oozie_version: str) -> None:
        with job_properties_file.open("w") as file:
            options = ["queueName=default", "examplesRoot=examples", "projectVersion={}".format(oozie_version)]
            options.extend(cli_options)
            file.write("\n".join(options))

def get_all_normal_examples(example_apps_dir: Path) -> Iterable[NormalExample]:
    """
    Returns the normal (non-fluent job) examples contained in `example_apps_dir`.

     Args:
        example_apps_dirs: The `apps` subdirectory in the root directory of the Oozie examples.

     Returns:
        An iterable over the Oozie normal (non-fluent) examples.

    """

    return map(NormalExample, get_all_example_dirs(example_apps_dir))

def _get_oozie_version() -> str:
    url = "http://localhost:11000/oozie/v2/admin/build-version"
    response: str
    with urllib.request.urlopen(url) as connection:
        response = connection.read().decode()

    json_dict = json.loads(response)
    return json_dict["buildVersion"]

def get_all_fluent_examples(example_dir: Path) -> Iterable[FluentExample]:
    """
    Returns the fluent job examples contained in `example_dir`.

     Args:
        example_dirs: The root directory of the Oozie examples.

     Returns:
        An iterable over the Oozie fluent job examples.

    """

    oozie_version = _get_oozie_version()
    lib = example_dir.expanduser().resolve().parent / "lib"
    oozie_fluent_job_api_jar = lib / "oozie-fluent-job-api-{}.jar".format(oozie_version)

    if not oozie_fluent_job_api_jar.exists():
        raise FileNotFoundError("Library jar file does not exist: {}.".format(oozie_fluent_job_api_jar))

    java_files: Iterable[Path] = (example_dir / "src" / "org" / "apache" / "oozie" / "example" / "fluentjob").iterdir()

    into_fluent_example = lambda java_file: FluentExample(oozie_version,
                                                          oozie_fluent_job_api_jar,
                                                          example_dir,
                                                          java_file.name.strip(".java"))
    return map(into_fluent_example, java_files)

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

def _get_example_result(example: Example,
                        whitelist: Optional[List[str]],
                        blacklist: List[str],
                        cli_options: Dict[str, List[str]],
                        poll_time: int,
                        timeout: int) -> report.ReportRecord:
    if example.name() in blacklist:
        logging.info("Skipping blacklisted example: %s.", example.name())
        return report.ReportRecord(example.name(), report.Result.SKIPPED, None, [])

    if whitelist is not None and example.name() not in whitelist:
        logging.info("Skipping non-whitelisted example: %s.", example.name())
        return report.ReportRecord(example.name(), report.Result.SKIPPED, None, [])

    logging.info("Running example %s.", example.name())

    options = (cli_options.get("all", []))
    options.extend(cli_options.get(example.name(), []))
    launch_result = example.launch(options)

    if isinstance(launch_result, int):
        logging.info("Starting example %s failed with exit code %s.", example.name(), launch_result)
        return report.ReportRecord(example.name(), report.Result.ERROR, None, [])

    logging.info("Oozie job id: %s.", launch_result)

    final_status = wait_for_job_to_finish(launch_result, poll_time, timeout)
    applications = get_yarn_applications_of_job(launch_result)

    return report.ReportRecord(example.name(), final_status, launch_result, applications)

def run_examples(examples: Iterable[Example],
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

    return list(map(
        lambda example: _get_example_result(example, whitelist, blacklist, cli_options, poll_time, timeout),
        examples))

def _get_application_name_from_external_id(external_id: str) -> str:
    if external_id.startswith("application"):
        return external_id

    index = external_id.find("_")
    return "application{}".format(external_id[index:])

def get_yarn_applications_of_job(job_id: str) -> List[str]:
    """
    Retrieves the id's of the yarn applications of the provided Oozie job.

    Args:
        job_id: The id of the Oozie job.

    Returns:
        A list with the id's of the yarn applications of the provided Oozie job.

    """

    url = "http://localhost:11000/oozie/v1/job/{}?show=info".format(job_id)
    response: str
    with urllib.request.urlopen(url) as connection:
        response = connection.read().decode()

    json_dict = json.loads(response)
    actions = json_dict.get("actions", [])

    yarn_actions = filter(lambda action: action["externalId"] != "-", actions)
    return list(map(lambda yarn_action: _get_application_name_from_external_id(yarn_action["externalId"]),
                    yarn_actions))

def default_cli_options() -> Dict[str, List[str]]:
    """
    Returns a dictionary with the default CLI options for the examples.
    """

    cli_options = dict()
    cli_options["all"] = ["nameNode=hdfs://namenode:9000",
                          "jobTracker=resourcemanager:8032",
                          "resourceManager=resourcemanager:8032"]
    cli_options["hive2"] = ["jdbcURL=jdbc:hive2://hiveserver2:10000/default"]

    return cli_options

BLACKLIST: List[str] = ["hcatalog"]
EXAMPLE_DIR = Path("~/examples").expanduser()

def get_argument_parser() -> argparse.ArgumentParser:
    """
    Builds and returns an argument parser for the script entry point.

    Returns:
        An argument parser for the script entry point.

    """

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

    try:
        args = get_argument_parser().parse_args()

        logfile = args.logfile if args.logfile is not None else "example_runner.log"
        logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(format=logging_format,
                            level=logging.INFO,
                            filename=logfile)

        examples = get_all_normal_examples(EXAMPLE_DIR / "apps")
        fluent_examples = get_all_fluent_examples(EXAMPLE_DIR)
        report_records = run_examples(itertools.chain(examples, fluent_examples),
                                      args.whitelist,
                                      args.blacklist if args.blacklist is not None else BLACKLIST,
                                      default_cli_options(),
                                      1,
                                      120)

        report_records_file = args.report_records if args.report_records is not None else "report_records.pickle"
        with open(report_records_file, "wb") as file:
            pickle.dump(report_records, file)

    # We catch all exceptions to be able to log them.
    # pylint: disable=bare-except
    except:
        err_stream = io.StringIO()
        traceback.print_exc(file=err_stream)
        logging.error(err_stream.getvalue())
        sys.exit(2)

    if not all(map(lambda r: r.result == report.Result.SUCCEEDED or r.result == report.Result.SKIPPED, report_records)):
        sys.exit(1)

if __name__ == "__main__":
    main()
