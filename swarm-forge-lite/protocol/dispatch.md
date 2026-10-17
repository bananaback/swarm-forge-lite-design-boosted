# Dispatch

The `prompt` that the orchestrator hands to the `subagent` tool when it calls a role. Only the orchestrator dispatches.

This is the **build-loop** envelope, for `specifier`, `coder`, `refactorer`, `test-reviewer`, and `hotfixer`. Dispatch the requirement and design roles (`interrogator`, `architect`, `designer`, `critic`) with `design-protocol.md`. Those roles have no `VERIFY` command and no build `ALLOWLIST`.

## The Envelope

```
<Verb>: <artifact> - <one-line outcome>

#SUBSYSTEM   <the scope name - the same name the whole way down>
#ROLE        <specifier | coder | refactorer | test-reviewer | hotfixer>
#LANE        <the subsystem name - always set>
#CHANGE CLASS <contained | module-internal | module-cut | requirement-level | new-subsystem>

#FEATURE  <feature path>
<cite the outcome lines this chunk pins: path:line>
#SKELETON <design/subsystems/<subsystem>/SKELETON.md>
<cite the accepted entries for this chunk: path:line + the entry name>
#INBOUND  <the path and line of the previous role's answer artifact>

#ENV         <cite PROJECT.md section ENV>
#CONVENTIONS <cite PROJECT.md section CONVENTIONS, or "none">
#CONTRACT    <cite the interface path - include only when the chunk crosses a module>
#ALLOWLIST
<one path per line. The role edits nothing outside it>

#SCOPE
Do the work the ask describes. For the refactorer: name one exact target, or write
`no cleanup`.
#CARRIED
<the failures that are not this chunk's to fix, each with its reason. `pass` means
the chunk's own gate>

#VERIFY  <the exact command>   - currently failing: <the test and its expectation>

#DONE
1. <observable check>
2. <observable check>
3. <observable check>

Output: <pack>/protocol/<role>.md - exactly that block, no preface, no trailing prose.
If a detail is missing: `ASSUMED: <...>` in one line, then continue.
```

## The Headline

The first line names the subsystem and is the ask: one line, imperative, no persona. Do not repeat it in the tail.

| Role | Headline opens with | Example |
|---|---|---|
| specifier | `Specify:` | `Specify: privacy_recording.feature - one scenario per requirement` |
| coder | `Implement:` | `Implement: ClipRecorder.start - a playable MP4 at the caller's filename` |
| refactorer | `Refactor:` | `Refactor: the retention pruner - same behavior, lower CRAP` |
| test-reviewer | `Review:` | `Review: the coder's authored tests against the quality rubric` |
| hotfixer | `Fix:` | `Fix: the clip path resolves relative to the wrong directory` |

## Cite the Path

Cite every input as `path:line`. The role reads the file when it needs the text.
Paste only the operator's ask (`#REQUEST`) and text that exists in no file.

Do not paste a record section, a previous answer, an environment block, or a stop
test. Cite them. A role that needs a whole file reads the file.

There is no size limit. A short paste is fine. A long paste where a path would do
is wasted, and the orchestrator pays for it on every turn.

## Who Supplies What

The orchestrator assembles every field by cite or by copy. It never invents content.

- **headline** - verb + artifact + the one-line outcome, from the chunk's dispatch. It is the ask.
- `#CHANGE CLASS` - the class of the change: `contained`, `module-internal`, `module-cut`, `requirement-level`, or `new-subsystem`. The orchestrator decides it **before** the first dispatch, from the change alone, never from the state of the record. The class picks the roles. See `constitution/articles/communication.md`.
- `#FEATURE` - the feature path and the `path:line` of the outcome lines this chunk pins.
- `#SKELETON` - the path and the `path:line` of the accepted entries **for this chunk**: the name, signature, contract, CQS tag, and responsibility sentence of each method. Neither the coder nor the refactorer opens the design record.
- `#INBOUND` - the `path:line` of the previous role's answer artifact. Evidence, never a summary.
- `#ENV` - cite `<pack>/PROJECT.md` section ENV, including the forbidden actions. On a resumed session, write `same ENV as the previous dispatch`. If a field is missing, ask the operator once and write the answer into the file. Never infer it from a message of a role.
- `#CONVENTIONS` - cite `<pack>/PROJECT.md` section CONVENTIONS, or `none`. Do not restate what the feature or IR already says.
- `#CONTRACT` - cite the interface path. Include it only when the chunk shares an interface with another chunk. Single-tree work has one chunk at a time, so omit it by default.
- `#ALLOWLIST` - the paths named by the `FILES` of the previous message, plus the source and test areas the operator named.
- `#SCOPE` - the ask. For the refactorer, name **one exact target**, or write `no cleanup`. Never write an open-ended license such as `cleanup where safe`. An open license makes the role hunt for work that does not exist.
- `#CARRIED` - the failures that are not this chunk's to fix, each with its reason. `pass` means the chunk's own gate alone. The refactorer refreshes `model.live.json` and `model.html` and never touches `model.json`.
- `#VERIFY` - the standard verification of the role, scoped to the chunk, copied exactly from `engineering.md`, with `python3` in front of every python tool. Ruff uses `python3 <pack>/tools/shared/ruff4py` (a package directory, never a binary). Pytest must run through the lane wrapper (`<pack>/tools/shared/lane <subsystem> ...`), never directly. Coder: the pinned test of the chunk and the acceptance of its feature. Refactorer: CRAP, then DRY. Add the failing side when one exists. The numbers the orchestrator cites come from the tool, never by hand, so the tool and the role agree.
- `#DONE` - up to three checks that a script, a reviewer, or a diff can verify. No quality words, no restatement of the ask.
- `#LANE` - always the subsystem name. The role prefixes every shell command with `<pack>/tools/shared/lane <subsystem>`, so the artifacts, caches, and generated tests are scoped to this subsystem alone. One subsystem, one lane: the steps of a change run in order.

`#ENV` and `#CONVENTIONS` are unverified claims, not facts. If the workspace contradicts one, tell the operator.

## Resumed Sessions Send the Delta

A role continued by its `sessionID` already holds the envelope. Send the new evidence and the single change, not the whole envelope again. State again the invariant that moved:

```
Test 2 still fails: <the new output>. Same done-list. Continue.
```

On a new session, send the whole envelope.

## One More Rule

Do not ask the role to dispatch the next role. It answers with its template and a `NEXT` line. The orchestrator reads `NEXT` and makes the next call.
