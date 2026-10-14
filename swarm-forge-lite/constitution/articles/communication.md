# Communication

The orchestrator dispatches roles with `subagent` and reads the final message. A role answers with its template. The orchestrator then dispatches the role named by `NEXT`.

## Language (ASD-STE100)
- Write every message in ASD-STE100 Simplified Technical English.
- Keep these items exactly as given: field names, control tokens, paths, identifiers, commands, code, and exit codes.
- Use short sentences. In an instruction, use a maximum of 20 words. In a description, use a maximum of 25 words.
- Write one instruction in each sentence. Use the imperative form for an instruction and the active voice.
- Use the simple present tense for a description.
- Do not use a contraction, the "-ing" form of a verb, or a semicolon.
- Use one term for one item, and use that term each time.
- Use American English spelling.

- Every dispatch carries `LANE: <subsystem>`. A role with `LANE [-] (none)` sets the lane before it writes.

## Calling
- `agent` is the role. `prompt` is the message from `<pack>/protocol/dispatch.md`. Omit `sessionID` to start a new session. Pass the returned `sessionID` to continue that session. The result is the final message of the callee.
- Continue by `sessionID` by default. This costs less and keeps the context. Start a new session when a continued session would mislead: a new task, a drifted or contradictory session, an unread prompt or protocol change, or a request for a clean pass.

## Tools
- Every role may use any tool of the catalog. Use each tool in a BOUNDED way.
- Bound every read. A call that returns a long text passes `limit` and a low cap. One step must not carry the whole of a long document or the whole of a long transcript.
- `convo` reads the conversation history. Read the running task, bounded. Do not read the whole of a long foreign session: the orchestrator's own transcript runs to thousands of messages, and one unbounded read of it aborts the next step.
- Name the target of a search first, then narrow. A sweep of a whole tree is a defect of the dispatch that asked for it.

## Answering
- End the turn with the message from `<pack>/protocol/<role>.md`. The `NEXT` of a role names the role that the orchestrator dispatches next.
- Report references, not content. Give the file path and the line number for every item a field carries, beside a short label. Do not paste the record, the code, the tests, or the findings.
- The terminal message of the refactorer ends the run. The orchestrator relays it and stops.

## Stuck
- A role that is stuck stops and asks in its last message. It does not use the `question` tool for this, and it does not force a workaround.
- The orchestrator answers the question and dispatches the role again. It asks the operator only when it cannot answer the question itself.

## Dispatch Rule
One decision for each returned message:
- `STATUS: done` plus `VERIFY` evidence (the specifier also gives `APPROVED: yes`, and a design role also gives `STATE: settled`) means dispatch `NEXT`.
- Re-surface a decision when new **verified** evidence contradicts the earlier answer of the operator: name the criterion it violated, and ask once. Never silently apply a contradiction.
- `STATUS: blocked` or `needs-input`, or `STATE: blocked`, means answer the `ASK` and dispatch the role again. Ask the operator only when the answer is not available. `STATE: open` with a `DECISION` means put the decision to the operator.
- `STATE: blocked` with an `ASK` that names the `hotfixer` means dispatch the `hotfixer` on the same ask. The requirement phase does not run for that ask.
- A permission stop (`STATUS: blocked` or `STATE: blocked` caused by a denied command, tool, or path) means surface the exact command and the exact error to the operator. Do not dispatch the role again and do not work around the denial. The operator performs the action.
- Interrogator `STATE: settled` means dispatch the specifier.
- Specifier `APPROVED: no` means do not dispatch the architect.
- Specifier `APPROVED: yes` means dispatch the architect, and the operator-gated design team starts.
- Architect `STATE: settled` means split the module map and dispatch one designer for each module in parallel.
- Designer `STATE: settled` means collect it. When every designer is settled, dispatch the critic on the union.
- Designer `STATE: blocked` with `CONFLICT` means route it to the architect, then re-dispatch only the consumers named in the changed interface file. The CONFLICT carries the exact proposed change: `path:line`, the new line, and the why. The architect answers ONE line - `AMEND`, `REJECT` or `REASSIGN`, with the reason - and re-runs no design. The orchestrator sends the one change, not a new envelope.
- Design role `STATE: open` means put the DECISIONS to the operator. The designer round batches every designer DECISION into ONE round. The architect gate and the critic gate each run once, in order, because each blocks the next phase; they do not batch with another phase.
- Critic `STATE: settled` means surface the accepted-skeleton gate. Dispatch the coder on Proceed.
- Test-reviewer `VERDICT: accept` means dispatch the role named by `NEXT`.
- Test-reviewer `VERDICT: reject` means dispatch the coder again with the findings file (the `FINDINGS` path) as the dispatch, and loop until accept.
- A missing field or a contradictory field means dispatch that role again once. If the message is still malformed, use your judgment.
- `ASSUMPTIONS: <...>` is information. Carry it into the next `INBOUND` and include it in the final relay.
- A failing terminal gate: the refactorer reports `STATUS: blocked` with `ASK`. Surface it to the operator.

