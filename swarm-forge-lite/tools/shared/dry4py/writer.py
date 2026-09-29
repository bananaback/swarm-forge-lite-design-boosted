"""Adapter that renders a duplicate report to a text stream."""

from .values import DuplicateReport


class ConsoleReportWriter:
    """Prints a report as one pair of file and line ranges per duplicate."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, report: DuplicateReport) -> None:
        if report.is_empty():
            print("No duplicate candidates found.", file=self._stream)
            return
        for duplicate in report.duplicates:
            self._write_duplicate(duplicate)
        print("Found " + str(report.count()) + " duplicate candidate(s).", file=self._stream)

    def _write_duplicate(self, duplicate):
        first = duplicate.first
        second = duplicate.second
        print(_position(first), file=self._stream)
        print(_position(second), file=self._stream)
        print(file=self._stream)


def _position(region):
    return str(region.path) + ":" + str(region.start) + "-" + str(region.end)
