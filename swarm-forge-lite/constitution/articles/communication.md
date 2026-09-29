# Communication

The orchestrator is the only dispatcher: it calls one role at a time with the `subagent` tool and reads that role's final message. Roles run as subagents and never call `subagent`.

## Calling
- `agent` is the role; `prompt` is the message from `<pack>/protocol/dispatch.md`. Omit `sessionID` to start fresh; pass the returned `sessionID` to resume that session. The result is the callee's final message.
- Resume by `sessionID` by default — it keeps the role's context and is the cache hit. Start a fresh session when resuming would mislead the role: a new task, a session that drifted or contradicts itself, a prompt or protocol revision it never read, or the operator asking for a clean pass. Neither is forbidden; prefer the cheaper resume and say why when you start fresh. Concurrency is for lanes with disjoint work, not for two instances on the same chunk.

## Answering
- End the turn with the message from `<pack>/protocol/<role>.md`. Never call `subagent`. A role's `NEXT` names the role the orchestrator dispatches next.
- The refactorer's terminal message ends the run; the orchestrator relays it and stops.

## Dispatch Rule
One decision per returned message:
- `STATUS: done` + `VERIFY` evidence (specifier: also `APPROVED: yes`; design role: `STATE: settled`) -> dispatch `NEXT`.
- `STATUS: blocked`/`needs-input` (build) or `STATE: open`/`blocked` (design) -> stop; surface `ASK`/`OPEN RISKS`/pending `DECISIONS` with `question`. A blocked message never advances.
- interrogator `STATE: settled` -> dispatch the specifier; no design role is next.
- specifier `APPROVED: no` -> do not dispatch the modeler.
- specifier `APPROVED: yes` -> dispatch the modeler; the operator-gated design team begins. The coder is never next.
- design role `STATE: open` or `blocked` -> stop; a `DECISION` unanswered is not a handoff. Never advance a design role on an unanswered decision.
- critic `STATE: settled` -> surface the accepted-skeleton gate; dispatch the coder only on Proceed.
- test-reviewer `VERDICT: accept` -> dispatch the role named by `NEXT`.
- test-reviewer `VERDICT: reject` -> do not advance; re-dispatch the coder with the `FINDINGS` as the brief and loop until accept.
- missing or contradictory fields -> re-dispatch that role once; still malformed -> escalate.
- `NEXT` absent or unknown -> escalate; never guess.
- `ASSUMPTIONS: <...>` is informational: carry it into the next `INBOUND`, include it in the final relay, and never block on it.
- Failing terminal gate: the refactorer reports `STATUS: blocked` with `ASK`; surface it to the operator and stop. A blocked gate never advances.

## Field Ownership
- The orchestrator fills chunk fields by copying, and **pastes content, not pointers**: `#FEATURE` carries the pinned outcome lines beside its path, `#SKELETON` carries the chunk's accepted entries beside its path, and `#INBOUND` is the previous role's message verbatim. `ALLOWLIST` = previous `FILES` + operator-named areas (for a design role: the blueprint path plus the feature paths it reads); `VERIFY` = the role's standard command in `engineering.md`, plus the failing side when one exists; `CONTRACT` only when a chunk crosses a boundary (omit in sequential single-tree); `BLUEPRINT` = `design/<task>/BLUEPRINT.md` for the interrogator, the design roles and the coder.
- For a design role, `#FROZEN` carries the accepted upstream sections at full text, and `#STOP TEST` is copied literally out of `reference/design-quality.md` into the envelope's **last** position — the slot that gets exact attention. A pointer there spends that slot on a filename.
- A role resumed by its `sessionID` already holds its envelope: send the new evidence and the one change, not the envelope again. A fresh session gets the whole envelope.
- `ENV` and `CONVENTIONS` come from `<pack>/PROJECT.md`, the operator-owned project state. Read it each task; if a field is missing, ask the operator once and write it back. Never infer them from a role's returned message, never re-ask per task, and never invent them.
- Chunks may run concurrently as lanes with disjoint allowlists: set `LANE` so the lane wrapper scopes artifacts, tests, caches, bytecode, and temp files per lane, and freeze shared authored files (registries, `conftest.py`, `pytest.ini`). A chunk never edits outside its allowlist. Never ask a role to dispatch another role.

## Evidence
- Carry the `VERIFY` command and its exit code; green without a `VERIFY` result is not evidence. The coder does not certify its own work; the refactorer's terminal gate is the final verification.
- `VERIFY` names the exact command and exit code and which `DEFINITION OF DONE` checks it proves. A green `VERIFY` that proves no done-check is not evidence.

## Gates
- The interrogator gates on the operator answering its `DECISIONS` (`question`: Accept / Reject / Modify): it reports `STATE: settled` only after every stop-test count is zero and all are answered.
- The specifier inspects the accepted record as a second party (the author does not inspect their own record), then gates on operator approval (`question`: Approve / Request changes / Stop) and reports `APPROVED: yes` only after Approve.
- Approval opens the design gate. Each design role gates the same way and reports `STATE: settled` only after all its decisions are answered. The critic's accepted `SKELETON` gates the handoff to the coder. These roles use `design-protocol.md`, not this build envelope.
- Ambiguity, contradiction, or a spec/test conflict: ask with `question`; never guess or carry it in chat.
- Passing terminal gate (`STATUS: done`, `NEXT: operator`): relay it and stop.
- A terminal-gate defect is `STATUS: blocked` with `ASK`; the operator decides the next move.
- Scope verification to the chunk while working; the full persistent suite and every feature run once, at the terminal gate.
- Recorded `ENV`/`CONVENTIONS` are claims, not facts. A role that observes the workspace contradicting a field stops with `STATUS: blocked` and `ASK` naming the field and the conflict; the orchestrator asks the operator, updates `<pack>/PROJECT.md`, and re-dispatches. A role never proceeds on a field it believes is stale.

# Project
- Pipeline: interrogator, then specifier, then the operator-gated design team (modeler, contractor, critic), then coder, then test-reviewer, then refactorer. Language: Python.
- The requirement record runs before the specifier; the design team runs after it. Every checkpoint of both is operator-gated, and the automatic chain resumes at the coder once the accepted `SKELETON` exists.
- Do not change another role's prompt or ownership without explicit direction.
