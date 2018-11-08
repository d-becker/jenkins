#!/usr/bin/env python3

import argparse

from pathlib import Path

import sys

if __name__ == "__main__":
    # We only import these if this file is run as the main script. As the main script, it is to run on
    # the Oozie server within the dockerised cluster, but we import this on the local machine so that
    # we can get the filename and copy it to the docker container.    
    import example_runner
    import report

def run_normal_example(path: Path) -> int:
    example = example_runner.NormalExample(path)
    cli_options = example_runner.default_cli_options()

    options = (cli_options.get("all", []))
    options.extend(cli_options.get(example.name(), []))
    report_record = example.launch(options, 1, 180)

    if report_record.result == report.Result.SUCCEEDED:
        return 0
    else:
        return 2

def run_fluent_example(example_dir: Path, class_name: str) -> int:
    oozie_version = example_runner.get_oozie_version()

    lib = example_dir.expanduser().resolve().parent / "lib"
    oozie_fluent_job_api_jar = lib / "oozie-fluent-job-api-{}.jar".format(oozie_version)

    example = example_runner.FluentExample(oozie_version, oozie_fluent_job_api_jar, example_dir, class_name)

    cli_options = example_runner.default_cli_options()

    options = (cli_options.get("all", []))
    options.extend(cli_options.get(example.name(), []))

    report_record = example.launch(options, 1, 180)

    if report_record.result == report.Result.SUCCEEDED:
        return 0
    else:
        return 2
    
def build_fluent_example(example_dir: Path, class_name: str, build_dir: Path) -> int:
    oozie_version = example_runner.get_oozie_version()

    lib = example_dir.expanduser().resolve().parent / "lib"
    oozie_fluent_job_api_jar = lib / "oozie-fluent-job-api-{}.jar".format(oozie_version)

    example = example_runner.FluentExample(oozie_version, oozie_fluent_job_api_jar, example_dir, class_name)

    result = example.build_example(str(build_dir))

    if isinstance(result, Path):
        return 0
    else:
        return 2

def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run tests.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-normal")
    group.add_argument("--run-fluent"  )
    group.add_argument("--build-fluent",
                       nargs=2,
                       help="The first argument is the name of the Java class, the second " +
                       "is the directory where the built files should be located.")

    return parser

if __name__ == "__main__":
    EXAMPLE_DIR = Path("~/examples").expanduser()

    args = get_argument_parser().parse_args()

    if args.run_normal:
        path = Path("~/examples/apps").expanduser().resolve() / args.run_normal
        res = run_normal_example(path)
    if args.run_fluent:
        class_name = args.run_fluent
        res = run_fluent_example(EXAMPLE_DIR, class_name)
        
    if args.build_fluent:
        class_name = args.build_fluent[0]
        build_dir_name = args.build_fluent[1]

        build_dir = Path(build_dir_name).expanduser().resolve()
        build_dir.mkdir(exist_ok=True)

        res = build_fluent_example(EXAMPLE_DIR, class_name, build_dir)

    sys.exit(res)

    
