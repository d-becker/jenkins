#!/usr/bin/env python3

"""
This module provides a class to store the results of and additional information about an Oozie job that was run.
"""

from enum import Enum, auto, unique
from typing import List, Optional

@unique
class Result(Enum):
    """
    An enum to store job results.
    """

    SUCCEEDED = auto()
    SKIPPED = auto()
    TIMED_OUT = auto()
    KILLED = auto()
    FAILED = auto()
    ERROR = auto()

class ReportRecord:
    """
    A class that stores the results of and additional information about an Oozie job that was run.
    """

    def __init__(self,
                 name: str,
                 result: Result,
                 oozie_job_id: Optional[str],
                 applications: List[str],
                 stdout: Optional[str] = None,
                 stderr: Optional[str] = None) -> None:
        """
        Creates `ReportRecord` object.

        Args:
            name: The name of the Oozie job.
            result: The result of the Oozie job.
            oozie_job_id: The id of the Oozie job.
            applications: The id's of the yarn applications of the Oozie job.
            stdout: Optionally, the stdout of the run/validation process.
            stderr: Optionally, the stderr of the run/validation process.

        """

        self.name = name
        self.result = result
        self.oozie_job_id = oozie_job_id
        self.applications = applications
        self.stdout = stdout
        self.stderr = stderr
