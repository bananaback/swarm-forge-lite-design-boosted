# Tools

Two vendored analyzers and the acceptance pipeline. Every command below runs with
the project root as the working directory, and every command is what a role names
in its report.

`$PACK` is the pack root: the directory holding `config/` and `constitution.md`.
This file is `$PACK/tools/README.md`. `$PROJECT` is the `project_root` of the
*selected* project (see **Projects** below), resolved against `$PACK` to an
absolute path. Scratch lives in `$PROJECT/<artifacts root>`.

## Projects

One pack serves several projects. `config/pack.json` holds a `projects` map, and
each entry carries its own `project_root`, `source_roots`, `class_root`,
`test_paths`, `unit_paths`, `lint_paths`, `features`, `docs_root`, `specs`,
`acceptance_command`, `artifacts_root` and `umlview` policy. Every path in this
file resolves through the selection, so no prompt or role hardcodes a layout.

`PACK_PROJECT` selects the project; when it is unset, `default_project` applies
silently. Every command a brief or a snippet shows therefore carries
`PACK_PROJECT=<project>` explicitly.

```sh
export PACK_PROJECT=<project>             # e.g. one key of config/pack.json
python3 $PACK/tools/design/arch.py env    # what resolved, and why
```

`arch.py env` is the first command of a dispatch. It prints the project, whether
the name came from `PACK_PROJECT` or from the default, and the resolved app,
class root, docs, architecture and scratch directories. Keep it in the report: it
is the proof that later commands used the intended project.

A missing tree, a missing `runtime.json`, or an empty `specs` map is a failure,
not a clean project — those commands exit non-zero and name what is missing. An
empty `arch classes ls` or `umlview ls` is the one shape that used to look green;
it no longer does.

Each project owns its own `<PACK>/architecture/<project>/` and its own
`<artifacts_root>`, so scratch and design models never mix across projects.

`artifacts_root` resolves against the project root, so a `..` value keeps every
report and generated test outside the repository — each project entry uses
`../swarm-forge-lite/tmp/<project>`, which leaves `git status` untouched.

> **Pass absolute paths to `--source-root`.** A relative path matches nothing and
> the tool still exits 0, so DRY or CRAP appears clean without analyzing a single
> file. Check that the report names the functions you expected.

| Tool | Path | Needs |
|---|---|---|
| `dryer` | `tools/shared/dryer` | `tree-sitter`, `tree-sitter-language-pack`, Python ≥ 3.11 |
| `crapper` | `tools/refactorer/crapper` | same as dryer, `coverage` for CRAP |
| APS | `tools/shared/aps` + `tools/shared/gherkin-parser` | Babashka (`bb`) on PATH |

## Search and navigation

Locate code before reading it. When a `.codegraph/` directory sits at any
ancestor of the project root, the tree is indexed: ask the index first.

```sh
codegraph explore "<symbols or question>"
```

One call returns the matching symbols' source and the call paths between them,
including dispatch a grep cannot follow. Without an index, use `glob`, or `grep`
with a path. Never open with a broad recursive search: name the file or subtree,
skip caches and generated trees, and widen only on a miss. Indexed paths can be
stale — resolve a hit by file name.

## Lint and format

Lint and formatting are plain `ruff`, a project dependency rather than part of
this pack.

```sh
ruff check <files you touched>
ruff format --check <files you touched>
```

Run them from the project root, with no flags. Ruff reads the project's own
`ruff.toml` for every file it checks; this pack ships no ruff configuration and
no options of its own. Clean means exit 0: a finding is a report, not a verdict
to negotiate.

## Unit tests

```sh
python3 -m pytest -q "$PROJECT/<unit path>"
```

## Acceptance

```sh
$PACK/tools/shared/gherkin-parser "$PROJECT/<features>/<stem>.feature" "$PROJECT/<artifacts root>/<stem>.json"
bb --config $PACK/tools/shared/aps/bb.edn gherkin-ir-dry-checker \
  "$PROJECT/<artifacts root>/<stem>.json" "$PROJECT/<artifacts root>/<stem>.dry.json"
<acceptance_command from config>      # the project runner the coder built
```

