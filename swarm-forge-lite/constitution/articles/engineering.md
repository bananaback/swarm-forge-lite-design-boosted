# Engineering

`<pack>` is the resolved pack root.

## Wiring
- Paths come from `harness.json`; resolve them with `<pack>/tools/shared/harness.py status`. Never hardcode.
- `workspace_root`: project under work. `source_roots`: test-free source. `persistent_tests`: authored tests. `hot_tests`: disposable generated area, cleaned on switch. `artifacts_root`: reports and caches. `state_root`: optional durable task state.
- `<pack>/PROJECT.md` is the operator-owned project `ENV`/`CONVENTIONS`; the orchestrator reads it and roles do not.
- `SWARM_LANE` scopes `artifacts_root`, `hot_tests`, and `state_root` under the lane id; run commands through `<pack>/tools/shared/lane <id>` to scope bytecode, pytest cache, hypothesis, and temp files too, so concurrent lanes share no disposable file.

## Startup Tools
- Go: `go install` `crap4go`, `dry4go`. Clojure: deps.edn `crap4clj`, `dry4clj`. Java: `mvn` `crap4java`, `dry4java`.
- Python: pip `radon`, `coverage`, `hypothesis`, `ruff`, plus `npm i -g jscpd@5`; CRAP `<pack>/tools/refactorer/crap4py`, DRY `<pack>/tools/shared/dry4py`, lint `<pack>/tools/shared/ruff4py`. Upstream ships no Python repo; these wrappers are the language tools.

## Language Defaults
- Python: `python3 -m pytest`, plain, non-interactive; hypothesis in a separate test root.
- Clojure: prefer Babashka; Speclj, not `clojure.test`.
- Java: no Maven test runs; build dedicated runners.
- Never search `$HOME` or run `find` for binaries; use project tooling.

## Commands
Run from the workspace root. Wrappers only: never call `ruff`, `radon`, `jscpd`, or `coverage` directly. One quality tool at a time; use `--workers 4` / `--max-workers 4`.
- Tests: `cd <persistent-root> && python3 -m pytest <paths or -k EXPR>` while working; the full `python3 -m pytest` once at the terminal gate; property only: append `property`.
- Ruff: `<pack>/tools/shared/ruff4py <source roots> <persistent roots>` (never pass `check`).
- CRAP: `<pack>/tools/refactorer/crap4py --source-root <source> --test-path <persistent tests>`. It runs coverage.py; there is no separate coverage command.
- DRY: `<pack>/tools/shared/dry4py --min-lines 4 <source roots>`.
- Gherkin: `<pack>/tools/shared/gherkin-parser <feature> <artifacts>/<stem>.json`.
- IR dry: `<pack>/tools/specifier/ir-dry-checker <ir> <artifacts>/<stem>.dry.json`.
- Acceptance: `<persistent>/acceptance/run_acceptance.py [feature stem ...]` parses, dry-checks, generates into `hot_tests`, and runs the generated tests; name a stem to scope, omit for every feature at the terminal gate.
- Clean on project switch: `<pack>/tools/shared/harness.py clean hot` (`state`, `artifacts`, `all`).

## Layout
- Source lives under `source_roots` and stays test-free. Authored tests: `persistent_tests/{unit,property,features,acceptance}`; harness tool tests: `<pack>/harness_tests/persistent/tools`. Generated tests: `<pack>/hot_tests`, disposable, never committed.
- Never create project source in the pack; never write tests into source roots.
- `artifacts_root` holds only reproducible artifacts. Deleting it or `hot_tests` must never delete a persistent test; never delete `<pack>/harness_tests/persistent/`.

## Design
- Small increments; the simplest design for the current behavior; tests close to the behavior.
- Separate testable modules from unsuitable ones (GUI, devices, env/system errors, hangs). Maximize testable code, minimize the boundary.
- IO-near modules call the domain module; never reimplement its answer.
- Only testable modules participate in unit tests, acceptance, CRAP, DRY, or property tests.
- Property tests stay separate; no property tags in unit/CRAP runs unless the role owns them.

