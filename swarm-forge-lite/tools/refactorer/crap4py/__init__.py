"""crap4py -- CRAP metric for Python projects.

Report-only: `CRAP(fn) = CC^2 * (1 - coverage)^3 + CC`, joining radon
cyclomatic complexity with coverage.py line coverage.

The four actions:

1. Describe a function and its score -- `function.py`, `measurement.py`
2. Load coverage line hits -- `coverage.py`
3. Acquire functions and coverage -- `complexity.py`, `providers.py`
4. Report and orchestrate -- `report.py`, `tool.py`, `cli.py`
"""

from .complexity import ComplexitySource, RadonComplexity
from .coverage import Coverage
from .errors import ToolError
from .function import Function
from .measurement import THRESHOLD, Measurement
from .providers import (
    CommandCoverage,
    CoverageProvider,
    ExistingCoverage,
    PytestCoverage,
)
from .report import CrapReport
from .tool import CrapTool

__all__ = [
    "THRESHOLD",
    "CommandCoverage",
    "ComplexitySource",
    "Coverage",
    "CoverageProvider",
    "CrapReport",
    "CrapTool",
    "ExistingCoverage",
    "Function",
    "Measurement",
    "PytestCoverage",
    "RadonComplexity",
    "ToolError",
]