Delete `$PROJECT/<artifacts root>/<stem>.*` before parsing. An IR left by an earlier run is
indistinguishable from a fresh one, so a stale file can make a dry-check look
green against someone else's parse.

`gherkin-parser` and `gherkin-ir-dry-checker` are read-only; they parse and
report. Clean means both exit 0. Their findings are advisory — report the counts,
do not edit the feature to silence them.

## For Project-Side Runners

A generated acceptance runner reads the same contract. It must:

- treat the pack root as the directory holding `config/pack.json`;
- read `project_root`, `features`, `source_roots`, `test_paths`, and
  `artifacts_root` from that file; `project_root` resolves against the pack root,
  every other path against the project root;
- derive `tests_root` = `project_root/test_paths[0]`;
- put IR, dry reports, and any scratch under `project_root/artifacts_root`, and
  generated acceptance tests under `project_root/artifacts_root/acceptance`;
- invoke the pipeline exactly as above;
- require the selector: when `projects` holds more than one entry and
  `PACK_PROJECT` is unset, exit non-zero naming the declared projects. A runner
  that falls back to `default_project` analyzes another project's features and
  still exits 0.

There is no `wiring` module in this pack. A runner that imports one was written
for the retired pack; change the runner, do not resurrect the module. A
project-local resolver of any other name that reads `config/pack.json` is fine —
that is what the project owns.

## Duplicate analysis

```sh
PYTHONPATH=$PACK/tools/shared python3 -m dryer \
  --root "$PROJECT/<artifacts root>" \
  --source-root "$PROJECT/<source root>" \
  --threshold 0.82 --min-lines 4 --min-nodes 20
```

Pairs print worst first and the report lands in
`$PROJECT/<artifacts root>/.metrics/dry.edn`. A `No source files to analyze.`
line means the source root was wrong, not that the code is clean.

## CRAP

CRAP reads coverage first, from
`<artifacts root>/target/coverage/<language>/lcov.info`:

```sh
python3 -m coverage run --data-file "$PROJECT/<artifacts root>/.coverage" \
  -m pytest -q "$PROJECT/<unit path>"
python3 -m coverage lcov --data-file "$PROJECT/<artifacts root>/.coverage" \
  -o "$PROJECT/<artifacts root>/target/coverage/python/lcov.info"
PYTHONPATH=$PACK/tools/refactorer python3 -m crapper \
  --root "$PROJECT/<artifacts root>" --use-existing-coverage \
  --source-root "$PROJECT/<source root>" --threshold 10
```

Exit 2 means the worst score is above the threshold: 10.0 passes, and there is no
headroom left. Report the worst score as well as the exit code. The report lands in
`.metrics/crap.edn` under the artifacts root.

## Design surface (project-local)

The project's two design views are generated from code plus one authored runtime
model, never hand-edited:

```sh
python3 swarm-forge-lite/tools/design/arch.py env
python3 swarm-forge-lite/tools/design/arch.py classes ls|show|deps|validate|render
python3 swarm-forge-lite/tools/design/arch.py classes add|remove|annotate|diff
python3 swarm-forge-lite/tools/design/arch.py runtime ls|show|validate|render
python3 swarm-forge-lite/tools/design/arch.py docs validate
python3 swarm-forge-lite/tools/design/arch.py render [classes|runtime|all]
```

`env` prints the resolved project and every path below; run it first, so a report
can never claim a gate it ran against another project.

`docs validate` checks the subsystem specs against the model: every class has a
row, the six sections exist, and no spec mentions a test or acceptance id. The
`specs` and `subsystems` keys of the selected project are the designer's: `specs`
names each spec file, `subsystems` declares the packages and their layer.
Specs and the generated views live under `<PROJECT>/<docs_root>`, where
`docs_root` and the `specs` list are entries in the project's `config/pack.json`
block. A project with no declared specs fails this gate rather than passing
vacuously.

