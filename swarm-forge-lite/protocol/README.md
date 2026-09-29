# Protocol

How the pipeline talks. Two protocols: the build loop (`specifier`, `coder`,
`refactorer`) uses `dispatch.md` and the build answer fields; the requirement and design
roles (`interrogator`, `modeler`, `contractor`, `critic`) use `design-protocol.md`, where
the method's filled artifacts are the message. The orchestrator is the only caller: it
invokes one role at a time with the opencode `subagent` tool and reads that role's final
message as the result. A role runs as a subagent and never calls
`subagent` itself; it answers with its template, and the orchestrator dispatches the
role named by `NEXT`.

## Calling a role

`subagent` with:

- `agent`: the role id (`specifier`, `interrogator`, `modeler`, `contractor`, `critic`, `coder`, `test-reviewer`, `refactorer`).
- `prompt`: the message from `dispatch.md` for build roles; for the interrogator and the design roles, the dispatch from `design-protocol.md`. `dispatch.md` is the build loop's envelope; those roles speak the method's artifacts, not `VERIFY`/`FILES`.
- `sessionID`: omit it to start a fresh child session; pass the id returned by an earlier call to resume it. Resume by default — that keeps the role's context and is the cache hit. Start fresh when resuming would mislead the role: a new task, a session that drifted or contradicts itself, a prompt or protocol revision it never read, or the operator asking for a clean pass. Neither is forbidden; say why when you start fresh. A concurrent chunk is a lane: one `sessionID` per lane, run through `<pack>/tools/shared/lane` so its roots, caches, bytecode, and temp files are disjoint.

The result is the callee's final message. Only the orchestrator passes `sessionID`.
The dispatch envelope carries `ENV` and `CONVENTIONS` alongside the chunk brief, and
places `INBOUND` before `BRIEF` so the role reads the ask last. `ENV` and
`CONVENTIONS` come from `<pack>/PROJECT.md` (operator-owned); the orchestrator reads
them and asks once only when a field is missing.

## Answering

End your turn with the message from your role template:

| Role | Template |
|---|---|
| specifier | `specifier.md` |
| interrogator | `interrogator.md` |
| modeler | `modeler.md` |
| contractor | `contractor.md` |
| critic | `critic.md` |
| coder | `coder.md` |
| test-reviewer | `test-reviewer.md` |
| refactorer | `refactorer.md` |

## The pipeline

```
intent  ->  interrogator  --STATE: settled-->  specifier  --APPROVED: yes-->  [design gate: modeler -> contractor -> critic]  --SKELETON accepted-->  coder  ->  test-reviewer  ->  refactorer
```

The **interrogator** runs first, on the operator's ambiguous ask. It resolves the requirement
document with the operator — a draft requirement (`docs/specs/NN-*.md`) is read and refined, and
when none exists the interrogator creates `docs/specs/NN-<task>.md` — so the doc is a deliverable
of the gate, before the specifier. A draft, when it exists, is an input, never an authority. It
frames the ask, makes the goal
measurable, states the behaviour as SCR tables, discharges the cases nobody stated, and ends at
`STATE: settled` only after the operator answers its `[DECISIONS]`. The **specifier** then
inspects the accepted record as a second party and derives Gherkin with one scenario per
requirement; a defect routes back to the interrogator, never forward. Its approval opens the
**design gate**: the automatic chain stops and the operator-gated design team runs under
`design-protocol.md`. Each design role ends at `STATE: settled` only after the operator
answers its `[DECISIONS]` at the role's own `question` gate; the orchestrator only sequences
and surfaces. Each role keeps its full state in `design/<task>/work/<nn>-<role>.md` and
projects the accepted sections into `BLUEPRINT.md`. The critic's accepted `SKELETON` gates the
handoff to the coder. The method is `design-procedure.md` (step index), `design-protocol.md` (I/O and state), `reference/design-craft-front.md` and `reference/design-craft-design.md`, and `reference/design-quality.md` (stop tests); the empty forms are under `design/templates/`.

Never call `subagent` from a role. `NEXT` names the role the orchestrator dispatches
next, not a role the role itself calls.

Each template ends with `ASSUMPTIONS:` — record any non-blocking default you took,
or `none`. Assumptions are informational and never block the chain.

## The dispatch rule

The orchestrator makes exactly one decision per returned message:

| Returned message | Orchestrator action |
|---|---|
| `STATUS: done` with `VERIFY` evidence (build roles) or `STATE: settled` (requirement and design roles) | dispatch the role named by `NEXT` |
| `STATUS: blocked` or `needs-input` (build), `STATE: blocked` (requirement and design) | do not advance; surface `ASK`/`OPEN RISKS` to the operator and stop |
| interrogator with `STATE: settled` | dispatch the specifier; no design role is next |
| specifier with `APPROVED: no` | do not dispatch the modeler |
| specifier with `APPROVED: yes` | open the design gate; dispatch the modeler; the coder is not next |
| design role with `STATE: settled` | dispatch the role named by `NEXT` |
| design role with `STATE: open` or `blocked` | do not advance; surface the pending `DECISIONS` or `OPEN RISKS` and stop |
| critic with `STATE: settled` | surface the accepted-skeleton gate, then dispatch the coder only on Proceed |
| test-reviewer with `VERDICT: accept` | dispatch the role named by `NEXT` (refactorer) |
| test-reviewer with `VERDICT: reject` | re-dispatch the coder with the `FINDINGS` as the brief; loop until accept |
| missing or contradictory fields | re-dispatch the same role once for a corrected message; if still malformed, escalate |
| `NEXT` absent or unknown | escalate; never guess |
| `ASSUMPTIONS:` present | informational; carry it forward and never block |
| operator answers `Stop` at a gate | stop the run |

A `blocked` message never advances the chain, even when it carries a `NEXT` line.
On a `blocked` message that names an `ENV`/`CONVENTIONS` conflict, the orchestrator
asks the operator, updates `<pack>/PROJECT.md`, then re-dispatches.

## Terminal gate

The refactorer ends the chain: `NEXT: operator` when the terminal gate (DRY,
ruff, the full persistent suite, the acceptance runner) passes. The orchestrator
relays the verdict and stops. On a failing gate the refactorer reports
`STATUS: blocked` with `ASK` naming the failure; the orchestrator surfaces it to
the operator and does not advance.

## Committing

The operator owns commits. A role commits or pushes only when the operator
explicitly asks, using the operator's message or the Angular form in
`workflow.md`. Never commit unrelated changes or generated artifacts. Handing
off never waits for, requires, or references a commit. Leave the tree for the
next role.

## Editing

These files are plain text. Change a field name, add a line, or delete one here and
every role picks it up on its next turn. Keep the field names stable: another role
reads them, and a missing field is a silent bug.
