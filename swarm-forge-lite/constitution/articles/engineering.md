# Engineering

`<pack>` is the resolved pack root.

## Wiring
- Paths come from `harness.json`. Resolve them with `<pack>/tools/shared/harness.py status`.
- `workspace_root`: the project under work. `source_roots`: the test-free source. `persistent_tests`: the authored tests. `hot_tests`: the disposable generated area. `clean` removes it at a switch. `artifacts_root`: the reports and caches. `state_root`: the optional durable task state.
- `<pack>/PROJECT.md` is the operator-owned project `ENV` and `CONVENTIONS`. The orchestrator reads the file and cites the fields in the dispatch. `harness.py envelope <role> --subsystem <subsystem>` prints the cite block. The block holds every path and the `#STOP TEST` cite.
- Git: the worker roles run read-only git only (`status`, `log`, `diff`, `show`, `rev-parse`, `ls-files`, `grep`, and the like). The role policy denies every other git command. The orchestrator runs `git` directly. It commits or pushes when the operator asks.
- `SWARM_LANE` scopes `artifacts_root`, `hot_tests`, and `state_root` under the lane id. Run the commands through `<pack>/tools/shared/lane <id>`. That scopes bytecode, pytest cache, hypothesis, and temporary files too. The lane id is the SUBSYSTEM name, always. See **Concurrent Sessions**.

## Concurrent Sessions
- The **subsystem** is the unit of isolation. The **lane id is the subsystem name**. Every dispatch carries `LANE: <subsystem>`. Every shell command runs through `<pack>/tools/shared/lane <subsystem>`. Never run `pytest`, `ruff`, or any tool directly. The wrapper sets `SWARM_PACK`, `SWARM_LANE`, `SWARM_TEST_DATA`, `TMPDIR`, `PYTHONPYCACHEPREFIX`, `HYPOTHESIS_STORAGE_DIRECTORY` and `PYTEST_ADDOPTS`. A direct run loses `SWARM_PACK` and `SWARM_TEST_DATA`, and writes its caches into the source tree. The wrapper does not set `PYTHONPATH`: each test root sets its own imports in `pytest.ini`, and a `python3 -m <package>` tool needs its tree on `PYTHONPATH` by hand. Then the disposable roots are disjoint between subsystems.
- **One subsystem per session at a time.** The operator assigns the subsystem. Two sessions do not write to the same subsystem's record at the same time. There is no claim and no registry: the subsystem name is the lane.
- **One name everywhere.** The subsystem, the `LANE`, and `design/subsystems/<subsystem>/` are the same string. Never work in, nest, or rename another subsystem's directory.
- **The requirement document's number is fixed per subsystem.** `docs/specs/NN-<subsystem>.md` lives in a root that every subsystem shares. Take the next unused number when you create the subsystem's document; the subsystem keeps that number.
- **One session can hold more than one subsystem.** When the operator asks for two subsystems in one session, keep each subsystem on its own lane. The subsystems stay isolated from each other by their lanes.
- `harness.py status` prints `LANE` and every resolved path. Run it as the first tool call of a subsystem.
- **Clean in a lane.** `clean` resolves through the lane. Therefore `lane <subsystem> harness.py clean all` touches only that subsystem. Run `lane <subsystem> harness.py clean <target>`.
- **Commits.** The project under work is a git repository. Commit one at a time.
- **Cross-subsystem reads.** Read another subsystem's `design/subsystems/<subsystem>/` record once its work is settled, so a new subsystem does not re-derive the domain from scratch.

## Shared Files
- A task owns its own test-facing files: the feature `PERSIST/features/<name>.feature`, the acceptance step subsystem `PERSIST/acceptance/steps/<feature>.py`, and the unit and property tests. The tool finds the step subsystem by name. There is no registry to edit. Reuse the phrases of another feature with `REUSES = ("other_feature",)` in your own file.
- `PERSIST/conftest.py` stays frozen. The shared declared-class list is not needed there. A subsystem that needs its own declared class list writes `dump/<subsystem>/testdata/declared_classes.txt` (one name on each line). The `lane` wrapper points `SWARM_TEST_DATA` at that file. Then two subsystems declare different lists at the same time.
- Shared files: `harness.json`, `constitution/**`, `protocol/**`, `reference/**`, `design/templates/**`, `.opencode/agents/**`, the acceptance infrastructure (`run_acceptance.py`, `generator.py`, `runtime.py`, `doubles.py`, `steps/__init__.py`), and the two published `docs/README.md` files. Change a shared file when the work needs it.
- Publishing `docs/design-archive/` is an operator action and is serial.

