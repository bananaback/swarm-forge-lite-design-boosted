# Uncle Bob's SwarmForge Workflow — Concepts

## Roles

| Phase | Owns | Tools |
|---|---|---|
| Interrogator | the requirement record: measurable goal, SCR behaviour tables, constraint ledger, exclusions, traceability | `question` |
| Specifier | observable behavior, acceptance criteria, examples; second-party inspection of the record | `gherkin-parser`, `ir-dry-checker`, `question` |
| Modeler | CRC cards, secrets, core/shell map, dependency graph, state map | `question` |
| Contractor | method contracts, CQS tags, test map | `question` |
| Critic | extension rehearsal, substitutability, final skeleton | `question` |
| Coder | production code + focused unit tests + acceptance pipeline | `gherkin-parser`, `run_acceptance.py`, `pytest`, `ruff4py` |
| Test reviewer | test quality against the craft rubric — behavioral, deterministic, specific oracle, mutation-honest | `pytest` |
| Refactorer | names, duplication, cohesion, coverage, property tests, boundaries, terminal gate | `crap4py` (reports coverage), `dry4py`, `ruff4py`, `run_acceptance.py`, `pytest` |
| Hotfixer (standalone) | an urgent change in one session — reproduce, fix minimally across whatever layers it touches, keep them consistent and green | `pytest`, `run_acceptance.py`, `ruff4py` |

## Requirement Record, Then Design

The front end runs before the specifier; the design team runs after it. The operator gates every
checkpoint. Method index: `protocol/design-procedure.md` (front-end index F1–F13, design steps
1–15). Protocol (input dispatch, output answer, working state): `protocol/design-protocol.md`.
Techniques: `reference/design-craft-front.md` and `reference/design-craft-design.md`. Stop tests and ownership: `reference/design-quality.md`.
Empty forms: `design/templates/`. Output: the accepted `design/<task>/BLUEPRINT.md` plus each
role's full state under `design/<task>/work/`, and a visual `design/<task>/model.json` →
`model.html` rendered by `tools/shared/umlview/render.py` (format: `reference/model-format.md`).
These roles do not use the build envelope: their input is `REQUEST` + `ACCEPTANCE`, their output
is a decision ledger plus filled forms, and their proof is a stop test, not a `VERIFY` command.

- **Interrogator** — Runs first, before the specifier. It resolves the requirement document with
  the operator before framing: an existing draft (`docs/specs/NN-*.md`) is read and refined, and
  when none exists the interrogator creates `docs/specs/NN-<task>.md` — the doc is a deliverable of
  the gate, one-to-one with the record. A draft is an input, never an authority. Steps: frame the ask (the perfect-technology filter; the
  context-free questions); make the goal measurable (Scale/Meter/Target); refine goals AND/OR
  (KAOS) and give every top goal an anti-goal; fix the variables (monitored, controlled, input,
  output); state the behaviour as SCR tables (mode transition, event, condition) and check
  **completeness and disjointness**; one row per goal leaf, each with one EARS pattern and one
  verification method; classify every constraint and list the exclusions; discharge every obstacle
  and misuse case; build the traceability matrix. Outputs: `GOAL`, `CONSTRAINTS`, `EXCLUSIONS`,
  `REQUIREMENTS`, plus the requirement document at `docs/specs/NN-<task>.md` — refined when a draft
  existed, created when none did. Its stop test is a zero-count rubric, not a judgement.
- **Specifier (inspection)** — reads the accepted record as a second party and re-runs those
  counts. A defect is a `[REVISION REQUEST]` back to the interrogator, never new Gherkin.
- **Modeler** — Inputs: accepted goal/constraints/exclusions. Steps: Abbott noun-verb
  analysis; CRC cards; one secret per card (Parnas); core/shell tagging; dependency
  inversion; SRP; state/ordering pass. Outputs: `CRC_CARDS`, `SECRETS`, `CORE_SHELL_MAP`,
  `DEPENDENCY_GRAPH`, `STATE_MAP`.
- **Contractor** — Inputs: accepted cards/secret/core-shell/dependency/state. Steps:
  pre/post/invariant per method; one Command/Query tag; Tell-Don't-Ask and Law-of-Demeter
  rewiring; the passes-the-tests gate. Outputs: `CONTRACTS`, `TEST_MAP`.
- **Critic** — Inputs: accepted contracts/test map. Steps: OCP extension rehearsal;
  LSP/ISP checks; dedup and minimalism (caller closure); reveals-intention naming.
  Outputs: `SKELETON` in the record, plus `SKELETON.md` — the implementation contract the coder and the refactorer read.

