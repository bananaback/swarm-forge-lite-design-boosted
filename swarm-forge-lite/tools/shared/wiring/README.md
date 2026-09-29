# wiring

Resolve harness paths from `harness.json`, so one pack points at either the
project under work or itself.

## The Four Actions

1. **Find the config** — `locator.py`
2. **Read it** — `config.py`
3. **Resolve every path against the config's directory** — `resolver.py`
4. **Hand the resolved paths to the tools** — `loader.py`, `wiring.py`

## Files

| File | Holds | Job |
|---|---|---|
| `__init__.py` | public API | re-exports `load`, `Wiring`, `WiringError`, … |
| `errors.py` | `WiringError` | missing / unreadable / malformed config |
| `pack.py` | `Pack`, `PACK_ROOT`, `resolve_pack_root` | the pack and where its own config lives |
| `config.py` | `ConfigFile`, `parse_config` | read + validate the JSON at construction |
| `resolver.py` | `PathResolver` | raw values → absolute paths |
| `locator.py` | `ConfigLocator`, `PackConfigLocator` | choose the config file |
| `wiring.py` | `Wiring` | the resolved path set (value object) |
| `loader.py` | `HarnessConfig`, `load` | schema → `Wiring` |

The filesystem is read only in `ConfigFile`; everything else is pure.

## Config

Every path is relative to the config's own directory.

| Field | Default | Meaning |
|---|---|---|
| `workspace_root` | `..` | the project under work |
| `state_root` | `.swarmforge` | durable state |
| `artifacts_root` | `dump` | reports and caches |
| `hot_tests` | `hot_tests` | generated tests |
| `persistent_tests` | `[]` | authored roots: `{root, kind}` |
| `source_roots` | `["src"]` | trees the quality tools scan |
| `features` | none | the authored Gherkin root |
| `specs` | none | the requirements workplace: where the requirements document for each feature is authored and updated |

## Usage

```python
import wiring

resolved = wiring.load()                          # the pack's own harness.json
resolved = wiring.load(config="other.json")       # or an explicit file
resolved.workspace_root, resolved.artifacts_root  # resolved Paths
resolved.as_dict()                                # JSON-ready dict
```

`SWARM_CONFIG` overrides the file when no explicit path is given. `SWARM_PACK`
overrides the pack root, so the tools read another pack's `ruff.toml` and
`harness.json`.

## Two Targets

| Field | Self-hosting | Pointed at a project |
|---|---|---|
| `workspace_root` | `..` | `../my-project` |
| `source_roots` | `[tools]` | `[../my-project/src]` |
| `persistent_tests` | harness root | project root |
| `features` | harness features | project features |

`state_root`, `artifacts_root`, and `hot_tests` stay in the pack.

## Runbook

Wiring the pack to an arbitrary project end to end — the operator questions, the
config shapes, verification, and the leak check — is in
`swarm-forge-lite/WIRING.md`.
