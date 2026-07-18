"""
validation_result.py — M17 Validation Result types

Lightweight result objects for the ValidationEngine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ValidationStatus(str, Enum):
    """Outcome of a single validation check or a full validation run."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"  # Soft failure — object is accepted but flagged


@dataclass
class CheckResult:
    """
    Outcome of one individual validation check.

    Attributes
    ----------
    check_name : str
        Human-readable name of the check (e.g. ``"schema_validation"``).
    status : ValidationStatus
        PASS, FAIL or WARN.
    message : str
        Descriptive outcome message.  Empty for PASS.
    """

    check_name: str
    status: ValidationStatus
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status == ValidationStatus.FAIL


@dataclass
class ValidationReport:
    """
    Aggregated result of running all validation checks on one object.

    Attributes
    ----------
    uuid : str
        UUID of the validated object.
    series_id : str
        Series ID (best-effort; may be empty for non-API objects).
    source_type : str
        ``API``, ``HTML``, ``PDF``, ``RSS``, or ``ARCHIVE``.
    checks : list[CheckResult]
        Individual check results, in execution order.
    overall_status : ValidationStatus
        FAIL if any check FAILED, else WARN if any check WARNED,
        else PASS.
    """

    uuid: str
    series_id: str
    source_type: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def overall_status(self) -> ValidationStatus:
        if any(c.failed for c in self.checks):
            return ValidationStatus.FAIL
        if any(c.status == ValidationStatus.WARN for c in self.checks):
            return ValidationStatus.WARN
        return ValidationStatus.PASS

    @property
    def passed(self) -> bool:
        return self.overall_status == ValidationStatus.PASS

    @property
    def failed(self) -> bool:
        return self.overall_status == ValidationStatus.FAIL

    @property
    def failures(self) -> List[CheckResult]:
        """Return only the FAILed checks."""
        return [c for c in self.checks if c.failed]

    @property
    def warnings(self) -> List[CheckResult]:
        """Return only the WARNed checks."""
        return [c for c in self.checks if c.status == ValidationStatus.WARN]

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "uuid": self.uuid,
            "series_id": self.series_id,
            "source_type": self.source_type,
            "overall_status": self.overall_status.value,
            "checks": [
                {
                    "check_name": c.check_name,
                    "status": c.status.value,
                    "message": c.message,
                }
                for c in self.checks
            ],
        }
