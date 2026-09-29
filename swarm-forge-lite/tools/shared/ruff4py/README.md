# ruff4py

Python code-quality check for the pack. A thin wrapper over `ruff check` that
pins the cache under the wiring artifacts root (no `.ruff_cache` in the project
tree), defaults the config to the pack's `ruff.toml`, and passes every other
argument through to ruff unchanged. Report-only: it returns ruff's own exit
status and never rewrites a clean result.

## Files

| File | Holds | Job |
|---|---|---|
| `__init__.py` | public API | re-export the values, ports, and adapters |
| `errors.py` | `InvalidUsage`, `InvalidConfiguration`, `ToolUnavailable` | name each failure |
| `values.py` | `CheckArguments`, `CacheDirectory`, `RuffConfig`, `RuffInvocation`, `CheckRequest` | frozen state: the request and the invocation |
| `contracts.py` | `CodeChecker`, `ToolLocator`, `UsageWriter` | the ports the wrapper defines |
| `locator.py` | `PathToolLocator` | find the ruff executable |
| `process.py` | `SubprocessChecker` | run the invocation |
| `usage.py` | `ConsoleUsage` | print the usage text |
| `cli.py` | `main`, `parse_args` | assemble collaborators (composition root) |
| `__main__.py` | entry point | run the directory as a script |

## Ports

The values never spawn a process, touch PATH, or print. Three ports carry every
outside dependency, all injected in `cli.main`:

| Port | Adapter | Dependency |
|---|---|---|
| `CodeChecker` | `SubprocessChecker` | the ruff process |
| `ToolLocator` | `PathToolLocator` | PATH / the filesystem |
| `UsageWriter` | `ConsoleUsage` | the text stream |

## Usage

```bash
python3 <pack>/tools/shared/ruff4py [ruff check arguments...]
```

`check` is supplied automatically; pass only paths and flags. If `--cache-dir`
or `--config` is absent, the wrapper injects the artifacts-root cache and the
pack config; supply either to override that default. `RUFF4PY_CONFIG` overrides
the config file.

| Exit | Meaning |
|---|---|
| `0` | ruff found no issues (or printed help) |
| nonzero | ruff's own status: issues found |
| `2` | usage error, bad config, or ruff not available |

## Design Notes

The layout applies the four-phase boundary pass:

- **Discovery** — no noun has identity; every noun is a frozen value object.
  `CheckRequest` answers whether it must inject a cache and config, so no caller
  branches on its state.
- **Structure** — one job per file. Nothing subclasses: variation enters through
  the ports. The one volatile boundary, how the linter is invoked, sits behind
  `CodeChecker` with its injection point in `cli.main`; no extra Strategy is
  manufactured.
- **Boundaries** — the executable (`ToolLocator`) and the process
  (`CodeChecker`) are Protocols before any concrete adapter. Lookups raise a
  named error; no method returns `None` to mean "absent".
- **Execution** — `CacheDirectory.prepare` is the command (returns `None`);
  `CheckRequest.invocation` and `CodeChecker.check` are queries. `cli.main`
  sequences the command and the query and returns the process status.
