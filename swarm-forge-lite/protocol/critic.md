# critic — design answer

The critic's final message, and the design team's handoff to the builder.

```
TASK: <stable task name>
ROLE: critic
STATE: settled | open | blocked
WORK: design/<task>/work/04-critic.md
PRODUCED: SKELETON REV 1 [ACCEPTED]
STOP TEST: at least one Xn slots in by addition only or has a written YAGNI reason; no LSP violation; no interface method unused by every client; zero duplicated policy; zero classes outside the caller closure; every name self-explanatory against its contract alone -> pass | fail
DECISIONS: <n>
  D1 [<named rule: OCP seam build/YAGNI, skeleton acceptance>] <question> | options: <a> | <b> | <c> | answer: <operator's>
FROZEN HANDOFF: <the accepted skeleton in handoff form: for each method, name + contract + responsibility sentence>
REVISION REQUESTS: <"[section] — reason — route to <role>" or "none">
OPEN RISKS: <design assumptions and non-blocking defaults, or "none">
NEXT: coder
```

Good: `STATE: settled`, `SKELETON REV 1 [ACCEPTED]`, each `DECISION` naming the seam and its cost,
`STOP TEST … -> pass`.
Bad: `SKELETON` accepted while a class outside the caller closure remains, or an OCP seam left
undecided.

On accept the critic also writes `design/<task>/SKELETON.md`, self-contained: for every method its
name, signature, pre/post/invariant, CQS tag and responsibility sentence, plus the dependency graph,
the state map and the test map. The coder and the refactorer read that file and never open
`BLUEPRINT.md`; if the two disagree, the blueprint wins.

`STATE: settled` means the operator settled every OCP seam and accepted the skeleton at the
`question` gate. `NEXT: coder` is dispatched only then. A rejected part becomes a
`[REVISION REQUEST]` routed to its owning design role; the critic never edits accepted upstream
text. `NEXT` names the role the orchestrator dispatches; the critic never calls it.
