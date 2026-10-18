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
#OTHER SESSIONS <the other active board rows, or "- none">
```

`#OTHER SESSIONS` is a copy of the other rows in `design/TASK_BOARD.md`, not a
computed overlap. If another session names the same subsystem, ask the operator
before a second writer starts. The board is a short note, not a lock.

A foreign change is not corruption. Check `design/TASK_BOARD.md` before you
assume a bug or overwrite a file.

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
- `CONFLICT` -> architect.
- `reject` -> coder.

Missing or contradictory fields: re-dispatch once with the exact missing field.
A second failure is `STATUS: blocked` for the operator.

## Module dispatch

For a designer add `#MODULE` and use lane `<subsystem>.<module>`.
For a module-cut change, dispatch the architect first, then only the designers
named by the changed interface.
