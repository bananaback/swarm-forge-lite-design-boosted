"""Adapter that translates the detector's raw JSON into domain values."""

import json
from pathlib import Path

from .errors import DetectorError
from .values import CodeRegion, Duplicate


class JscpdReportParser:
    """Reads a jscpd JSON report and returns the duplicate pairs."""

    def parse(self, raw: str) -> tuple:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise DetectorError("report is not valid JSON") from error
        clones = data.get("duplicates") if isinstance(data, dict) else None
        if clones is None:
            raise DetectorError("report has no duplicate list")
        return tuple(self._to_duplicate(clone) for clone in clones)

    def _to_duplicate(self, clone):
        try:
            return Duplicate(
                self._to_region(clone["firstFile"]),
                self._to_region(clone["secondFile"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DetectorError("malformed clone entry: " + repr(error)) from error

    def _to_region(self, raw_file):
        return CodeRegion(
            Path(raw_file["name"]),
            int(raw_file["start"]),
            int(raw_file["end"]),
        )
