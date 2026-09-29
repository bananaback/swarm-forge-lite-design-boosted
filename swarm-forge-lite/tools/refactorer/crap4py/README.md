# crap4py

CRAP report for Python projects: `CRAP(fn) = CC^2 * (1 - coverage)^3 + CC`.
Joins radon cyclomatic complexity with coverage.py line coverage, ranks the
functions worst-first, and counts those above CRAP 10. Report-only; exits 0
unless setup fails.

## The Four Actions

1. **Describe a function and its score** — `function.py`, `measurement.py`
2. **Load coverage line hits** — `coverage.py`
3. **Acquire functions and coverage** — `complexity.py`, `providers.py`
4. **Report and orchestrate** — `report.py`, `tool.py`, `cli.py`

## Files

| File | Holds | Job |
|---|---|---|
| `__init__.py` | public API | re-exports `CrapTool`, `Function`, `Coverage`, … |
| `errors.py` | `ToolError` | a dependency (radon, coverage) failed |
| `function.py` | `Function` | name, file, line range, complexity; computes CRAP |
| `measurement.py` | `Measurement`, `THRESHOLD` | a function + its hits; answers report fields |
| `coverage.py` | `Coverage` | parse LCOV; hits for a function's line range |
| `complexity.py` | `ComplexitySource`, `RadonComplexity` | port + adapter over `radon cc -j` |
| `providers.py` | `CoverageProvider`, `PytestCoverage`, `CommandCoverage`, `ExistingCoverage` | port + the three ways to produce an LCOV file |
| `report.py` | `CrapReport` | rank and render the table |
| `tool.py` | `CrapTool` | join complexity with coverage; orchestrate |
| `cli.py` | `main`, `parse_args`, `coverage_provider` | flags → strategy → tool |
| `__main__.py` | entry point | run the directory as a script |

## Ports

The domain (`Function`, `Measurement`, `Coverage`) never runs a subprocess.
Two ports carry every outside dependency, each with its injection point in
`CrapTool(...)`:

| Port | Adapter | Dependency |
|---|---|---|
| `ComplexitySource` | `RadonComplexity` | `radon` via subprocess |
| `CoverageProvider` | `PytestCoverage` / `CommandCoverage` / `ExistingCoverage` | `coverage`, or a caller command, or a prebuilt LCOV |

## Usage

```bash
python3 <pack>/tools/refactorer/crap4py --source-root src --test-path tests
python3 <pack>/tools/refactorer/crap4py --coverage-command "pytest --cov ... {lcov}"
python3 <pack>/tools/refactorer/crap4py --use-existing-coverage --lcov dump/coverage.lcov
python3 <pack>/tools/refactorer/crap4py src/mymodule        # filter by path fragment
```

Without `--source-root`, it scans `wiring`'s `source_roots`. Coverage data and
the LCOV file stay under the configured artifacts root.

| Flag | Meaning |
|---|---|
| `--source-root` | source root to analyze; repeatable |
| `--test-path` | test path for the default coverage run; repeatable |
| `--lcov` | LCOV file to read (default: `<artifacts>/coverage.lcov`) |
| `--use-existing-coverage` | read the LCOV file, do not run coverage |
| `--coverage-command` | command that writes the LCOV; `{lcov}` is its path |
| `filters` | keep only files whose path contains a fragment |
