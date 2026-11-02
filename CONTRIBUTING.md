# Contributing

How to change this harness without breaking the installs that run it.

---

## Part 1 — for an agent changing the harness

An improvement made in one install is an upgrade for every install, so a change
here is a compatibility change, not a local edit.

### 1. The invariants

Each one has a test. If a change violates one, the suite fails — that is the
point, not an obstacle.

| # | Invariant | Enforced by |
|---|---|---|
| I1 | **Tier boundary.** Authored knowledge → project repo; workspace wiring → pack, untracked; generated output → pack scratch. The two rendered views stay in the project's docs. | `tests/contract/test_tier_boundary.py` |
| I2 | **No project specifics** in the general tier: no project name, host product, language tool or absolute path in `constitution/`, `protocol/`, `INSTALL.md`, `CONTRIBUTING.md`, `README.md`. | `test_instruction_hygiene.py` |
| I3 | **Host neutrality by absence.** No host API, no daemon, no per-host adapter file. The one entry point is `protocol/orchestrator.md`. | `test_portability.py` |
| I4 | **Compatibility.** A migration only adds or copies. A tracked state path is never deleted or renamed; deprecate for one release. | review + `test_update.py` |
| I5 | **Config hygiene.** `<PACK>` instead of a folder name, no absolute paths, schema-validated. | `pack.schema.json`, `test_config.py`, `test_schema.py` |
| I6 | **A contract test per behavior.** Every rule in the goal's C2 list has a test that fails without the behavior. | review |
| I7 | **Records move together.** Version, `CHANGELOG.md` and any migration change in the same commit. | `test_release_consistency.py` |
| I8 | **Installability.** Every file a workspace must supply ships as `*.example`, and `install.py` can create it. | install fixture in CI |
| I9 | **Determinism.** The same input renders byte-identically. | `test_design_surface.py` (renders twice, compares bytes) |
| I10 | **One gate to push.** `python3 tools/selftest.py` is green. | CI |

### 2. Classify the change first

| Class | Examples | Version | Same commit must carry |
|---|---|---|---|
| docs | wording, a paragraph in a role prompt | patch | nothing |
| capability | a new gate, a new config key with a default | minor | contract test, changelog, `*.example` update |
| layout | a path moves, a new local file, a rename | minor + migration | migration, deprecation warning, changelog; both layouts green |
| breaking | removing an option, changing an exit code | major + operator approval | migration, one release of deprecation, changelog `BREAKING CHANGE:` |

An agent never declares a change breaking on its own: it proposes it in the
report and the operator decides.

### 3. Procedure

1. Read this file and the goal's contract rules for the area you touch.
2. Classify the change (above) **before** writing code. Stop for the operator if
   it is layout or breaking.
3. Write the test first; name the wrong implementation it rejects.
4. Make the change.
5. Run `python3 tools/selftest.py`. Red is not done.
6. Update the records the class requires: `VERSION`, `CHANGELOG.md`, a migration.
7. Commit with the conventional type, push only when the operator asks.
8. Report: what changed, the class, each command and its exit status.

### 4. When a change cannot avoid an invariant

Never relax a check to make a change fit. Instead:

1. add a migration that moves state additively, with an `is_needed()` guard;
2. keep the old path working for one release, with a deprecation note;
3. record it under **Deprecated** in `CHANGELOG.md`;
4. change the check in the same commit as the behavior, and say in the body why
   the old check was wrong.

A convention may be superseded by a written decision. It is never bypassed
silently.

---

## Part 2 — for the operator

### Review checklist

- the change class is stated and matches the diff;
- no tracked state path is deleted or renamed;
- a new required file ships as `*.example`;
- the test fails without the change and names what it rejects;
- `VERSION`, `CHANGELOG.md` and any migration agree;
- `python3 tools/selftest.py` is green;
- no project data and no host product appears in the diff.

### Release

1. bump `VERSION`;
2. add the `CHANGELOG.md` section under that version;
3. commit, tag `v<VERSION>`, push;
4. consumers learn about it through `tools/update.py check`.

### Rollback

Consumers never lose project data to an upgrade, so a rollback is a harness
change only: check out the previous tag and run `doctor`. The project's `design/`
folder and its specs are untouched by design.