## Change Class

The orchestrator classifies the ask **before** the first dispatch. The class picks
the roles. Read the module map and the ask, then pick one:

| Class | Test | Roles |
|---|---|---|
| `contained` | an implementation-specific change: a test edit, a refactor, a rename, a doc claim, a vocabulary or wording pass over an existing document, or a value/tuning change and its pins. No goal, constraint, requirement, or SCR-table effect | `hotfixer` alone |
| `module-internal` | no module cut, no `Owns` move, no frozen-interface change, no goal or requirement change | the affected designer, then the critic, coder, test-reviewer, refactorer |
| `module-cut` | a module cut, an `Owns` move, or a frozen-interface change | the architect, the affected designers, the critic, coder, test-reviewer, refactorer |
| `requirement-level` | a goal, a constraint, a requirement, or an SCR-table change - a **business** effect | the full chain: interrogator, specifier, architect, designers, critic, coder, test-reviewer, refactorer |
| `new-subsystem` | a new subsystem directory | the full chain |

- The class comes from the **change alone**. The state of the record never picks the class. A thin, empty, or absent record is never a reason to escalate.
- `contained` and `module-internal` belong to an implementation-specific change. Never pick `requirement-level` for such a change, whatever the record holds. That change writes no requirement document and no design record.
- `requirement-level` needs a business effect. Without a goal, a constraint, a requirement, or an SCR-table change, the class is not `requirement-level`.
- Escalate one class only between `contained`, `module-internal`, and `module-cut`. Never escalate into `requirement-level` without a business effect.
- A subsystem with no accepted record does not force the full chain. An implementation-specific change in such a subsystem is `contained`.
- If an implementation-specific ask reaches the interrogator, the interrogator stops with `STATE: blocked` and an `ASK` that names the `hotfixer`. It writes no requirement document.
- `contained`, `module-internal`, and `module-cut` skip the interrogator and the specifier. The requirement record stands.
- The class is the field `#CHANGE CLASS` in the dispatch.
- The affected modules come from the `consumers:` line of each frozen interface. Dispatch a designer only for a module the change touches.

## Field Ownership
- The orchestrator cites every input as `path:line`. It pastes only the ask of the operator and text that exists in no file. `#FEATURE` cites the pinned outcome lines. `#SKELETON` cites the accepted entries of the chunk. `#INBOUND` cites the previous role's answer artifact. `ALLOWLIST` = the previous `FILES` plus the areas that the operator names (for a design role: the record path plus the feature paths it reads). `VERIFY` = the standard command of the role in `engineering.md`, plus the failing side when one exists. The `VERIFY` numbers come from the tool, never by hand. Include `CONTRACT` only when a chunk crosses a module. `SUBSYSTEM` = `design/subsystems/<subsystem>/` for the interrogator, the design roles, and the coder.
- For a design role, `#FROZEN` cites the accepted upstream sections this phase needs: the path and the section, read from `design/subsystems/<subsystem>/`. Cite the path of every other section. Put the `#STOP TEST` cite last - the pass clauses of the role in `reference/design-quality.md`. The full list is the module gate, run by `swarm.check`.
- A role continued by its `sessionID` already holds its envelope. Send the new evidence and the one change, not the envelope again. A new session gets the whole envelope.
- `ENV` and `CONVENTIONS` come from `<pack>/PROJECT.md`, the operator-owned project state. Read it for each task. If a field is missing, ask the operator once and write the answer into the file.
- In one task, the steps run in order on one lane. Two tasks in two sessions are isolated by their lanes, so the disposable output, the caches, and the generated tests cannot collide.
- A role that finds a red check outside its allowlist reports `CONFLICT: <subsystem> owns <path>` and continues. The orchestrator surfaces the conflict to the operator.
- A designer that cannot honor a frozen interface reports `STATE: blocked` with `CONFLICT: <interface path> - <change> - <why>`. It never edits the frozen zone. The orchestrator routes it to the architect (see `reference/module-rules.md`).

