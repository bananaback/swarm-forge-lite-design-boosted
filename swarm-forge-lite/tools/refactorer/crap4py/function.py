"""A measured function and its CRAP score."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Function:
    """One function or method reported by the complexity source."""

    name: str
    path: str
    lineno: int
    endline: int
    complexity: int

    def __post_init__(self):
        if not self.name or self.endline < self.lineno or self.complexity < 1:
            raise ValueError(f"invalid function: {self!r}")

    def crap(self, covered: float) -> float:
        """The CRAP score for a coverage fraction in 0..1."""
        return self.complexity**2 * (1 - covered) ** 3 + self.complexity
