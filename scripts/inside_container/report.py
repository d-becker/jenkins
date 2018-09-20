#!/usr/bin/env python3

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
    def __init__(self,
                 name: str,
                 result: Result,
                 oozie_job_id: Optional[str],
                 applications: List[str]) -> None:
        self.name = name
        self.result = result
        self.oozie_job_id = oozie_job_id
        self.applications = applications
