# Engineering

Binding rules. `<pack>` is the resolved pack root. Paths come from `harness.json`;
`python3 <pack>/tools/shared/harness.py status` prints them.

## Layout

- The **subsystem** is the unit of design, state, lane, and record.
- The **module** is the unit of parallel design and of the frozen interface.
- Source stays test-free. Authored tests live in the configured persistent test roots.
- Generated acceptance tests live in `hot_tests/<lane>`. Never commit them.
- Artifacts and caches live in `dump/<lane>`. Never commit them.
- A flat record has four durable files plus the model:

```
design/subsystems/<subsystem>/
  GOAL.md            orchestrator scratchpad, max ~40 lines
  requirements.md    frame, goal, Rn/ACn, Cn, Xn, traceability, DECISIONs
  architecture.md    module map, shared files, frozen interface sections
  modules/<m>.md     contract + design + decisions for one module
  SKELETON.md        generated union for coder and refactorer
  model.json         topology, edited through swarm.uml
  model.html         derived review page; never read, never hand-edit
  review.md          optional critic review
  docs/specs/NN-<subsystem>.md   the shipped requirement document (SPECS root)
```

## Lanes

- The subsystem name is the lane id. A parallel designer uses `<subsystem>.<module>`.
- Every shell command runs through `<pack>/tools/shared/lane <lane> <command...>`.
- Never run `pytest`, `ruff`, `dryer`, or `crapper` directly.
- The lane sets `SWARM_PACK`, `SWARM_LANE`, `SWARM_TEST_DATA`, `TMPDIR`,
  `PYTHONPYCACHEPREFIX`, `HYPOTHESIS_STORAGE_DIRECTORY`, and `PYTEST_ADDOPTS`.
  It does **not** set `PYTHONPATH`.
- `lane --config <path> <lane> <command...>` selects another `harness.json`.
- One subsystem per session. Do not run two sessions on one record.
- The lane writes `<state_root>/owner` with the session id, pid, host, and time.
  It is awareness, not a lock. Read it when a file changes under you; never block
  on it.

## Commands

Prefer the `swarm.*` tools. The shell forms are fallback only.

| Task | Command |
|---|---|
| Tests | `lane <s> bash -c 'cd <persistent-root> && python3 -m pytest <paths or -k EXPR>'` |
| Ruff | `python3 <pack>/tools/shared/ruff4py <source roots> <persistent roots>` |
| Format | `python3 -m ruff format --check --cache-dir <pack>/dump/<lane>/ruff-cache <roots>` |
| CRAP | `PYTHONPATH=<pack>/tools/refactorer python3 -m crapper --root <artifacts> --source-root <src> --threshold 10` |
| DRY | `PYTHONPATH=<pack>/tools/shared python3 -m dryer --root <artifacts> --threshold 0.82 --min-lines 4 --min-nodes 20 <paths>` |
| Gherkin | `<pack>/tools/shared/gherkin-parser <feature> <artifacts>/<stem>.json` |
| Dry-check | `<pack>/tools/specifier/ir-dry-checker <ir> <artifacts>/<stem>.dry.json` |
| Acceptance | `python3 <persistent-root>/acceptance/run_acceptance.py [feature ...]` |

## Record rules

- The record is living and operator-owned. Edit it in place, by delta. Never
  copy a template over it, never regenerate an untouched table, never add a
  revision, status, or change log.
- One fact has one home. `requirements.md` holds requirement facts and decisions.
  `architecture.md` holds the cut and the frozen interfaces. A module file holds
  its own contract.
- The frozen zone is the interface sections in `architecture.md` and the accepted
  `SKELETON.md` contracts. A change there is `module-cut`, never `contained`.
- The requirement document is a view. `swarm.genDoc` rewrites existing rows in
  place. Never hand-edit a generated row and never create a second numbering space.
- IDs: `Rn` requirement, `ACn` acceptance criterion, `Cn` constraint, `Xn`
  exclusion, `Dn` decision, `Gn` goal node.
- A gap is `ASSUMED:`, a `DECISION` row, or `blocked`. Never invent a value.

## Model

- `model.json` is the only editable topology. Edit it through `swarm.uml`.
- `model.html` is generated. Never read it, never edit it.
- `swarm.uml` queries: `classes`, `ops`, `edges`, `violations`, `stats`, `check`.
- `swarm.uml({op:'render'})` renders the page after a change.

## Quality

- Files stay under 600 lines. Split in the same change.
- CRAP per function is at most 10. DRY threshold is 0.82.
- Terminal gate: `swarm.gate({subsystem, feature, crap:true})` returns `pass:true`
  only when dry, ruff, format, pytest, acceptance, and CRAP are clean.
- The test-reviewer gate runs after the coder and before the refactorer.
- Acceptance mutation is out of scope; test quality is judged by the reviewer.
