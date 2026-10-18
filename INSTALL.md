# Install the harness

Read `HARNESS_SELF_IMPROVEMENT.md` first. It records the owner's goal, the
current harness shape, the verified baseline, and the open optimization work.

This folder is a complete, self-contained agent harness for a Python project. Drop it
at the root of a workspace, install the dependencies, calibrate it to the project,
and run it. It ships **unwired**: it names no project and resolves no project path
until you wire it.

The pack is built to fit an unknown project. A small part of it is fixed - it is what
makes the system work. Everything else calibrates to the project's real layout, however
deep the source, the tests, or the docs sit. Section 2 is the fixed part, section 3 is
the calibratable part, and sections 5 to 6 say what to do when a path is not there.

## 1. Prerequisites

| Need | Required by | Notes |
| --- | --- | --- |
| `python3` 3.10+ | every `swarm-forge-lite/tools/` entry point | Modern annotations and typing throughout. |
| `pytest` | the persistent test roots | Test runner. |
| `hypothesis` | `property/` in a persistent root | Property tests. |
| `tree-sitter-language-pack` | `tools/shared/dryer/` | Pulls in `tree-sitter`. DRY scanning. |
| `PyYAML` | `switch_agent_model.py` | Agent frontmatter read/write. |
| `coverage` | `tools/refactorer/crapper/` | Python CRAP scoring reads an LCOV report. Absent, Python scores 0%. |
| `ruff` | `tools/shared/ruff4py/` | Found on `PATH` by name. |
| `bb` (Babashka) | `tools/shared/aps/` | `gherkin-parser`, `ir-dry-checker`, `gherkin-mutator`. Checks skip cleanly without it. |
| `node` | the umlview render tests | They skip without it. |
| `codegraph` | the `codegraph` MCP server in `opencode.json` | `codegraph serve --mcp`. Optional; remove the server to skip it. |

```bash
python3 -m pip install pytest hypothesis tree-sitter-language-pack PyYAML coverage ruff
```

Missing a tool degrades that one check. Missing `python3` stops everything.

## 2. The fixed form - do not move, rename, or re-author

The tools find themselves and their data by depth from the pack root, and the protocol
names these paths literally. Relocating any of them breaks the system.

| Fixed | Why |
| --- | --- |
| `harness.json` at the pack root | The config locator reads that name at that place. A second config is fine, but it must be selected with `--config` or `SWARM_CONFIG`. |
| The pack's internal layout: `tools/shared/wiring/`, `tools/shared/{harness.py,lane,record.py,questions.py,swarm_json.py}`, `tools/{specifier,refactorer}/`, `protocol/`, `reference/`, `constitution/`, `design/templates/GOAL.md`, `harness_tests/`, `project_tests/` | Entry points compute their own location from the pack root, and the tools import each other by these names. |
| `protocol/<role>.md`, named by role | The dispatch envelope prints it. A role name and its protocol file are one string. |
| The flat record under `design/subsystems/<subsystem>/` | `requirements.md`, `architecture.md`, `modules/<module>.md`, `review.md`, `GOAL.md`, `model.json`, `model.html`. `questions.FLAT_FILES` fixes the names. The subsystem name and the `LANE` are one string. |
| `PROJECT.md` and its `## ENV` heading | The dispatch envelope prints that block verbatim. The heading is parsed by name. |
| The persistent-root contract (section 5 names where it may sit) | It is a pytest root: `pytest.ini` with `testpaths = .`, a `conftest.py`, and `acceptance/` (`packroot.py`, `run_acceptance.py`, `generator.py`, `runtime.py`, `steps/`). It holds `unit/`, `property/`, `features/`, `acceptance/steps/`. A step module exposes a `HANDLERS` list; `steps/__init__.py` discovers every sibling by filename, so there is no registry to edit. |
| The pack's acceptance components: `run_acceptance.py`, `generator.py`, `runtime.py`, `steps/__init__.py` | Reuse them. Do not re-author them. Section 5 covers where they may live. |
| Authored versus disposable | Authored tests and features persist. `dump/`, `hot_tests/`, and `.swarmforge/` are disposable, stay in the pack, and are never authored. |
| The lane wrapper for every command | `swarm-forge-lite/tools/shared/lane <lane> <command>` scopes `SWARM_TEST_DATA`, `TMPDIR`, the bytecode cache, the hypothesis store, and the pytest cache into the pack. Never set those by hand. |

## 3. The calibration points - fit them to the project

Everything in this table is project-dependent. Read each row, probe, then write the
value. A wrong guess here is cheap to fix; a hardcoded path in a tool or a prompt is not.

