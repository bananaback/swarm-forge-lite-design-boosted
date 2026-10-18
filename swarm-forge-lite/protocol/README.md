# Protocol

One pipeline. Nine worker roles. A hotfixer fast path.

```
operator
  -> interrogator   requirements.md + docs/specs/NN-<subsystem>.md
  -> specifier      FEATURES/<name>.feature + Gherkin check
  -> architect      architecture.md + model.json
  -> designer x N   modules/<module>.md        (parallel)
  -> critic         review.md + SKELETON.md     (adversarial union)
  -> coder          source + tests + acceptance step
  -> test-reviewer  VERDICT accept | reject
  -> refactorer     terminal gate
  -> operator
```

## Gates

| Gate | Pass condition |
|---|---|
| requirement | `swarm.ready({role:'interrogator',subsystem})` |
| specifier | parse + dry-check clean; operator `APPROVED: yes` |
| architect | `swarm.ready({role:'architect',subsystem})`; interfaces frozen |
| designer | `swarm.check`; contracts complete; red test per acceptance check |
| critic | union review; `swarm.genRecord`; operator Proceed |
| coder | red for the right reason, then green; ruff clean |
| test-reviewer | `VERDICT: accept` |
| terminal | `swarm.gate({subsystem,feature,crap:true})` |

## Durable outputs

- `docs/specs/NN-<subsystem>.md` — shipped requirement document.
- `FEATURES/*.feature` — shipped behavior.
- `design/subsystems/<subsystem>/model.html` — review page, generated.
- `design/subsystems/<subsystem>/model.json` — topology, tool-edited.
- Source code and authored tests.

Everything else in the record is working state. Keep it short. Do not ship it.

## Roles

| Role | Reads | Writes |
|---|---|---|
| orchestrator | operator, `GOAL.md` | `GOAL.md`, dispatch |
| interrogator | ask, draft, `requirements.md` | `requirements.md`, spec doc |
| specifier | `requirements.md`, spec doc | feature |
| architect | `requirements.md` | `architecture.md`, `model.json` |
| designer | `architecture.md`, one module map row | `modules/<module>.md` |
| critic | `architecture.md`, all modules | `review.md`, `SKELETON.md` |
| coder | `SKELETON.md`, feature | source, tests, step handler |
| test-reviewer | tests, contracts, feature | one review report |
| refactorer | `SKELETON.md`, source, tests | code, tests, `model.json` overlay |
| hotfixer | symptom, source, tests | one fix, tests, step handler |

## Change classes

- `contained` -> hotfixer alone.
- `module-internal` -> affected designer, critic, coder, test-reviewer, refactorer.
- `module-cut` -> architect first, then the build loop.
- `requirement-level` / `new-subsystem` -> full chain.

The class comes from the change. Never escalate without a business effect.

## Parallel design

Designers run in parallel only when:

- every write set is disjoint;
- every shared edge is frozen in `architecture.md`;
- each designer uses lane `<subsystem>.<module>`.

A designer that cannot honor a frozen interface reports
`STATUS: blocked` and `CONFLICT: <path>:<line> - <new line> - <why>`.
The architect answers `AMEND`, `REJECT`, or `REASSIGN`. Only named consumers are
re-dispatched.

## Frozen zone

- The `## Interface <module>` sections in `architecture.md`.
- The accepted contracts in `modules/<module>.md` and `SKELETON.md`.

A change to either is `module-cut`. The coder implements bodies; it does not
renegotiate a contract.

## Evidence

Every role ends with:

```
STATUS: done | blocked
FILES: path:line, ...
VERIFY: <exact command> => exit <n>
NEXT: <role> | operator
```

A green claim without `VERIFY` is thin. The refactorer's terminal message ends the run.
