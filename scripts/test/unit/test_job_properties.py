from pathlib import Path

import tempfile

from typing import Dict, List, Tuple

import unittest
import xml.etree.ElementTree as ET

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
            result = job_properties_file.open().read()
            self.assertEqual(expected_result, result)