| Knob (in `swarm-forge-lite/harness.json`) | Decides | How to find it | Default when the operator says "you decide" |
| --- | --- | --- | --- |
| `workspace_root` | the project directory | Ask. Confirm it holds the source. | A sibling of the pack. |
| `source_roots` | the Python trees the quality tools scan | Look for `pyproject.toml`, `setup.py`, `setup.cfg`, `[tool.setuptools] package-dir`. Or `git ls-files '*.py' \| cut -d/ -f1-2 \| sort -u`. May be several, and may be nested. | `<PROJECT_ROOT>/src` |
| `specs` | the requirements workplace | Look for `docs/specs`, an existing `NN-<subsystem>.md`, or the `SPECS` row of a previous `harness status`. | `<PROJECT_ROOT>/docs/specs` |
| `features` | the authored `.feature` root | `git ls-files '*.feature'` | pack-side `project_tests/persistent/features` |
| `persistent_tests[].root` | the pytest root that holds the authored tests | Look for `pytest.ini`, `conftest.py`, or `[tool.pytest.ini_options]`. If one exists, point at it. If none exists, scaffold from the pack's `project_tests/persistent`. | pack-side `project_tests/persistent` |
| `persistent_tests[].kind` | nothing but a label | - | `project` |
| `state_root`, `artifacts_root`, `hot_tests` | the disposable areas | Keep all three in the pack, so nothing disposable lands in the project. | the pack defaults |
| `PROJECT.md`: `ENV`, `CONVENTIONS`, `REFERENCES` | what every dispatch carries | Read the project. Do not infer. | - |
| The two relocated-root expressions (section 5) | how a moved root finds the pack | Only when you move or copy the root. | - |

Two fields are labels, not switches:

- `roles` is a list of names for the record. No tool reads it. Keep it equal to the
  agents that exist in `.opencode/agents/`.
- `persistent_tests[].kind` is carried through and never selects a root. Both listed
  roots are used.

## 4. Install

1. **Place the pack at the workspace root.** The root is the directory OpenCode opens.
   It must hold `opencode.json`, `AGENTS.md`, and `swarm-forge-lite/` side by side.
2. **Install the prerequisites** (section 1).
3. **Optional - pick the agent models.** `opencode.json` sets the default model. To set
   a model per role, edit the `AGENT_MODELS` map in `switch_agent_model.py` and run it
   from the root:

   ```bash
   python3 switch_agent_model.py --list     # show the plan, write nothing
   python3 switch_agent_model.py            # apply it
   ```
4. **Calibrate and wire.** Follow `swarm-forge-lite/WIRING.md`, which is the field-by-field
   runbook for section 3. It replaces every `<PROJECT_ROOT>` in `harness.json`. For a quick
   look before wiring, export the variable instead of editing:

   ```bash
   SWARM_PROJECT=/path/to/project python3 swarm-forge-lite/tools/shared/harness.py status
   ```
5. **Verify.** Every row must be `[ok]`, and no placeholder may remain:

   ```bash
   grep -c '<PROJECT_ROOT>' swarm-forge-lite/harness.json   # must print 0
   python3 swarm-forge-lite/tools/shared/harness.py status
   ```
6. **Run.** `AGENTS.md` and `opencode.json` are what OpenCode loads; the orchestrator
   agent drives the pipeline from there.

## 5. When the persistent root is not where the pack put it

The project's tests may sit anywhere: `tests/`, `pkg/app/tests/`, `src/tests/unit/`. Point
`persistent_tests[].root` at that directory, and copy the pack's `project_tests/persistent`
there if it does not exist yet. Nothing else needs editing: the root's
`acceptance/packroot.py` finds the pack by `SWARM_PACK` - which the lane wrapper exports -
and otherwise by a walk up the tree for the pack's `tools/shared/wiring`.

| Keep | Why |
| --- | --- |
| `pytest.ini` with `testpaths = .` | Makes the root its own pytest root. |
| `acceptance/packroot.py` | The pack locator, shipped with the template. Do not edit it, and do not drop it. |
| `acceptance/{run_acceptance.py,generator.py,runtime.py,steps/}` together | The runner locates its siblings relative to itself. |

Two rules follow:

- **Run through the lane wrapper.** It exports `SWARM_PACK`, so a root resolves from
  anywhere. A root that sits outside the pack and runs without the wrapper must set
  `SWARM_PACK=<pack root>`; the locator says exactly that in its error.
- A bare `pytest` outside the lane writes `.pytest_cache` into the root. Keep that entry
  in the project's `.gitignore`. Through the lane, the cache lands in the pack.

## 6. When something is missing - do not get stuck

- **Reuse before you scaffold.** If a persistent root exists, point at it and adapt it.
  Scaffold from `project_tests/persistent` only when none exists.
- **Ask only when the choice is irreversible**: where the persistent root lives, or
  overwriting an existing one. Otherwise take the default in section 3, write it under
  `ASSUMPTIONS`, and continue.
- **A missing optional directory is not an error.** If `features` or `specs` is absent,
  create it empty, or leave the field out. A missing `bb`, `node`, `ruff`, or `coverage`
  skips that check and nothing else.
- **Never invent tests.** If the project has none, say so and report the resolved paths.
- **Stop after two attempts.** If a `harness status` row is still not `[ok]`, report that
  exact row and stop. Do not loop, and do not work around it by editing a tool, a prompt,
  or the constitution.

## 7. Per project - not part of this harness

- **Skills** live in `.agents/skills/`, with `skills-lock.json` recording them. Install
  the skills a project needs into that project. They are not carried here.
- **`.codegraph/`** is generated by the codegraph plugin. Do not copy an index; run
  `codegraph init` in the new workspace.

## 8. Entry points

- `python3 swarm-forge-lite/tools/shared/harness.py --help` - config, status, clean, records, envelopes.
- `swarm-forge-lite/tools/shared/lane <lane> <command>` - runs one command with every disposable output scoped to the lane.
- `swarm-forge-lite/WIRING.md` - the wiring runbook: the fields of section 3, in order.
- `swarm-forge-lite/PROJECT.md` - the project facts: fill `ENV`, `CONVENTIONS`, and `REFERENCES`.