## Specifier
- **Inputs:** the accepted requirement record (the interrogator's); the operator's ask.
- **Steps:**
  1. Inspect the record as a second party — the author does not inspect their own record: re-run the stop-test counts and confirm every requirement carries a verification method. A defect is a `[REVISION REQUEST]` routed to the interrogator, not new Gherkin.
  2. Ask questions to settle ambiguity.
  3. Write deterministic Gherkin in the APS format, separated by behavior and technology; externally visible behavior only; one behavior per scenario, each named for the outcome it pins with a name unique within the feature (the ordinal is a convenience, the name is the durable handle). Every scenario names the Rn it pins.
  4. Make every value that might vary a parameter; bind every placeholder to an example column and delete any column no step reads; prune identical example columns that add no value; move repeated setup into `Background`.
  5. Cover the failures as well as the happy path (Cockburn): walk the main success path step by step and, at each step, enumerate what can go wrong there.
  6. `gherkin-parser` → canonical IR.
  7. `ir-dry-checker` → normalize/prune, dry report.
  8. Operator approves via `question`.
  9. Run tests only when verification is needed.
- **Outputs:** approved feature + IR + dry report; approval opens the design gate (next: modeler, never the coder).

## Coder
- **Inputs:** approved feature + IR + the accepted `SKELETON` (method name, contract, responsibility sentence).
- **Steps:**
  1. Implement in the project language from the constitution, starting from the latest accepted spec.
  2. Write focused unit tests that would fail for a plausible wrong implementation.
  3. Write only enough production code to pass; run `pytest`.
  4. Use the APS `gherkin-parser` (prefer Babashka); build the generator, runtime, step handlers, and scripts; `run_acceptance.py` generates and runs acceptance tests.
  5. Default to regex-capture step handlers, one per repeated step shape; literal handlers only for genuinely different behavior.
  6. `ruff4py`; clear names, straightforward control flow, no avoidable duplication; leave broad cleanup to the refactorer unless it blocks the slice.
  7. Run property tests only when explicitly requested.
- **Outputs:** implementation + unit tests + step handlers; unit and acceptance green.

## Refactorer
- **Inputs:** green implementation + tests.
- **Steps:**
  1. Move behavior out of environmentally unsuitable modules into testable ones; keep unsuitable modules as small adapter shells.
  2. `crap4py` first: ≤ 10 per function; a single dispatch answering one question may exceed; nested or mixed-duty functions must split; an extract owns its inputs.
  3. `dry4py`: remove duplication.
  4. Raise coverage as crap4py reports it; add property tests where undercovered (invariants, ranges, round trips, conservation, idempotence, ordering, parse/format stability); adopt a framework or build a small one; run property tests as a separate explicit command.
  5. Split a file with more than one job before handoff.
  6. Terminal gate, one tool at a time, fixing each before the next: `dry4py` → `ruff4py` → full `pytest` suite (property separately) → `run_acceptance.py`.
- **Outputs:** same behavior, lower CRAP/DRY, higher coverage; terminal gate green.

## Verification
- A passing test is a hypothesis, not evidence. The coder does not grade its own work; the refactorer's terminal gate is the final verification.
- Every role reports `ASSUMPTIONS:` (the non-blocking defaults it took) or `none`; assumptions never block the chain.
- Acceptance pipeline: Gherkin → canonical IR → generated executable tests → runtime with step handlers.
- CRAP ≤ 10 per function; a single dispatch answering one question may exceed; nested or mixed-duty functions must split.
- crap4py's report carries coverage; there is no separate coverage command. DRY and property tests run separately; property tags stay out of normal unit runs unless the role owns property verification.
- Run one tool at a time; acceptance generation and acceptance runs stay sequential; avoid whole-suite test runs concurrent with acceptance generation.
- Prefer project-local cache and configuration paths.
- Run the local verification command before handoff; the refactorer's terminal gate re-runs DRY, ruff, the full suite, and the acceptance runner.

## Design And Testability
- Maximize testable code; minimize the environmentally unsuitable boundary (GUIs, devices, environment errors, system errors, hangs).
- Only testable modules participate in unit tests, acceptance, coverage, CRAP, or test-invoking DRY.
- IO-near modules must not reimplement a domain question; call the high-level module and translate the result.
- A high-level module that exists only for tests while an adapter reimplements it is a defect.
- Dependency rule: high-level modules far from IO must not depend on low-level modules near IO.
- Keep tests close to the behavior; work in small increments; prefer the simplest design that leaves clear options for the next step; keep tests separate from test helpers.

## Startup And Tools
- Procure the latest CRAP and DRY tools from upstream; do not rely on stale cached, vendored, or preinstalled copies.
- The APS supplies `gherkin-parser` and `ir-dry-checker`; install them with the project-local helper, never by searching `$HOME` or running `find`.

## Epistemics
- Do not pin prompt prose with automated tests; test observable runtime behavior.
- No local proxies for CRAP, DRY, or coverage.
- Inspect local help or project documentation before relying on an unfamiliar command.
