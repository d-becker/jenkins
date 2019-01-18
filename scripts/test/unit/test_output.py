#!/usr/bin/env python3

# pylint: disable=missing-docstring

from pathlib import Path

import tempfile

from typing import List

import unittest
import xml.etree.ElementTree as ET

# pylint: disable=useless-import-alias
import oozie_testing.inside_container.report as report
# pylint: enable=useless-import-alias

import output

class TestOutput(unittest.TestCase):
    success_oozie_id = "0000003-181015062156203-oozie-oozi-W"
    timeout_oozie_id = "0000001-181015062156203-oozie-oozi-W"
    killed_oozie_id = "0000004-181015062156203-oozie-oozi-W"
    failed_oozie_id = "0000002-181015062156203-oozie-oozi-W"

    failed_application1_id = "application_1539599757230_0001"
    failed_application1_cont_1_stdout = "container_1539599757230_0001_01_000001 stdout"
    failed_application1_cont_1_stderr = "container_1539599757230_0001_01_000001 stderr"
    failed_application1_cont_2_stdout = "container_1539599757230_0001_01_000002 stdout"
    failed_application1_cont_2_stderr = "container_1539599757230_0001_01_000002 stderr"

    failed_application2_id = "application_1539599757230_0002"
    failed_application2_cont_1_stdout = "container_1539599757230_0002_01_000001 stdout"
    failed_application2_cont_1_stderr = "container_1539599757230_0002_01_000001 stderr"

    error_stdout = "Stdout message"
    error_stderr = "Stderr message"

    def test_generate_report(self) -> None:
        generated_report = TestOutput._get_report()

        root = generated_report.getroot()

        self._check_skipped(root)
        self._check_timeout(root)
        self._check_killed(root)
        self._check_failed_test(root)
        self._check_error(root)

    def _check_skipped(self, root: ET.Element) -> None:
        skipped = root.find("testcase[@name='skipped_test']")
        self.assertIsNotNone(skipped)
        assert skipped is not None # Mypy does not recognise unittest assertions.
        self.assertIsNotNone(skipped.find("skipped"))

    def _check_timeout(self, root: ET.Element) -> None:
        timeout = root.find("testcase[@name='timeout_test']")
        self.assertIsNotNone(timeout)
        assert timeout is not None # Mypy does not recognise unittest assertions.
        self.assertIsNotNone(timeout.find("failure[@type='timeout']"))

    def _check_killed(self, root: ET.Element) -> None:
        killed = root.find("testcase[@name='killed_test']")
        self.assertIsNotNone(killed)
        assert killed is not None # Mypy does not recognise unittest assertions.
        self.assertIsNotNone(killed.find("failure[@type='killed']"))

    def _check_failed_test(self, root: ET.Element) -> None:
        failed = root.find("testcase[@name='failed_test']")
        self.assertIsNotNone(failed)
        assert failed is not None # Mypy does not recognise unittest assertions.
        self.assertIsNotNone(failed.find("failure[@type='failed']"))

        failed_stdout = failed.find("system-out")
        self.assertIsNotNone(failed_stdout)
        assert failed_stdout is not None # Mypy does not recognise unittest assertions.

        failed_stdout_text = failed_stdout.text
        self.assertIsNotNone(failed_stdout_text)
        assert failed_stdout_text is not None # Mypy does not recognise unittest assertions.
        self.assertTrue(TestOutput.failed_application1_cont_1_stdout in failed_stdout_text)
        self.assertTrue(TestOutput.failed_application1_cont_2_stdout in failed_stdout_text)
        self.assertTrue(TestOutput.failed_application2_cont_1_stdout in failed_stdout_text)

        failed_stderr = failed.find("system-err")
        self.assertIsNotNone(failed_stderr)
        assert failed_stderr is not None  # Mypy does not recognise unittest assertions.

        failed_stderr_text = failed_stderr.text
        self.assertIsNotNone(failed_stderr_text)
        assert failed_stderr_text is not None # Mypy does not recognise unittest assertions.
        self.assertTrue(TestOutput.failed_application1_cont_1_stderr in failed_stderr_text)
        self.assertTrue(TestOutput.failed_application1_cont_2_stderr in failed_stderr_text)
        self.assertTrue(TestOutput.failed_application2_cont_1_stderr in failed_stderr_text)

    def _check_error(self, root: ET.Element) -> None:
        error = root.find("testcase[@name='error_test']")
        self.assertIsNotNone(error)
        assert error is not None # Mypy does not recognise unittest assertions.
        self.assertIsNotNone(error.find("error[@type='error']"))

        error_stdout = error.find("system-out")
        self.assertIsNotNone(error_stdout)
        assert error_stdout is not None # Mypy does not recognise unittest assertions.

        error_stdout_text = error_stdout.text
        self.assertIsNotNone(error_stdout_text)
        assert error_stdout_text is not None # Mypy does not recognise unittest assertions.
        self.assertTrue(TestOutput.error_stdout in error_stdout_text)

        error_stderr = error.find("system-err")
        self.assertIsNotNone(error_stderr)
        assert error_stderr is not None # Mypy does not recognise unittest assertions.

        error_stderr_text = error_stderr.text
        self.assertIsNotNone(error_stderr_text)
        assert error_stderr_text is not None # Mypy does not recognise unittest assertions.
        self.assertTrue(TestOutput.error_stderr in error_stderr_text)

    @staticmethod
    def _create_report_records() -> List[report.ReportRecord]:
        skipped = report.ReportRecord("skipped_test", report.Result.SKIPPED, None, [], None, None)
        timeout = report.ReportRecord("timeout_test", report.Result.TIMED_OUT,
                                      TestOutput.timeout_oozie_id, [], None, None)
        killed = report.ReportRecord("killed_test", report.Result.KILLED, TestOutput.killed_oozie_id, [], None, None)
        failed = report.ReportRecord("failed_test",
                                     report.Result.FAILED, TestOutput.failed_oozie_id,
                                     [TestOutput.failed_application1_id, TestOutput.failed_application2_id],
                                     None, None)
        error = report.ReportRecord("error_test", report.Result.ERROR, None, [],
                                    TestOutput.error_stdout, TestOutput.error_stderr)
        success = report.ReportRecord("success_example", report.Result.SUCCEEDED,
                                      TestOutput.success_oozie_id, [], None, None)

        return [skipped, timeout, killed, failed, error, success]

    @staticmethod
    def _application_name_to_container_name(application_name: str, container_number: int) -> str:
        return application_name.replace("application", "container") + "_01_" + str(container_number).zfill(6)

    @staticmethod
    def _write_file(file_path: Path, text: str) -> None:
        with file_path.open("w") as file:
            file.write(text)

    @staticmethod
    def _fill_directory_with_logs(log_dir: Path) -> None:
        logs = log_dir.expanduser().resolve() / "nodemanager" / "hadoop-logs"
        logs.mkdir(parents=True, exist_ok=True)

        application1 = logs / TestOutput.failed_application1_id
        application1.mkdir()
        application1_cont1 = (application1
                              / TestOutput._application_name_to_container_name(TestOutput.failed_application1_id, 1))
        application1_cont1.mkdir()
        TestOutput._write_file(application1_cont1 / "stdout", TestOutput.failed_application1_cont_1_stdout)
        TestOutput._write_file(application1_cont1 / "stderr", TestOutput.failed_application1_cont_1_stderr)

        application1_cont2 = (application1
                              / TestOutput._application_name_to_container_name(TestOutput.failed_application1_id, 2))
        application1_cont2.mkdir()
        TestOutput._write_file(application1_cont2 / "stdout", TestOutput.failed_application1_cont_2_stdout)
        TestOutput._write_file(application1_cont2 / "stderr", TestOutput.failed_application1_cont_2_stderr)

        application2 = logs / TestOutput.failed_application2_id
        application2.mkdir()
        application2_cont1 = (application2
                              / TestOutput._application_name_to_container_name(TestOutput.failed_application2_id, 1))
        application2_cont1.mkdir()
        TestOutput._write_file(application2_cont1 / "stdout", TestOutput.failed_application2_cont_1_stdout)
        TestOutput._write_file(application2_cont1 / "stderr", TestOutput.failed_application2_cont_1_stderr)

    @staticmethod
    def _get_report() -> ET.ElementTree:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name)
            TestOutput._fill_directory_with_logs(tempdir)
            report_records = TestOutput._create_report_records()
            generated_report = output.generate_report("Testsuite_name", report_records, tempdir)
            return generated_report
