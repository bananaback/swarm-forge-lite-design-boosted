# Dispatch

The orchestrator sends one role per `subagent` call.

## Build the envelope

Run `swarm.envelope({role,subsystem,module})`. Paste the result verbatim.

```
#PACK       <absolute pack root>
#ROLE       <role>
#SUBSYSTEM  <subsystem>
#LANE       <subsystem> | <subsystem>.<module>
#RECORD     design/subsystems/<subsystem>/
#WORK       <the file or directory this role writes>
#TOOLS      <the swarm tools this role needs>
#SPECS      <specs root>
#HARNESS    <pack>/tools/shared/harness.py
#ENV        <from PROJECT.md>
#STOP TEST  <one line>
```

Then add:

```
#CHANGE CLASS  contained | module-internal | module-cut | requirement-level | new-subsystem
#FROZEN        <paths the role may not edit>
#ALLOWLIST     <paths the role may edit>
#DONE          <the checks that end the run>
#VERIFY        <exact command> => exit <n>
#OTHER SESSIONS <the other active board rows, verbatim, or "- none">
#FOREIGN       <the reminder line, pasted as written>
```

`#OTHER SESSIONS` is a copy of the other rows in `design/TASK_BOARD.md`, pasted
verbatim, not a computed conflict. If another session names the same subsystem,
ask the operator before a second writer starts. The board is a short note, not a
lock.

## Foreign changes

A foreign change is a change the role did not make. It belongs to another
session, the operator, or an earlier run. Never revert one, and never call one
corruption. Paste it as written in every dispatch:

```
A change you did not make belongs to another session. Check design/TASK_BOARD.md
before you call it a bug or undo it. Report it as FOREIGN: path:line and continue.
```

A role that meets one reports `FOREIGN: path:line - <what>`, changes nothing, and
continues. The orchestrator answers it from the board, and names the session that
owns it.

## Rules

- Cite the Path: every input is `path:line`. Paste only the operator's ask or
  text that exists in no file.
- Use the record's own words. Do not paraphrase a requirement, a contract, or a
  decision.
- Verify every citation against the current file before sending. Drop a stale one.
- One or two tool calls build a dispatch. Do not re-read the pack to assemble it.
- The dispatch is complete when the role can work without reading another file.

## Handoff

The role returns its protocol block. Route by `STATUS`:

- `done` -> dispatch `NEXT`.
- `blocked` -> answer `ASK` and re-dispatch the same session.
- `FOREIGN` -> check the board, name the owner, continue the same session.
- `CONFLICT` -> architect.
- `reject` -> coder.

Missing or contradictory fields: re-dispatch once with the exact missing field.
A second failure is `STATUS: blocked` for the operator.

## Module dispatch

For a designer add `#MODULE` and use lane `<subsystem>.<module>`.
For a module-cut change, dispatch the architect first, then only the designers
named by the changed interface.
