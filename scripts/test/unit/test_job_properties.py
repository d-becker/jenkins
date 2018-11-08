#!/usr/bin/env python3

# pylint: disable=missing-docstring

from pathlib import Path

import tempfile

import unittest

import oozie_testing.inside_container.example_runner

class TestJobProperties(unittest.TestCase):
    def test_job_properties(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tmp_dir = Path(tempdir_name).expanduser().resolve()
            job_properties_file = tmp_dir / "job.properties"

            options = ["option1=A", "option2=B"]
            oozie_version = "5.1.0"

            expected_result = """\
queueName=default
examplesRoot=examples
projectVersion=5.1.0
option1=A
option2=B"""

            oozie_testing.inside_container.example_runner.FluentExampleBase.create_job_properties(
                job_properties_file,
                options,
                oozie_version)

            with job_properties_file.open() as file:
                result = file.read()

            self.assertEqual(expected_result, result)