## Startup Tools
- Python: install `coverage`, `hypothesis`, `tree-sitter`, `tree-sitter-language-pack`, and `ruff==0.16.9` with pip. CRAP: the vendored `<pack>/tools/refactorer/crapper`, run as `python3 -m crapper` (a package, not a binary). DRY: the vendored `<pack>/tools/shared/dryer`, run as `python3 -m dryer` with `<pack>/tools/shared` on `PYTHONPATH` (a package, not a binary). Lint: `<pack>/tools/shared/ruff4py`, run as `python3 <pack>/tools/shared/ruff4py` (a package directory, never as a binary and never as `python3 -m ruff4py`). The upstream ships no Python repo. These wrappers are the language tools.

## Language Defaults
- Python: `python3 -m pytest`, plain and non-interactive. Put hypothesis in a separate test root.

## Commands
Run from the workspace root.
- Tests: run through the lane wrapper, never directly: `<pack>/tools/shared/lane <subsystem> bash -c 'cd <persistent-root> && python3 -m pytest <paths or -k EXPR>'`. Run the full suite once at the terminal gate. For property tests only, append `property`. A direct `python3 -m pytest` lacks `SWARM_PACK` and `SWARM_TEST_DATA`, so it writes its caches into the source tree. The lane adds no `PYTHONPATH`: the root's `pytest.ini` sets `pythonpath` for the imports.
- Ruff: `python3 <pack>/tools/shared/ruff4py <source roots> <persistent roots>` (never pass `check`). `ruff4py` is a package directory, not an executable: always put `python3` in front, and never run `lane ... ruff4py` or `python3 -m ruff4py`. The wrapper pins the cache and injects no config; ruff finds `ruff.toml` beside each file. A clean tree reports 0 findings.
- Ruff format: `ruff format --check --cache-dir <pack>/dump/ruff-cache <source roots> <persistent roots>`. A clean tree reports 0 files to reformat.
- CRAP: the vendored `crapper` at `<pack>/tools/refactorer/crapper`, run as `python3 -m crapper` with `<pack>/tools/refactorer` on `PYTHONPATH`. Pass `--root <artifacts> --source-root <source> --threshold 10`. It runs coverage.py when no report is fresh, writes `.metrics/crap.edn` under the root, and exits 2 when the worst score is above the threshold. The pack's `swarm.crap` tool wraps it and keeps the CRAP 10 threshold.
- DRY: the vendored `dryer` at `<pack>/tools/shared/dryer`, run as `python3 -m dryer` with `<pack>/tools/shared` on `PYTHONPATH`. `dryer` is a package directory, not an executable; never run it directly. Pass `--root <artifacts> --threshold 0.82 --min-lines 4 --min-nodes 20`. It writes `.metrics/dry.edn` under the root. The pack's `swarm.dry` tool wraps it and keeps the DRY defaults.
- Gherkin: `<pack>/tools/shared/gherkin-parser <feature> <artifacts>/<stem>.json`. It is a bash script. Do not put `python3` in front of it.
- IR dry: `<pack>/tools/specifier/ir-dry-checker <ir> <artifacts>/<stem>.dry.json`. It is a bash script. Do not put `python3` in front of it.
- Acceptance: `python3 <persistent>/acceptance/run_acceptance.py [feature stem ...]` parses, dry-checks, generates into `hot_tests`, and runs the generated tests. Name a stem to scope the run. Omit the stem to run every feature at the terminal gate.
- Clean at a project switch: `<pack>/tools/shared/harness.py clean hot` (`state`, `artifacts`, `all`).

## Layout
- Source lives under `source_roots` and stays test-free. Authored tests: `persistent_tests/{unit,property,features,acceptance}`. Harness self-tests: `<pack>/harness_tests/persistent`. Generated tests: `<pack>/hot_tests`, disposable, never committed.
- File hygiene: keep every file short. Prefer several sibling files in a reasonable length over one long file, with the shared helpers in a `*_support.py`. There is no hard limit, and never over 600 lines. An acceptance step subsystem is a package of parts, one `HANDLERS` list each, joined in its `__init__.py`. Split a file in the same change that grows it.
- `artifacts_root` holds only reproducible artifacts. Deleting it or `hot_tests` must never delete a persistent test.

## Design
- Use small increments and the simplest design for the current behavior. Keep the tests close to the behavior.
- Separate the testable subsystems from the unsuitable subsystems (GUI, devices, environment and system errors, hangs). Maximize the testable code and minimize the module.
- An IO-near subsystem calls the domain subsystem. It never implements the answer of the domain subsystem again.
- Only the testable subsystems participate in the unit tests, the acceptance tests, CRAP, DRY, or the property tests.
- Keep the property tests separate. Do not put property tags in the unit or CRAP runs unless your role owns them.

