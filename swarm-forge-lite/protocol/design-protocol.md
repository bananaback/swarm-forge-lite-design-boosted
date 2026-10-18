# Design protocol

The design team turns an accepted requirement into a frozen module skeleton.
It writes three things a later role needs: requirements, interfaces, contracts.
Everything else is working state.

## Inputs and outputs

| Role | Input | Output |
|---|---|---|
| interrogator | ask, optional draft | `requirements.md`, spec doc, decisions |
| specifier | `requirements.md`, spec doc | `FEATURES/<name>.feature` |
| architect | requirements, feature | `architecture.md`, `model.json`, `model.html` |
| designer | one module row, its interface | `modules/<module>.md` |
| critic | architecture, all modules | `review.md`, `SKELETON.md` |

Generate `SKELETON.md` with `swarm.genRecord`. It concatenates the module
contracts and the review brief. Do not hand-copy a contract.

## Freeze

The freeze checklist is in `reference/module-rules.md`.

- Write sets are disjoint.
- The dependency graph is acyclic.
- Each module has one secret.
- Every caller is in the closure.
- Every shared edge has an interface section in `architecture.md`.
- Every acceptance check walks across the modules with no gap.

The architect freezes. Only the architect changes a frozen interface. A change is
`AMEND`, `REJECT`, or `REASSIGN`, one line each.

## Parallel split

Run designers in parallel only when all write sets are disjoint and all shared
edges are frozen. Otherwise serialize.

Each designer owns one `modules/<module>.md`. It never edits `architecture.md`,
`model.json`, or another module file.

## Decisions

A design-internal choice is a `DECISION` row in the file that owns it.

- One row per question.
- The question is one sentence.
- The options are concrete.
- The answer is `open` or the operator's answer.

`STATE: settled` requires zero open rows. A new DECISION makes `settled` illegal.
One decision round per module: batch the questions, ask once, then write the answers.

## Conflicts

A designer that cannot honor a frozen interface stops:

```
STATUS: blocked
CONFLICT: <interface path>:<line> - <new line> - <why>
```

The architect answers. Only consumers named in the changed interface are
re-dispatched. Cap the CONFLICT loop at 3 rounds, then report
`CONFLICT: unresolved` to the operator and stop.

## Scope gate

The interrogator records near-term use cases, expected scale, and out-of-scope
work before the specifier starts. The critic checks that every module earns its
keep. YAGNI is a valid answer, and it must name the excluded case.
