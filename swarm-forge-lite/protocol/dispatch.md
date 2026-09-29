# Dispatch

The `prompt` the orchestrator hands to the `subagent` tool when it calls a role. Only
the orchestrator dispatches; a role never calls `subagent` and never forwards.

This is the **build-loop** envelope, for `specifier`, `coder`, `refactorer`, `test-reviewer`
and `hotfixer`. The requirement and design roles (`interrogator`, `modeler`, `contractor`,
`critic`) are dispatched with the envelope in `design-protocol.md` instead — they have no
`VERIFY` command and no build `ALLOWLIST`, and their output is a decision ledger plus filled
forms, not a diff.

## The envelope

Shape follows the V4+ prompting guide: the verb-led headline first, the evidence in labelled
blocks, and the ask with the hard constraints **last**, where attention is exact.

```
<Verb>: <artifact> — <one-line outcome>

#TASK     <stable task name — the same name the whole way down>
#ROLE     <specifier | coder | refactorer | test-reviewer | hotfixer>
#LANE     <disjoint lane id, or none — scopes the disposable roots>

#FEATURE  <feature path>
<PASTE the scenarios this chunk pins — the outcome lines, verbatim>
#SKELETON <design/<task>/SKELETON.md>
<PASTE the accepted entries for this chunk — name · signature · contract · CQS · responsibility>
#INBOUND
<the previous role's final message, verbatim>

#ENV
<PASTE every ENV line from PROJECT.md, the forbidden actions included>
#CONVENTIONS
<the one non-obvious invariant the feature/IR does not state; else "none">
#CONTRACT
<the shared interface — include only when the chunk crosses a boundary>
#ALLOWLIST
<one path per line; the role edits nothing outside it>

#SCOPE
Edit only the allowlist. Never edit a test, a feature or a config to make a check pass. No network,
no package installs, no git history changes, no `rm`, no `chmod`.

#VERIFY  <the exact command>   · currently failing: <the test and its expectation>

#ASK
<the chunk brief in one or two lines: what this role must achieve>
#DONE
1. <observable check>
2. <observable check>

Output: <pack>/protocol/<role>.md — exactly that block, no preface, no trailing prose.
If a detail is missing: `ASSUMED: <...>` in one line, then continue.
```

## The headline — a routing cue, not decoration

The first line names the task domain, because V4+ routes by domain and the head of a long
prompt is compressed. One line, imperative, no persona.

| Role | Headline opens with | Example |
|---|---|---|
| specifier | `Specify:` | `Specify: privacy_recording.feature — one scenario per requirement` |
| coder | `Implement:` | `Implement: ClipRecorder.start — a playable MP4 at the caller's filename` |
| refactorer | `Refactor:` | `Refactor: the retention pruner — same behaviour, lower CRAP` |
| test-reviewer | `Review:` | `Review: the coder's authored tests against the quality rubric` |
| hotfixer | `Fix:` | `Fix: the clip path resolves relative to the wrong directory` |

## Why content, not pointers

Paste the artifact. `#FEATURE` carries the pinned outcome lines and `#SKELETON` the accepted
entries for the chunk — not just their paths. A path spends the role's attention on a filename
and throws away the exact identifiers it needs; the path stays alongside so the role can read
more when it must.

## Who supplies what

The orchestrator assembles every field. It does no role work: it copies from the operator's
brief, the previous role's message, and the constitution.

- **headline** — verb + artifact + the one-line outcome, from the chunk's brief.
- `#ASK` — the chunk brief in one or two lines: what this role must achieve. It sits with
  `#DONE` in the tail, after the evidence, where attention is exact.
- `#FEATURE` — the feature path *and* the scenario outcome lines this chunk pins, copied
  verbatim. A fresh feature starts from its feature artifact and the roots it touches.
- `#SKELETON` — the path *and* the accepted entries for the chunk: each method's name,
  signature, contract, CQS tag and responsibility sentence. This is the coder's contract and
  the refactorer's fixed shape; neither opens `BLUEPRINT.md`.
- `#INBOUND` — the previous role's final message, verbatim. Evidence, never a summary of it.
- `#ENV` — every line from `<pack>/PROJECT.md`, **including the forbidden actions**, copied.
  One line each. If a field is missing, ask the operator once and write it back; never infer it
  from a role's message.
- `#CONVENTIONS` — the one non-obvious invariant the feature/IR does not state, or `none`,
  copied from `<pack>/PROJECT.md`. Do not restate what the feature/IR already says.
- `#CONTRACT` — include only when the chunk shares an interface with another chunk. Sequential
  single-tree work has one chunk at a time, so omit it by default.
- `#ALLOWLIST` — the paths named by the previous message's `FILES`, plus the source and test
  areas the operator named.
- `#VERIFY` — the role's standard verification, scoped to the chunk, copied exactly from
  `<pack>/constitution.md`. Coder: the chunk's pinned test and its feature's acceptance.
  Refactorer: CRAP, then DRY. Add the failing side when it exists: the test and what it expects.
  The full persistent suite and every feature run only at the terminal gate.
- `#DONE` — two to five checks a script, a reviewer or a diff could verify. No quality words.
- `#LANE` — set only when this chunk runs beside another. The role prefixes its shell commands
  with `<pack>/tools/shared/lane <lane>`; omit it for a lone chunk, and never reuse an id.
- `#SCOPE` — copy verbatim. It is the blast-radius fence, and V4.1 agent runs need it.

`#ENV` and `#CONVENTIONS` are unverified claims, not facts. If the workspace contradicts one, the
role blocks with `ASK` naming the field and the conflict instead of proceeding.

## Resumed sessions send the delta

A role resumed by its `sessionID` already holds the envelope in context. Send the new evidence
and the single change — not the whole envelope again — and restate the invariant that moved:

```
Test 2 still fails: <the new output>. Same done-list. Keep going.
```

On a fresh session, send the whole envelope.

## One more rule

Do not ask the role to dispatch the next role. It answers with its template and a `NEXT` line;
the orchestrator reads `NEXT` and makes the next call.
