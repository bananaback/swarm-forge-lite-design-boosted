"""A function joined with its coverage line hits."""

from dataclasses import dataclass

from .function import Function

THRESHOLD = 10.0
UNMEASURED = "unmeasured"


@dataclass(frozen=True)
class Measurement:
    """A function with its line hits; answers every field the report needs."""

    function: Function
    hits: dict[int, int]

    def exceeds(self) -> bool:
        score = self._score()
        return score is not None and score > THRESHOLD

    def coverage_text(self) -> str:
        fraction = self._fraction()
        return UNMEASURED if fraction is None else f"{fraction * 100:.1f}%"

    def score_text(self) -> str:
        score = self._score()
        return UNMEASURED if score is None else f"{score:.1f}"

    def sort_key(self) -> tuple:
        score = self._score()
        return (score is None, -(score or 0), self.function.path, self.function.lineno)

    def _fraction(self) -> float | None:
        lines = [
            number
            for number in self.hits
            if self.function.lineno <= number <= self.function.endline
        ]
        if not lines:
            return None
        return sum(1 for number in lines if self.hits[number] > 0) / len(lines)

    def _score(self) -> float | None:
        fraction = self._fraction()
        return None if fraction is None else self.function.crap(fraction)
