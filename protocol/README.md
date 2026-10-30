# Protocol

One orchestrator. Six roles. One rule for deciding what runs.

```text
operator
  -> orchestrator   decide, dispatch, report
  -> designer       note: intent + class design
  -> specifier      .feature from the note
  -> coder          acceptance pipeline + implementation
  -> test-reviewer  verdict on the tests: accept or reject
  -> refactorer     coverage, property tests, CRAP, DRY
  -> architect      boundaries + terminal gate
  -> operator
```

## Order

- **New or changed behavior:** designer → specifier → coder → test-reviewer → refactorer → architect.
- **Structure only, behavior unchanged:** refactorer → architect.
- **Local fix, no behavior change:** coder → test-reviewer → architect.
- **Design review, or "show me this another way":** designer, alone. The
  designer owns the views as well as the note; there is no second design role.

A one-line fix stays one-line work: it never runs the designer or the specifier, and the operator
is not asked to approve a specification that did not change.

## Gates

| Gate | Owner | Pass condition |
|---|---|---|
| design note | designer | two headings, self-check yes, under 30 lines |
| specification | specifier | `gherkin-parser` clean, `gherkin-ir-dry-checker` clean; operator approves note + feature |
| implementation | coder | red test first, then green; unit and acceptance pass; ruff clean |
| tests | test-reviewer | verdict accept; both runs exit 0; every changed test has an oracle and a named wrong implementation |
| structure | refactorer | tests still pass; worst CRAP ≤ 10; `dryer` exits 0 at `--threshold` |
| design views | designer | the changed view renders; the spec's `## Classes`/`## Flow` are current; `arch classes validate`, `arch runtime validate` or `arch docs validate` exits 0 |
| terminal | architect | ruff, format, DRY, unit, acceptance, CRAP, `arch classes validate`, `arch runtime validate` — all pass |

The orchestrator accepts a gate from the role's report. The architect re-runs
the terminal gate in full, so the pack always ends with one verified command
set rather than five claims.

## Roles

| Role | Owns | Writes |
|---|---|---|
| orchestrator | deciding the chain, dispatch, operator contact | nothing in the project |
| designer | intent, class design, spec, policy, proposals, design views | `<PROJECT>/<docs_root>/specs/NN-*.md`, `<PACK>/architecture/{runtime,design}.json`, rendered views |
| specifier | behavior and acceptance criteria | `*.feature` |
| coder | acceptance pipeline, implementation, unit tests | source, tests, generated acceptance |
| test-reviewer | the verdict on the tests; what a green suite actually proves | nothing — findings only, under the artifacts root |
| refactorer | coverage, property tests, duplication, complexity | source, tests |
| architect | module boundaries, dependency direction, terminal gate | source, tests |

## Reporting

Each role ends with a short prose report: files changed, the exact commands it
ran with their exit status, and what should happen next. The orchestrator
accepts a gate only when the report names the command it expects.

## Deliberately Absent

- **Mutation testing**, language and Gherkin. Cost outweighed the signal.
- **Worktrees, tmux, daemons, dashboards, boards.** Roles are sequential and the
  platform already provides messaging.
- **A durable design record.** The specification is the feature file, the
  architecture is the code, and the history is git.
- **Coverage-chasing tests.** The reviewer rejects a test whose only proof is
  that a call happened; a green suite without oracles is not evidence.
