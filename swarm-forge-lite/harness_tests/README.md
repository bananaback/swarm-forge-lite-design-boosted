# Harness Tests

Self-tests for the SwarmForge Lite harness tooling (`swarm-forge-lite/tools/`),
not the host project. Sibling areas: `project_tests/` is the pack-side home for
the wired project's persistent tests, and `hot_tests/` is the shared generated
area.

## Wiring

Paths come from `swarm-forge-lite/harness.json` (nearest upward, or
`SWARM_CONFIG` / `SWARM_PACK`). `swarm-forge-lite/tools/shared/harness.py status` prints the
resolved paths; `swarm-forge-lite/tools/shared/harness.py config` prints them as JSON.

## Areas

| Area | Nature | Committed | Contains |
|---|---|---|---|
| `harness_tests/persistent/` | authored harness self-tests | yes | unit, property, features, acceptance steps |
| `project_tests/persistent/` | pack-side template for authored src-project tests | yes | pytest root, conftest, acceptance runtime, empty step registry |
| `hot_tests/` | generated, shared | no | generated acceptance entrypoints |

Principle: persist authored inputs; regenerate hot outputs. Deleting `hot_tests/`
must never delete a persistent test.

## Layout

```
swarm-forge-lite/
├── harness_tests/              # harness self-tests
│   ├── pytest.ini              # testpaths = persistent; pythonpath adds ../tools
│   └── persistent/
│       ├── conftest.py         # no bytecode; hypothesis storage → ../dump/hypothesis
│       ├── unit/
│       ├── property/
│       ├── features/
│       └── acceptance/
├── project_tests/              # src-project tests (pack-side template)
│   └── persistent/
│       ├── pytest.ini
│       ├── conftest.py
│       ├── unit/
│       ├── property/
│       ├── features/
│       └── acceptance/
└── hot_tests/                  # shared generated area
    └── acceptance/
```

## Running

```
cd swarm-forge-lite/harness_tests
python3 -m pytest                    # harness tests
python3 -m pytest persistent/unit    # one kind
```

Acceptance pipeline (parse → dry-check → generate → run generated tests):

```
python3 swarm-forge-lite/harness_tests/persistent/acceptance/run_acceptance.py
```

Project tests run from their own root:

```
cd swarm-forge-lite/project_tests/persistent
python3 -m pytest
```

## Switching Projects

- `swarm-forge-lite/tools/shared/harness.py clean hot` clears the shared generated area;
  add `state`, `artifacts`, or `all` to clear those too.
- Point the harness at another project with `SWARM_CONFIG=/path/to/harness.json`,
  or by editing `workspace_root` in `harness.json`.

## Rules

- No host-project imports: tests build temp project roots under pytest's `tmp_path`.
- No live state: tests touch only pytest temp roots, never the real project or
  `.swarmforge/`.
- Optional toolchains degrade: APS-dependent checks skip cleanly when `bb` is
  absent.
- Artifacts stay out of the tree: quality reports and caches go to the configured
  artifacts root.