## Requirement And Design Phase
- The **requirement record** runs first, before the specifier. The interrogator resolves the requirement document with the operator (refine a draft, or create `docs/specs/NN-<subsystem>.md`, and see `protocol/interrogator.md`). Then it frames the ask, makes the goal measurable, states the behavior as SCR tables, and discharges the cases that nobody stated. Then the **specifier** examines that record as a second party before it writes Gherkin.
- The **design method** runs between the specifier and the coder. It is `architect -> designer x N -> critic`. The operator gates a BUSINESS choice alone: a behavior, a constraint, an exclusion, or the scope. A role settles every design-internal choice itself, in its own `decisions.md` row.
  - Step index: `<pack>/protocol/design-procedure.md` (front end F1-F13, design steps 1-16).
  - Input, output, and working state: `<pack>/protocol/design-protocol.md`.
  - The freeze and the parallel split: `<pack>/reference/module-rules.md`.
  - Techniques: `<pack>/reference/design-craft-front.md`, `<pack>/reference/design-craft-design.md`.
  - Stop tests, ownership, and loop control: `<pack>/reference/design-quality.md`.
- These roles do not use the build envelope. Their input is the design dispatch (`#REQUEST`, `#DRAFT`, `#MODULE`, `#ACCEPTANCE`, `#FEATURES`, `#FROZEN`, `#INTERFACES`, `#STOP TEST`). Their output is a decision ledger plus filled forms. The architect keeps its sections and `ARCHITECTURE.md` in `<pack>/design/subsystems/<subsystem>/02-architect/`, and freezes one living file for each module in `<pack>/design/subsystems/<subsystem>/interfaces/`. A designer keeps its module in `<pack>/design/subsystems/<subsystem>/modules/<module>/`. The critic keeps its sections in `<pack>/design/subsystems/<subsystem>/04-critic/`. Each fills the record from `<pack>/design/templates/<role>/`. The role sections are the record; there is no separate artifact.
- The output is one durable record directory for each subsystem at `<pack>/design/subsystems/<subsystem>/`. It is never written into the project tree, and `harness clean` never removes it.
- Generate the visual view. Do not author it. The architect writes `design/subsystems/<subsystem>/model.json`. `tools/shared/umlview/render.py` turns it into a standalone `model.html` (reload with F5). The model and the rules are a port of the domain of `unclebob/uml-viewer`. The renderer reports the dependency-rule violation and the structural errors only. Format: `<pack>/reference/model-format.md`.
- Edit a section file in place, and add every row, entry, and section that the work needs. That is how the record grows. Write no bookkeeping about the edit: no version number, no status flag, no change log. The latest content of a file is its whole truth.
- The accepted `SKELETON` is the contract of the coder. The signatures, contracts, CQS tags, subsystem secrets, and the dependency graph are fixed before the bodies exist. The critic projects it into `design/subsystems/<subsystem>/SKELETON.md`, self-contained. The coder and the refactorer read that file.

## Acceptance
- APS: `gherkin-parser` + `ir-dry-checker`, Babashka, vendored unmodified at `<pack>/tools/shared/aps/`.
- Mutation (language or Gherkin) is out of scope. Meaningfulness = the acceptance suite + the property tests.
- Project acceptance components (generator, runtime, step handlers, scripts) live under the persistent test root. Generated entry points go to `hot_tests`.

## Verification
- Run the tools one at a time.
- Caches (`.pytest_cache`, `.hypothesis`, `.coverage`) and bytecode can appear in either tree. `.gitignore` covers them.
- Terminal gate (`refactorer`): DRY, then ruff check, then ruff format --check, then the full persistent suite, plus the acceptance runner. Then refresh the diagram (run `sync_python.py` and render the live model over `design/subsystems/<subsystem>/model.html` - the accepted `model.json` is not touched). Scope the tests to the chunk while you work. Run the full suite and every feature once, at this gate.
- Test-quality gate (`test-reviewer`): after the coder and before the refactorer, read the authored tests of the coder against `<pack>/reference/test-quality.md`. A `reject` sends the coder back until the tests are real. The coder does not grade its own work.
- Run the applicable local verification command before a handoff.
- Split a source file with more than one job.
- Scope CRAP to the subsystems under work. A function the coverage report does not mention scores 0%. An absent or failing baseline does not block.
