# dry4py

Duplicate-code report for Python projects. Finds repeated regions with jscpd
and prints each pair as two `file:start-end` line ranges. Report-only; exits 0
on a clean or dirty result and 1 only when the scan could not run.

## Files

| File | Holds | Job |
|---|---|---|
| `__init__.py` | public API | re-export the values, ports, and command |
| `errors.py` | `InvalidRegion`, `InvalidDuplicate`, `EmptyScope`, `DetectorUnavailable`, `DetectorError` | name each failure |
| `values.py` | `CodeRegion`, `Duplicate`, `DuplicateReport`, `ScanScope` | frozen state: the request and the result |
| `contracts.py` | `DuplicateDetector`, `ProcessRunner`, `ReportWriter` | the ports the domain defines |
| `process.py` | `SubprocessRunner` | run an external command |
| `parser.py` | `JscpdReportParser` | translate jscpd JSON into domain values |
| `detector.py` | `JscpdDetector` | invoke jscpd, collect its report |
| `writer.py` | `ConsoleReportWriter` | print pairs and the summary |
| `command.py` | `DuplicateReportCommand` | the one use case: detect, then report |
| `cli.py` | `main`, `parse_args` | flags to collaborators (composition root) |
| `__main__.py` | entry point | run the directory as a script |

## Ports

The values never run a subprocess or print. Three ports carry every outside
dependency, all injected in `cli.main`:

| Port | Adapter | Dependency |
|---|---|---|
| `DuplicateDetector` | `JscpdDetector` | jscpd via subprocess |
| `ProcessRunner` | `SubprocessRunner` | the OS process |
| `ReportWriter` | `ConsoleReportWriter` | the text stream |

## Usage

```bash
python3 <pack>/tools/shared/dry4py [--min-lines N] [--min-tokens N] <paths>...
```

Takes one or more files or directories; thresholds are optional.

| Flag | Meaning |
|---|---|
| `--min-lines` | minimum clone size in lines (default: 4) |
| `--min-tokens` | minimum clone size in tokens (default: 50, jscpd's default) |

A clone must meet both thresholds, so a small line count is still gated by the
token floor; lower `--min-tokens` to surface short duplicates.

| Exit | Meaning |
|---|---|
| `0` | scan completed (duplicates may or may not have been found) |
| `1` | detector missing, detector failed, or a path does not exist |
| `2` | no paths given (usage error) |