## Evidence
- Carry the `VERIFY` command and its exit code. A green result without a `VERIFY` result is thin evidence. The terminal gate of the refactorer is the final verification.
- `VERIFY` names the exact command, the exit code, and the `#DONE` checks it proves.

## Gates
- Gate integrity: a role never reports `APPROVED: yes` or `STATE: settled` without the answer of the operator at that gate. A missing answer is `STATE: open`, not a settlement.
- The gate belongs to the OPERATOR'S choices alone. Raise a DECISION when the answer changes a behavior, a constraint, an exclusion or the scope. Every other choice belongs to the ROLE: decide it, write the answer in the role's own `decisions.md` row, and continue. A design-internal choice - a name, a seam, a split, a summary column - never stops the pipeline.
- A disagreement the CHECKER can settle is fixed by the tool and never by two roles. Read the finding, apply `swarm.fix({code})`, and re-run the check. A count, a stale line cite, and a mismatch between the record and a view never become a DECISION.
- `STATE: settled` and a new `DECISION` never coexist. A new DECISION means `STATE: open`.
- Prefix a DECISION id with the role tag when the ask of the operator already uses `Dn` (`INT-D1`, `MOD-D1`, `CON-D1`, `CRT-D1`), so ids never collide.
- The **scope gate** runs at the interrogator. It asks the operator the fixed scope questions once: which use cases must the subsystem serve now, which are expected in the near term, which are out of scope for now, and what scale must it hold now and in the near term. The interrogator records the answers as exclusion rows (reason `YAGNI`) and constraint rows. The design team then cites a scope answer for every extension point, seam, and split. An extension point with no scope answer is a defect. This is where a future that does not exist is excluded, so the design does not pay for it.
- The interrogator gates on the answers of the operator to its `DECISIONS` (`question`: Accept / Reject / Modify). It reports `STATE: settled` after the stop test counts are zero and the operator answers each decision.
- The specifier examines the accepted record as a second party (the author does not examine their own record). Then it gates on operator approval (`question`: Approve / Request changes / Stop) and reports `APPROVED: yes` after Approve.
- Approval opens the design gate. The architect gates on its module DECISIONS and reports `STATE: settled` after the operator answers. **The orchestrator then splits the module map and dispatches one designer for each module in parallel. It batches every designer DECISION into one operator round (Accept / Reject / Modify).** It then dispatches the critic on the union. The accepted `SKELETON` from the critic gates the handoff to the coder. These roles use `design-protocol.md`, not the build envelope.
- Ambiguity, contradiction, or a spec/test conflict: ask with `question`.
- Gate options: interrogator and design roles - Accept / Reject / Modify. Specifier - Approve / Request changes / Stop. Skeleton gate of the critic - Proceed / Stop.
- A passing terminal gate (`STATUS: done`, `NEXT: operator`): relay it and stop.
- A terminal-gate defect is `STATUS: blocked` with `ASK`. The operator decides the next move.
- Scope the verification to the chunk while you work. The full persistent suite and every feature run once, at the terminal gate.
- The recorded `ENV` and `CONVENTIONS` are claims, not facts. A role that observes the workspace contradict a field stops with `STATUS: blocked` and an `ASK` that names the field and the conflict. The orchestrator asks the operator and updates `<pack>/PROJECT.md`.
- Read another subsystem's design when its work is settled.
- The hotfixer is the fast path. It never dispatches a role. A requirement, a scenario, or a contract change routes to its owning role.

## Project
- Pipeline: interrogator, specifier, then the architect, then the designers in parallel (one for each module), then the critic, then coder, test-reviewer, refactorer. The operator gates a BUSINESS choice alone: a behavior, a constraint, an exclusion, or the scope. A role settles every design-internal choice itself, in its own `decisions.md` row. Language: Python.
- The requirement record runs before the specifier. The design team runs after the specifier. The automatic chain starts again at the coder when the accepted `SKELETON` exists.
