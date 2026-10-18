# Wiring The Pack To A Project - Agent Runbook

**Audience:** an opencode agent acting for the operator. The operator has moved
`swarm-forge-lite/` next to a real project and points you at this file. Repoint
the harness yourself; the operator does not hand-edit JSON.

**Goal:** make `swarm-forge-lite/harness.json` resolve to the target project with
the operator's chosen persistent-test placement, then prove it with the harness
CLIs and the project's tests.

**One rule above all:** `harness.json` is the single source of truth. Every path
a tool or role uses comes from it. Never hardcode a path anywhere else.

What may be calibrated, and what must not change, is classified in `INSTALL.md`
sections 2 and 3. This file is the field-by-field runbook for the calibratable part.

---

## The placeholder contract (read first)

A **new install** starts unwired. It names no project: every project path in
`harness.json` is the placeholder `<PROJECT_ROOT>`. The copy inside a working
project is already wired; this page is the runbook for a new one.

| Placeholder | Resolves from | Meaning |
|---|---|---|
| `<PROJECT_ROOT>` | `SWARM_PROJECT` | the target project directory |

Resolve it in one of two ways. The first is durable; the second leaves no trace.

1. **Wire the pack.** Replace every `<PROJECT_ROOT>` in `harness.json` with the
   project path - relative to `swarm-forge-lite/`, or absolute. This is what the
   rest of this runbook does. A wired pack holds no placeholder.
2. **Export the variable.** Set `SWARM_PROJECT=<path>` for the shell, the server,
   or one command. The tools expand the placeholder on every read. Use it for a
   quick run or a throwaway project.

The tools never guess. An unresolved placeholder is a hard error, not a silent
bad path:

```
harness: the pack is not wired: <PROJECT_ROOT> is unresolved.
Set SWARM_PROJECT=<path to the project>, or wire the pack - see WIRING.md.
```

An unknown token is an error too. Only the placeholders in the table are defined.

---

## 0. TL;DR Agent Checklist

1. Read the placeholder contract above. The shipped `harness.json` is unwired.
2. Probe, then ask the five questions in section 1, plus the project's `ENV`/`CONVENTIONS`, and write the latter into `<pack>/PROJECT.md`. Do not guess.
3. Resolve the pack and project to absolute paths; decide the relative paths you
   write (section 2, section 4).
4. Edit `swarm-forge-lite/harness.json` (section 3, section 4): replace every
   `<PROJECT_ROOT>`. Keep `state_root`, `artifacts_root`, and `hot_tests` in the pack.
