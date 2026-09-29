"""Render the CRAP table."""

from .measurement import THRESHOLD, Measurement


class CrapReport:
    """A ranked CRAP table over the measurements."""

    HEADER = f"{'Function':<30} {'File':<38} {'CC':>4} {'Cov%':>10} {'CRAP':>10}"

    def __init__(self, measurements: tuple[Measurement, ...]):
        self._measurements = measurements

    def render(self) -> str:
        rows = sorted(self._measurements, key=Measurement.sort_key)
        lines = ["CRAP Report", "=" * 11, self.HEADER, "-" * len(self.HEADER)]
        lines += [self._row(row) for row in rows]
        lines += ["", f"{self._above()} function(s) above CRAP {THRESHOLD:.0f}"]
        return "\n".join(lines)

    def show(self) -> None:
        print(self.render())

    def _above(self) -> int:
        return sum(1 for row in self._measurements if row.exceeds())

    @staticmethod
    def _row(row: Measurement) -> str:
        function = row.function
        location = f"{function.path}:{function.lineno}"
        return (
            f"{function.name:<30} {location:<38} {function.complexity:>4} "
            f"{row.coverage_text():>10} {row.score_text():>10}"
        )
