# Protocol

Two protocols. The build loop (`specifier`, `coder`, `test-reviewer`, `refactorer`,
`hotfixer`) uses `dispatch.md`.
The requirement and design roles (`interrogator`, `architect`, `designer`, `critic`)
use `design-protocol.md`. The orchestrator dispatches one role per `subagent` call and
reads its final message. A role answers with its template. The orchestrator dispatches
the role named by `NEXT`.

## Call a Role

`subagent`:
- `agent`: the role id.
- `prompt`: the message from `dispatch.md` for a build role, or the dispatch from `design-protocol.md` for the interrogator and the design roles.
- `sessionID`: omit to start. Pass the returned id to continue. Continue by default; start a new session only when a continued session would mislead (`communication.md`, Calling). One session for each lane. Run it through `<pack>/tools/shared/lane`, so its roots, caches, bytecode, and temporary files stay disjoint.

The result is the final message of the callee.

Every dispatch carries `LANE: <subsystem>`. A parallel designer uses the lane
`<subsystem>.<module>`, so two modules never share a disposable file. The operator
assigns the subsystem; there is no claim registry.

The envelope carries `ENV` and `CONVENTIONS` with the chunk dispatch, and puts
`INBOUND` before the ask, so the role reads the ask last. `ENV` and `CONVENTIONS` come
from `<pack>/PROJECT.md` (operator-owned). Ask once only when a field is missing.

## Answer

End your turn with the block of your role template, with no preface and no trailing
prose. The template is shared: never edit it. Print it with your own values.

Format it for a human reader: one field on each line, a blank line between the field
groups, and each DECISION on its own line, indented. Do not pack two fields on one line.

| Role | Template |
|---|---|
| specifier | `specifier.md` |
| interrogator | `interrogator.md` |
| architect | `architect.md` |
| designer | `designer.md` |
| critic | `critic.md` |
| coder | `coder.md` |
| test-reviewer | `test-reviewer.md` |
| refactorer | `refactorer.md` |
| hotfixer | `hotfixer.md` |

Each template ends with `ASSUMPTIONS:`. Record each non-blocking default, or write
`none`. Assumptions never block the chain.

## Code Mode (`execute`)

Inside `execute` (the Code Mode sandbox), only `tools.convo.*`, `tools.swarm.*`, and `tools.opencode.*` exist. The tools `read`, `shell`, `glob`, `grep`, and `codegraph_explore` are top-level tools; they are not available inside `execute`. Code Mode is a JavaScript sandbox: it has no `require`, no `fs`, and no Node.js. Use `shell` (a top-level tool) for filesystem access, and use `tools.*` for conversation, swarm, and opencode access. Do not write Python inside `execute`; it is JavaScript only.

## The Pipeline

```
intent -> interrogator --STATE: settled--> specifier --APPROVED: yes--> architect
       --STATE: settled--> [designer x N, IN PARALLEL] --> critic --SKELETON accepted-->
       coder -> test-reviewer -> refactorer
```

The **interrogator** runs first. It resolves the requirement document with the
operator (refine a draft, or create `docs/specs/NN-<subsystem>.md`), frames the ask,
makes the goal measurable, states the behavior as SCR tables, and discharges the cases
nobody stated. It reaches `STATE: settled` only after the operator answers its DECISIONS.

The **specifier** examines the accepted record as a second party, and derives one
Gherkin scenario for each requirement. A defect routes back to the interrogator, never
forward. Its approval opens the design gate.

The **architect** cuts the subsystem into modules and freezes the interfaces. It
returns `ARCHITECTURE.md` and one living interface file for each module. The operator
gates it. Then the orchestrator splits the module map and dispatches one **designer**
for each module, in parallel. A designer returns `STATE: settled`, `STATE: open` with
DECISIONS, or `STATE: blocked` with `CONFLICT`. A CONFLICT returns to the architect,
which amends, rejects, or reassigns.

The **critic** reads the union of the accepted module skeletons and the frozen
interfaces, and writes the subsystem `SKELETON.md`. Its accepted `SKELETON` gates the
handoff to the coder.

Each design role reaches `STATE: settled` only after the operator answers its
DECISIONS at the `question` gate.

The orchestrator only sequences and surfaces. Each role edits its own sections: the
architect in `design/subsystems/<subsystem>/02-architect/` and
`design/subsystems/<subsystem>/interfaces/`; a designer in
`design/subsystems/<subsystem>/modules/<module>/`; the critic in
`design/subsystems/<subsystem>/04-critic/`. The role sections are the record.

The method: `design-procedure.md` (steps), `design-protocol.md` (I/O and state),
`module-rules.md` (the freeze and the split), `reference/design-craft-front.md` and
`reference/design-craft-design.md` (techniques), `reference/design-quality.md` (stop
tests). Empty forms: `design/templates/`.

`NEXT` names the role that the orchestrator dispatches next.

## The Dispatch Rule

One decision for each returned message. The rule and its cases:
`constitution/articles/communication.md` section Dispatch Rule.

## The Terminal Gate

The refactorer ends the chain. It reports `NEXT: operator` when the gate passes (DRY,
ruff, the full persistent suite, the acceptance runner). The orchestrator relays the
verdict and stops. On a failing gate it reports `STATUS: blocked` with an `ASK` that
names the failure; the orchestrator surfaces it and does not advance.

## The Fast Path

For an urgent defect, the orchestrator dispatches `hotfixer` alone. It never dispatches
a role, makes one contained change, keeps the tree green, and ends the run with the
`hotfixer.md` block. A requirement, a scenario, or a contract change routes to its
owning role.

## Commit

The operator owns the commits. A role commits or pushes only when the operator asks,
with the message of the operator or the Angular form in `workflow.md`. Never commit an
unrelated change or a generated artifact. A handoff never waits for a commit and never
refers to a commit. Leave the tree for the next role.