5. If the target persistent root does not exist, create it from the template in
   section 5 (the pack's `project_tests/` already is that template).
6. Verify with `harness status` and `harness config` (section 6). Every row must be
   `[ok]`, and no placeholder may remain.
7. Clean the shared areas before the first run (`harness clean all`).
8. Run the project's unit/property tests and the acceptance pipeline (section 6).
9. Report the resolved paths, the test results, and anything you could not
   resolve.

---

## 1. Probe First, Then Ask

Probe the project before you ask anything. The probe answers most rows, and a
probed answer beats a guessed one. Ask the operator only when the choice is
irreversible (where the persistent root lives, overwriting an existing project
root). Otherwise take the documented default, record it under `ASSUMPTIONS`, and
continue.

| Probe | Finds |
|---|---|
| `ls` the pack's parent, and ask which directory is the project | `workspace_root` |
| `cat pyproject.toml setup.py setup.cfg` - look for `package-dir`, `packages`, `requires-python` | `source_roots`, the Python version |
| `git ls-files '*.py' \| cut -d/ -f1-2 \| sort -u` | the source trees, and where the tests already sit |
| `git ls-files 'pytest.ini' 'conftest.py' 'pyproject.toml'` | an existing persistent root to reuse |
| `git ls-files '*.feature'` | `features` |
| `git ls-files 'docs/**'` and any `NN-<subsystem>.md` | `specs` |

Then ask only these:

| Question | Why it matters | Default if the operator says "you decide" |
|---|---|---|
| What is the **target project directory**? | It becomes `workspace_root`. | A sibling of `swarm-forge-lite/`. |
| Should the **persistent tests live in the pack or in the project**? | Sets `persistent_tests[].root` and `features`. | In the pack (keeps the project tree test-free). |
| What is the **source root** (where the project's code lives)? | Becomes `source_roots`; quality tools scan it. | `<project>/src`. |
| Where are the project's **existing tests/features**, if any? | Reuse them instead of scaffolding new ones. | None - scaffold under the chosen root. |
| Where are the **requirements written** (the specs root)? | Becomes `specs`; the interrogator owns the document there. | `<project>/docs/specs`. |

If the project already has a pytest persistent root, point
`persistent_tests[].root` at it instead of scaffolding.

---

## 2. How Paths Resolve (lite rules - read before editing)

These rules live in `swarm-forge-lite/tools/shared/wiring/` and are the only way
a port breaks.

- **Base directory.** Every path in `harness.json` resolves relative to the
  **directory that contains `harness.json`** - the pack root. `~` expands to the
  home directory. Absolute paths are used as-is. Every result is canonicalized.
- **The config.** The tools read `<pack>/harness.json`. There is **no upward
  walk**. `SWARM_CONFIG` (or an explicit `--config`) replaces that file;
  `SWARM_PACK` replaces the pack root. If resolution looks wrong, check for a
  stray `SWARM_*` variable first.
- **`persistent_tests` entries** are only `{root, kind}`. There is **no
  `pythonpath` field** in the lite config - imports are handled by the persistent
  root's own `pytest.ini` (section 5).
- **`kind` is a label, not a selector.** `"harness"` marks the pack's own tests,
  `"project"` marks a wired project's tests. Nothing chooses a root by kind; both
  listed roots are used.
- **Keep the disposable areas in the pack.** Unless the operator explicitly wants
  otherwise, leave these as the pack's shared areas so nothing lands in the
  project:

| Field | Keep it at | Meaning |
|---|---|---|
| `state_root` | `".swarmforge"` (pack) | durable task state |
| `artifacts_root` | `"dump"` (pack) | parse IR, dry reports, coverage, caches |
| `hot_tests` | `"hot_tests"` (pack) | generated acceptance entry points |

---

## 3. Field Reference

| Field | Required | Default | Notes |
|---|---|---|---|
| `version` | yes | - | Always `1`. |
| `workspace_root` | yes | `..` | The project under work. |
| `state_root` | recommended | `.swarmforge` | Durable state; keep in the pack. |
| `artifacts_root` | recommended | `dump` | Reports and caches; keep in the pack. |
| `hot_tests` | recommended | `hot_tests` | Generated tests; keep in the pack. |
| `persistent_tests` | yes | `[]` | List of `{root, kind}`. |
| `source_roots` | yes | `["src"]` | Trees the quality tools scan. |
| `features` | recommended | none | The authored `.feature` root. |
| `specs` | recommended | none | The requirements workplace: where the requirements document for each feature is authored and updated. |
| `roles` | no | see below | The pipeline roles. A label list: no tool reads it. Keep it equal to the agents in `.opencode/agents/`. |

`persistent_tests[]` entry:

| Key | Meaning |
|---|---|
| `root` | The persistent test root (contains `unit/`, `property/`, `features/`, `acceptance/`). |
| `kind` | `"project"` for a wired project, `"harness"` for the pack's own tests. |

The shipped `roles` list is
`["orchestrator", "specifier", "interrogator", "architect", "designer", "critic", "coder", "test-reviewer", "refactorer", "hotfixer"]`.

Any path value may hold a placeholder instead of a literal path. The shipped pack
uses `<PROJECT_ROOT>` (see *The placeholder contract*). A wired pack holds no
placeholder.

---

## 4. Choose The Placement, Then Edit

Decide with the operator, then write one of the two shapes. In both, only
`workspace_root`, `source_roots`, `persistent_tests`, `features`, and `specs`
change; the shared areas stay in the pack.

### Option A - persistent tests in the pack (recommended; project stays test-free)

```json
{
  "version": 1,
  "workspace_root": "../myproject",
  "state_root": ".swarmforge",
  "artifacts_root": "dump",
  "hot_tests": "hot_tests",
  "persistent_tests": [
    { "root": "project_tests/persistent", "kind": "project" }
  ],
  "source_roots": ["../myproject/src"],
  "features": "project_tests/persistent/features",
  "specs": "../myproject/docs/specs",
  "roles": [
    "orchestrator",
    "specifier",
    "interrogator",
    "architect",
    "designer",
    "critic",
    "coder",
    "test-reviewer",
    "refactorer",
    "hotfixer"
  ]
}
```

Path math (layout `work/myproject/`, `work/swarm-forge-lite/`):

- config dir = `work/swarm-forge-lite`
- `workspace_root` = `../myproject` -> `work/myproject`
- `root` = `project_tests/persistent` -> `work/swarm-forge-lite/project_tests/persistent`
- `source_roots` = `../myproject/src` -> `work/myproject/src`
- `features` = `project_tests/persistent/features` -> the pack's project feature root
- `specs` = `../myproject/docs/specs` -> `work/myproject/docs/specs`

The pack's `project_tests/` already ships the pytest root, conftest, acceptance
runtime, generator, runner, and an empty step registry - nothing to scaffold.

### Option B - persistent tests inside the project

```json
{
  "version": 1,
  "workspace_root": "../myproject",
  "state_root": ".swarmforge",
  "artifacts_root": "dump",
  "hot_tests": "hot_tests",
  "persistent_tests": [
    { "root": "../myproject/tests/persistent", "kind": "project" }
  ],
  "source_roots": ["../myproject/src"],
  "features": "../myproject/tests/persistent/features",
  "specs": "../myproject/docs/specs",
  "roles": [
    "orchestrator",
    "specifier",
    "interrogator",
    "architect",
    "designer",
    "critic",
    "coder",
    "test-reviewer",
    "refactorer",
    "hotfixer"
  ]
}
```

Path math:

- `root` = `../myproject/tests/persistent`
- `features` = `../myproject/tests/persistent/features`
- `specs` = `../myproject/docs/specs`

In Option B the authored tests intentionally live in the project, but the
**disposable** areas still do not: `dump/`, `hot_tests/`, and `.swarmforge/` stay
in the pack, and the project-side pytest root must keep its caches in the pack
(section 5). You must also copy the acceptance components (`runtime.py`, `generator.py`,
`run_acceptance.py`, `steps/`) into the project root, because `run_acceptance.py`
locates its siblings relative to itself.

### Absolute project paths

Relative paths survive moving the pack and project together. When the project is
not a sibling, absolute paths are valid:

```json
"workspace_root": "/srv/apps/myproject",
"source_roots": ["/srv/apps/myproject/src"],
"persistent_tests": [
  { "root": "/srv/apps/myproject/tests/persistent", "kind": "project" }
],
"features": "/srv/apps/myproject/tests/persistent/features",
"specs": "/srv/apps/myproject/docs/specs"
```

Never mix a relative `root` with an absolute `pythonpath`-style value; always
confirm the result with `harness config`.

---

## 5. Create Or Adapt The Persistent Test Root

The pack's `project_tests/` is the working template. A persistent root is a
pytest root: it needs a `pytest.ini` and a `conftest.py` that makes the project
source importable.

Layout:

```
<persistent root>/
|-- pytest.ini
|-- conftest.py
|-- unit/          # TDD unit tests
|-- property/      # hypothesis properties
|-- features/      # authored Gherkin specs
+-- acceptance/    # runtime + generator + runner + steps/
```

`pytest.ini` - the pack copy is:

```ini
[pytest]
testpaths = .
```

- `testpaths = .` makes the persistent root its own pytest root, so
  `cd <persistent root> && python3 -m pytest` works in place.
- The pytest cache is redirected by the `lane` wrapper, which adds
  `-o cache_dir=<pack>/dump/pytest-cache` through `PYTEST_ADDOPTS`. Do not put a
  `cache_dir` in `pytest.ini`: a bare `pytest` outside the lane writes
  `.pytest_cache` into the root, so keep that entry in the project's `.gitignore`.
- Do not add inline `;` comments; `pytest.ini` does not parse them.

The persistent root's `conftest.py` loads `wiring` and puts the project source
on `sys.path`, so tests can import it without a `pythonpath` entry. It carries no
project-specific fixtures; those belong to the wired project.

The root finds the pack through its own `acceptance/packroot.py`: `SWARM_PACK` first
(the lane wrapper exports it), then a walk up the tree. A root copied anywhere in the
workspace resolves with no edit. Details: `INSTALL.md` section 5.
Caches (`.pytest_cache`, `.hypothesis`, `.coverage`) and bytecode may appear in
either tree; pack and project `.gitignore` cover them, so nothing is redirected.

Step handlers: add one module per feature area under
`project_tests/persistent/acceptance/steps/`, exposing a `HANDLERS` list.
`steps/__init__.py` discovers every sibling module automatically, so a new
feature area adds one file and edits nothing. The `gherkin-parser` and
`ir-dry-checker` wrappers, and the acceptance runtime/generator/runner, are
reused from the pack; do not re-author them.

---

## 6. Verify (do this before reporting done)

Run from the workspace root, in order.

```bash
# 0. No placeholder may remain in a wired pack (must print 0)
grep -c '<PROJECT_ROOT>' swarm-forge-lite/harness.json

# 1. Every path resolves and exists (exit 2 on a bad config)
python3 swarm-forge-lite/tools/shared/harness.py status

# 2. The resolved JSON, to check the persistent root and source roots
python3 swarm-forge-lite/tools/shared/harness.py config

# 3. Clean the shared areas before the first run of a new project
python3 swarm-forge-lite/tools/shared/harness.py clean all

# 4. The project's unit + property tests (from the chosen persistent root)
cd <persistent root> && python3 -m pytest

# 5. The project's acceptance pipeline (parse -> dry -> generate -> run)
python3 <persistent root>/acceptance/run_acceptance.py
```

`<persistent root>` is the resolved `PERSIST` row: Option A is
`swarm-forge-lite/project_tests/persistent`; Option B is the project root you set.

Expected: `harness status` marks every row `[ok]`; no `<PROJECT_ROOT>` remains in
`harness.json`; the unit/property suites pass; the acceptance pipeline exits 0. If the project has no tests yet, say so and
report the resolved paths instead of inventing tests. If `harness status` still
shows a non-`[ok]` row after two fix attempts, stop and report the exact row
instead of looping.

`run_acceptance.py` reads features from `features`, parses each into
`artifacts_root/<stem>.json`, dry-checks into `artifacts_root/<stem>.dry.json`,
generates entry points into `hot_tests/acceptance/`, then runs them. It loads
wiring from `SWARM_CONFIG` or the pack's `harness.json`; pass
`SWARM_CONFIG` when you are using an alternate config.

---

## 7. Return To Self-Hosting

Before the pack is wired to any project it self-hosts. The self-host config
(`harness.selftest.json`) holds no placeholder: it resolves inside the pack.
Restore these four fields in `swarm-forge-lite/harness.json`, then clean:

```json
"workspace_root": "..",
"source_roots": ["tools"],
"persistent_tests": [
  { "root": "harness_tests/persistent", "kind": "harness" },
  { "root": "project_tests/persistent", "kind": "project" }
],
"features": "harness_tests/persistent/features"
```

```bash
python3 swarm-forge-lite/tools/shared/harness.py clean all
```

That is the entire switch: four fields in one file.

---

## 8. Switching Between Targets Without Editing (optional)

To keep two targets side by side, leave `harness.json` alone and add a second
config in the pack, e.g. `swarm-forge-lite/harness.myproject.json`. Select it
with `SWARM_CONFIG` or `--config`:

```bash
python3 swarm-forge-lite/tools/shared/harness.py \
  --config swarm-forge-lite/harness.myproject.json status
SWARM_CONFIG=swarm-forge-lite/harness.myproject.json \
  python3 swarm-forge-lite/project_tests/persistent/acceptance/run_acceptance.py
```

Clean the shared `hot_tests/` before switching, or the previous project's
generated entry points collide with the next.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `harness: cannot read config ...` | Bad path or malformed JSON | Fix `harness.json`; the error names the file. |
| `the pack is not wired: <PROJECT_ROOT> is unresolved` | The shipped config is still unwired | Replace `<PROJECT_ROOT>` in `harness.json`, or export `SWARM_PROJECT`. |
| `unknown placeholder <...>` | A token that is not in the contract | Use `<PROJECT_ROOT>`, or write a literal path. |
| A path resolves to the wrong place | A stray `SWARM_*` env var overrides the file | Unset `SWARM_CONFIG` / `SWARM_PACK`; check for an explicit `--config`. |
| Tests cannot import the project | The persistent root's `conftest.py` puts the wrong directory on `sys.path` | It adds each `source_roots` entry's parent. Point `source_roots` at the package directory, and confirm with `harness config`. |
| Generated tests collide across projects | Shared `hot_tests/` holds the previous project's entry points | `harness clean hot` (or `all`) before switching. |
| `clean state` refuses | State items are locked | Only use force with operator confirmation. |
| `.pytest_cache`/`__pycache__` in the project | Allowed | Confirm the `.gitignore` entries exist; nothing to clean. |
| Acceptance needs a config | The runner cannot find one | Pass `SWARM_CONFIG` or `--config`. |
| APS tasks missing | Babashka (`bb`) is not installed | Install `bb`; APS-dependent checks skip without it. |

---

## 10. Boundaries

- Edit **only** `harness.json` (or add a new config in the pack). Do not edit the
  tools, the agent prompts, or the constitution to make a path work.
- Never write into the project's source roots. The project source stays
  test-free; only Option B's persistent root is authored inside the project.
- Never delete `swarm-forge-lite/harness_tests/persistent/` (the pack's own
  tests). `hot_tests/`, `dump/`, and `.swarmforge/` are disposable; the project
  tree is not.
- Prefer relative paths; they survive moving the pack and project together.
- After editing, always run `harness status` **and** `harness config` and read
  the resolved output before claiming the port is done.
- Report back: the config file you changed, the resolved `workspace_root` and
  persistent root, the placement chosen, and the test results.