## Requirement And Design Phase
- The **requirement record** runs first, before the specifier: the interrogator frames the ask, makes the goal measurable, states the behaviour as SCR tables, and discharges the cases nobody stated. It resolves the requirement document with the operator first: an existing draft (`docs/specs/NN-*.md`) is refined, and when none exists the interrogator creates the doc — a deliverable of the gate, one-to-one with the record. A draft is an input, never an authority. The **specifier** then inspects that record as a second party before writing any Gherkin.
- The **design method** runs between the specifier and the coder. Every checkpoint of both phases is operator-gated. Method: `<pack>/protocol/design-procedure.md` (front-end index F1–F13, design steps 1–15); input dispatch, output answer, and working state: `<pack>/protocol/design-protocol.md`; techniques: `<pack>/reference/design-craft-front.md` and `<pack>/reference/design-craft-design.md`; stop tests, ownership, and loop control: `<pack>/reference/design-quality.md`.
- These roles do not use the build envelope. Their input is the design dispatch (`#REQUEST`, `#DRAFT`, `#ACCEPTANCE`, `#FEATURES`, `#FROZEN`, `#ASK`, `#STOP TEST`); their output is a decision ledger plus filled forms. Each role keeps full state in `<pack>/design/<task>/work/<nn>-<role>.md`, filled from `<pack>/design/templates/<role>.md`, and projects only the accepted sections into `BLUEPRINT.md`.
- Output is one durable blueprint per task at `<pack>/design/<task>/BLUEPRINT.md`; it is never written into the project tree and is never cleaned by `harness clean`.
- A visual view is generated, not authored: the modeler writes `design/<task>/model.json`, `tools/shared/umlview/render.py` turns it into a standalone `model.html` (reload with F5). The model and rules are a port of `unclebob/uml-viewer`'s domain; the renderer reports the dependency-rule violation and the structural errors only. Format: `<pack>/reference/model-format.md`.
- Design roles append only their own sections. An accepted section is immutable; a later change is a `[REVISION REQUEST]` line that increments REV and marks the changed span. No revision log is kept — the artifact is the record.
- The accepted `SKELETON` is the coder's contract: signatures, contracts, CQS tags, module secrets, and the dependency graph are fixed before bodies exist. The critic projects it into `design/<task>/SKELETON.md`, self-contained, and that file is the coder's and the refactorer's brief.
- The coder implements to the skeleton; the refactorer cleans up within it and never redesigns across an accepted module secret.

## Acceptance
- APS: `gherkin-parser` + `ir-dry-checker`, Babashka, vendored unmodified at `<pack>/tools/shared/aps/`; do not fetch the Go fallbacks.
- Mutation (language or Gherkin) is out of scope. Meaningfulness = acceptance suite + property tests.
- Project acceptance components (generator, runtime, step handlers, scripts) live under the persistent test root; generated entrypoints go to `hot_tests`.

## Verification
- Run tools one at a time; never CRAP/DRY/ruff concurrently.
- Acceptance generation and runs sequential; no whole-suite test run concurrent with acceptance generation.
- Caches (`.pytest_cache`, `.hypothesis`, `.coverage`) and bytecode may appear in either tree; `.gitignore` covers them, so there is no leak check.
- Terminal gate (`refactorer`): DRY then ruff then the full persistent suite, plus the acceptance runner. Scope tests to the chunk while working; the full suite and every feature run once, at this gate.
- Test-quality gate (`test-reviewer`): after the coder and before the refactorer, the coder's authored tests are audited against `<pack>/reference/test-quality.md`; a `reject` sends the coder back until the tests are real. The coder does not grade its own work; the reviewer writes nothing.
- Run the relevant local verification command before handing off.
- Split a source file with more than one job; do not split a one-job module to chase a count.
- Scope CRAP to the modules under work; a function without coverage is reported `unmeasured`; an absent or failing baseline does not block.

## Guardrails
- No project-local CRAP/DRY/coverage proxies; use the wrappers.
- Never edit a `VERIFY` command, a test, or a feature to make a check pass; a passing check earned by editing the check is a defect.
- Never pin prompt prose (role prompts, the constitution, generated instruction files) with an automated unit or acceptance test; test observable runtime behavior only.
- Do not commit unrelated changes or generated artifacts.
- Inspect local help or docs before an unfamiliar command.
