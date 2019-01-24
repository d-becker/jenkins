#!/usr/bin/env python3

"""
This script is used from within the dockerised cluster during integration testing.
It contains functions that run or build examples.
"""

import argparse

from pathlib import Path

import sys

if __name__ == "__main__":
    # We only import these if this file is run as the main script. As the main script, it is to run on
    # the Oozie server within the dockerised cluster, but we import this on the local machine so that
    # we can get the filename and copy it to the docker container.

    # We suppress the pylint warning because of the special import handling.
    # pylint: disable=import-error
    import example_runner
    import report
    # pylint: enable=import-error

def run_normal_example(path: Path, oozie_url: str) -> int:
    """
    Runs a normal (non-fluent) example.

    Args:
        path: The path to the directory containing the example files.

    Returns:
        Zero if the example ran successfully; a non-zero value otherwise.

    """

    example = example_runner.NormalExample(path, oozie_url)
    cli_options = example_runner.default_cli_options()

    options = (cli_options.get("all", []))
    options.extend(cli_options.get(example.name(), []))
    report_record = example.launch(options, 1, 180)

    # pylint: disable=no-else-return
    if report_record.result == report.Result.SUCCEEDED:
        return 0
    else:
        return 2

def run_fluent_example(example_dir: Path, class_name: str, oozie_url: str) -> int:
    """
    Runs a fluent example.

    Args:
        example_dir: The path to the directory containing the Oozie examples.
        class_name: The name of the java class of the fluent job example.

    Returns:
        Zero if the example ran successfully; a non-zero value otherwise.

    """

    oozie_version = example_runner.get_oozie_version(oozie_url)

    lib = example_dir.expanduser().resolve().parent / "lib"
    oozie_fluent_job_api_jar = lib / "oozie-fluent-job-api-{}.jar".format(oozie_version)

    example = example_runner.FluentExample(oozie_version, oozie_fluent_job_api_jar, example_dir, class_name, oozie_url)

    cli_options = example_runner.default_cli_options()

    options = (cli_options.get("all", []))
    options.extend(cli_options.get(example.name(), []))

    report_record = example.launch(options, 1, 180)

    # pylint: disable=no-else-return
    if report_record.result == report.Result.SUCCEEDED:
        return 0
    else:
        return 2

def build_fluent_example(example_dir: Path, class_name: str, build_dir: Path, oozie_url: str) -> int:
    """
    Builds a fluent example.

    Args:
        example_dir: The path to the directory containing the Oozie examples.
        class_name: The name of the java class of the fluent job example.
        build_dir: The directory in which the build results will be placed.

    Returns:
        Zero if the example was built successfully; a non-zero value otherwise.

    """

    oozie_version = example_runner.get_oozie_version(oozie_url)

    lib = example_dir.expanduser().resolve().parent / "lib"
    oozie_fluent_job_api_jar = lib / "oozie-fluent-job-api-{}.jar".format(oozie_version)

    example = example_runner.FluentExample(oozie_version, oozie_fluent_job_api_jar, example_dir, class_name, oozie_url)

    result = example.build_example(str(build_dir))

    # pylint: disable=no-else-return
    if isinstance(result, Path):
        return 0
    else:
        return 2

def get_argument_parser() -> argparse.ArgumentParser:
    """
    Builds and returns an argument parser for the script entry point.

    Returns:
        An argument parser for the script entry point.

    """

    parser = argparse.ArgumentParser(description="Run tests.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-normal")
    group.add_argument("--run-fluent")
    group.add_argument("--build-fluent",
                       nargs=2,
                       help="The first argument is the name of the Java class, the second " +
                       "is the directory where the built files should be located.")

    return parser

EXAMPLE_DIR: Path = Path("~/examples").expanduser()

def main() -> None:
    """
    The entry point of the script.
    """

    args = get_argument_parser().parse_args()
    oozie_url = "http://localhost:11000/oozie"

    if args.run_normal:
        path = Path("~/examples/apps").expanduser().resolve() / args.run_normal
        res = run_normal_example(path, oozie_url)
    if args.run_fluent:
        class_name = args.run_fluent
        res = run_fluent_example(EXAMPLE_DIR, class_name, oozie_url)

    if args.build_fluent:
        class_name = args.build_fluent[0]
        build_dir_name = args.build_fluent[1]

        build_dir = Path(build_dir_name).expanduser().resolve()
        build_dir.mkdir(exist_ok=True)

        res = build_fluent_example(EXAMPLE_DIR, class_name, build_dir, oozie_url)

    sys.exit(res)

if __name__ == "__main__":
    main()