`classes` scans the AST on every call; there is no stored model to drift.
`runtime` reads `<PACK>/architecture/<project>/runtime.json`; `validate` fails
when a subsystem under the project's `class_root` has no box. `classes
add|remove|annotate` write `<PACK>/architecture/<project>/design.json` (the draft
overlay); `diff` reports what the code has not caught up with. The pack's
`umlview` remains the module-grade view and is not involved.

## Diagram

A generated UML of the project, with the design validation kept from the
original viewer: source is scanned into a model, a policy orders it, and the
dependency rule marks violations.

```sh
python3 $PACK/tools/umlview init        # derive the policy from the code (once)
python3 $PACK/tools/umlview load IR     # authored EDN/JSON IR -> model.json
python3 $PACK/tools/umlview load IR     # authored EDN/JSON IR -> model.json
python3 $PACK/tools/umlview scan        # source + policy -> model.json
python3 $PACK/tools/umlview validate    # exit 1 on a dependency-rule violation
python3 $PACK/tools/umlview render      # model.json -> viewer.html
python3 $PACK/tools/umlview ls [--at PATH] [--violations] [--proposal NAME]
python3 $PACK/tools/umlview show ID
python3 $PACK/tools/umlview policy show|order|level|foreign|omit|edge-kind|propose ...
python3 $PACK/tools/umlview validate --proposal NAME
```

`scan` writes the policy itself when none exists, the way the original's
designer agent did: it derives the prefix, the segment order, and the levels
from the observed dependency direction. Nobody hand-authors the policy; a human
only contradicts it when the intent differs.

`load` reads a hand-authored IR — EDN or JSON — and applies the same
normalization and range checks as the original: ids lowercased, `crap` as a
number or `{mu, max, sigma}`, coverage inside 0–1, unique class ids, and every
edge endpoint known. A document may hold one diagram or a stack under
`:diagrams`; the viewer renders them top to bottom, exactly as the original
does. Commands that inspect one diagram (`validate`, `ls`, `show`) use the
first, matching his `load-diagram`.

The viewer renders a static diagram as package boxes, exactly as a generated
hierarchical diagram renders as a namespace tree.

A policy with `packages` and `diagrams` selects the packaged branch, as his
does: each `diagrams` entry becomes one generated diagram — `{"view":
"overview"}` for one box per policy package plus an `Unassigned` box, or
`{"package": "<id>"}` for that package with its neighbour stubs. A policy with
neither key is hierarchical, matching `hierarchical?`.

Foreign libraries are first-class nodes with edges to the modules that import
them, and the viewer draws them as ovals in every mode. At a drilled level,
edges that leave the current component are counted on the box as `↗out ↙in`
instead of disappearing.

Mutation grading follows the original when snapshots exist: `.metrics/mutate/*`
files are joined by namespace, pooled as killed / (killed + survived + gap), and
averaged with the CRAP grade. Without snapshots the box is graded by CRAP alone —
this pack has no Python mutation runner, so that half of his formula stays
dormant rather than painting everything red.

A policy with `packages` and `diagrams` selects the packaged branch, as his
does: each `diagrams` entry becomes one generated diagram — `{"view":
"overview"}` for one box per policy package plus an `Unassigned` box, or
`{"package": "<id>"}` for that package with its neighbour stubs. A policy with
neither key is hierarchical, matching `hierarchical?`.

Foreign libraries are first-class nodes with edges to the modules that import
them, and the viewer draws them as ovals in every mode. At a drilled level,
edges that leave the current component are counted on the box as `↗out ↙in`
instead of disappearing.

Mutation grading follows the original when snapshots exist: `.metrics/mutate/*`
files are joined by namespace, pooled as killed / (killed + survived + gap), and
averaged with the CRAP grade. Without snapshots the box is graded by CRAP alone —
this pack has no Python mutation runner, so that half of his formula stays
dormant rather than painting everything red. At a drilled level,
edges that leave the current component are counted on the box as `↗out ↙in`
instead of disappearing.

Mutation grading follows the original when snapshots exist: `.metrics/mutate/*`
files are joined by namespace, pooled as killed / (killed + survived + gap), and
averaged with the CRAP grade. Without snapshots the box is graded by CRAP alone —
this pack has no Python mutation runner, so that half of his formula stays
dormant rather than painting everything red.

`load` reads a hand-authored IR — EDN or JSON — and applies the same
normalization and range checks as the original: ids lowercased, `crap` as a
number or `{mu, max, sigma}`, coverage inside 0–1, unique class ids, and every
edge endpoint known. A document may hold one diagram or a stack under
`:diagrams`; the viewer renders them top to bottom, exactly as the original
does. Commands that inspect one diagram (`validate`, `ls`, `show`) use the
first, matching his `load-diagram`.

The viewer renders a static diagram as package boxes, exactly as a generated
hierarchical diagram renders as a namespace tree.

A policy with `packages` and `diagrams` selects the packaged branch, as his
does: each `diagrams` entry becomes one generated diagram — `{"view":
"overview"}` for one box per policy package plus an `Unassigned` box, or
`{"package": "<id>"}` for that package with its neighbour stubs. A policy with
neither key is hierarchical, matching `hierarchical?`.

Foreign libraries are first-class nodes with edges to the modules that import
them, and the viewer draws them as ovals in every mode. At a drilled level,
edges that leave the current component are counted on the box as `↗out ↙in`
instead of disappearing.

Mutation grading follows the original when snapshots exist: `.metrics/mutate/*`
files are joined by namespace, pooled as killed / (killed + survived + gap), and
averaged with the CRAP grade. Without snapshots the box is graded by CRAP alone —
this pack has no Python mutation runner, so that half of his formula stays
dormant rather than painting everything red.

`viewer.html` is one self-contained file: no server, no framework, no network.
Boxes are graded by CRAP; a dependency from an inner rank to an outer rank is a
violation. `python3 $PACK/tools/umlview/selftest.py` proves the rule and the
reader.

**Agents never read the model or the HTML.** They use `ls`, `show`, and
`policy`; the JSON is for the browser. That keeps a model of hundreds of
modules out of the context.

### Policy

The policy is the project entry's `umlview.policy`, relative to the project root,
and its output is `umlview.out`. Each project keeps its own policy, so one
project's module tree never leaks into another's diagram.
It contains only real namespace segments:

| Key | Role |
|---|---|
| `root` | Source tree to scan, relative to the project |
| `prefix` | Strip this from each module; the rest is the tree |
| `order` | Visual order of existing top-level segments |
| `levels` | Groups of segments, inner first. Rank is the group index |
| `foreign` | External libraries drawn as ovals |
| `edge_kinds` | Override `"from->to": "association"` |
| `omit_edges` | Drop `["from", "to"]` pairs entirely |
| `omit_edges` | Drop `["from", "to"]` pairs entirely |
| `omit` | Modules left off the diagram |
| `packages` | Packaged mode: named components over explicit namespace ids |
| `diagrams` | Packaged mode: one generated diagram per entry |
| `packages` | Packaged mode: named components over explicit namespace ids |
| `diagrams` | Packaged mode: one generated diagram per entry |

The dependency rule, copied from the original verbatim: a `dependency` edge
violates when both ends have a rank and the source rank is **strictly smaller**
than the target rank. Same rank is allowed; `association`, `implements`, and
every other kind is never compared; unranked and foreign ends are not compared;
a collapsed arrow keeps the flag if any bundled leaf dependency had it. Rank
lookup is the exact id, then the longest dotted prefix.

Grading is copied too: CRAP is pooled function-weighted as population μ and σ,
a box is graded by **μ + σ** through cutoffs `8 / 12 / 20` mapped linearly onto
`10 / 5.5 / 1`, and missing data counts as red (`20`) once per function. The
original averages that with a mutation grade; this pack has no mutation, so the
combined grade is the CRAP grade.

### Proposals and the design loop

A proposal is a named grouping of existing segments — a what-if architecture
that does not exist in the source. The viewer's context selector switches
between the real diagram and any proposal; `validate --proposal` checks one.

```sh
python3 $PACK/tools/umlview policy propose flow "source,stream_mux" "detector,tracker" "osd,rtsp_output"
python3 $PACK/tools/umlview validate --proposal flow     # exit 1 on a violation
```

The design loop, in the original's terms: after any source or policy change,
refresh metrics (`crapper`), then `scan`, then `render`. The human points at the
diagram and says what is wrong; the agent changes the policy or the code. There
is no mailbox here — the conversation is the mailbox.

## Not here

Mutation testing, Gherkin mutation, coverage gating, and any catalog or wrapper
CLI. They were removed deliberately; do not reintroduce them in a role prompt.

The vendored APS bundle still declares a `gherkin-mutator` task and ships its
spec. It is not part of this pack: do not run it.
