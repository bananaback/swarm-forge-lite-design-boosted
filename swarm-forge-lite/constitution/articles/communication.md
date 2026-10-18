# Communication

## Language

Write ASD-STE100 Simplified Technical English.

- Instruction: 20 words maximum. Description: 25 words maximum.
- Use the imperative for instructions and the simple present for descriptions.
- Use the active voice. Do not use contractions, `-ing` verbs, or semicolons.
- Use one term for one item. Use American spelling.
- Keep field names, tokens, paths, commands, identifiers, and exit codes exact.

## Dispatch

Every dispatch carries:

- `#ROLE`, `#SUBSYSTEM`, `#LANE`, `#RECORD`, `#WORK`, `#TOOLS`, `#SPECS`.
- `#CHANGE CLASS`: `contained | module-internal | module-cut | requirement-level | new-subsystem`.
- `#FROZEN`: the paths the role may not edit.
- `#ALLOWLIST`: the files the role may edit.
- `#DONE`: the checks that end the run.
- `#VERIFY`: the exact commands and the expected exit codes.
- `#OTHER SESSIONS`: active claims from another session on the same subsystem or
  overlapping files, or `- none`. A foreign change is not corruption; check
  `design/TASK_BOARD.md` before you assume a bug.

Use `swarm.envelope({role,subsystem,module})` to build the block. Paste it
verbatim. Cite inputs as `path:line`. Verify every citation before sending.

## Answers

- End with `protocol/<role>.md`, filled exactly.
- Report references (`path:line`), not content.
- `NEXT` names the next role. The hotfixer has no `NEXT`.
- `STATUS: done` means the stop test is green. `STATUS: blocked` carries `ASK`.
- Never report `APPROVED: yes` or `STATE: settled` without the operator's answer.

## Handoff

| Incoming | Action |
|---|---|
| `STATUS: done` | Dispatch `NEXT`. |
| `STATUS: blocked` / `needs-input` | Answer `ASK` and re-dispatch. |
| `STATE: settled` | Continue; a new DECISION makes that illegal. |
| `CONFLICT` | Route to the architect. |
| test-reviewer `reject` | Route to the coder. |

## Gate integrity

- The operator answers business choices. A design-internal choice is a
  `DECISION` row in the record.
- A new DECISION means `STATE: open`.
- A role may not mark a gate green. Only the tool result and the operator answer do.
- Re-surface a decision only when its inputs changed, and name the change.
- A green claim without `VERIFY` is thin. The terminal gate is final.

## Field ownership

- `#ALLOWLIST` is the previous `FILES` plus the areas the operator names.
- `#FROZEN` names the interface sections and the accepted contracts.
- `ENV` and `CONVENTIONS` come from `PROJECT.md`.
- A role writes only its own files. A cross-file need is `FOR OTHER ROLES: path:line`.

## Change classes

| Class | Path |
|---|---|
| `contained` | orchestrator, then hotfixer alone |
| `module-internal` | affected designer, critic, coder, test-reviewer, refactorer |
| `module-cut` | architect, affected designers, critic, coder, test-reviewer, refactorer |
| `requirement-level` | full chain |
| `new-subsystem` | full chain |

The class comes from the change, never from record state. A business effect is
the only reason to escalate to `requirement-level`. A `module-internal` change
starts from the existing module file and its feature. A `module-cut` change
starts from `architecture.md` and the accepted `SKELETON.md`.

## Scope gate

Run the scope gate before the specifier starts.

Before the specifier, the interrogator records three answers: near-term use
cases, expected scale, and out-of-scope work. A missing answer is a DECISION.

## Roles and tools

Use `swarm.*` in Code Mode. Inside `execute`, only `tools.swarm`, `tools.convo`,
and `tools.opencode` exist. Use top-level `read`, `glob`, `grep`, and `shell`
outside it. Every `swarm.*` result is a JSON string; parse it. Every result
carries `pack`.
