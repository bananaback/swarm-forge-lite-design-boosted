# contractor — design answer

The contractor's final message. Design-native: the contract is the output.

```
TASK: <stable task name>
ROLE: contractor
STATE: settled | open | blocked
WORK: design/<task>/work/03-contractor.md
PRODUCED: CONTRACTS REV 1 [ACCEPTED]
PRODUCED: TEST_MAP REV 1 [ACCEPTED]
STOP TEST: every method has pre/post/invariant and exactly one CQS tag; no chain beyond one dot; every acceptance check has a named test wired to an existing signature -> pass | fail
DECISIONS: <n>
  D1 [<named rule: CQS split, public-shape split, business contradiction>] <question> | options: <a> | <b> | <c> | answer: <operator's>
FROZEN HANDOFF: <the contract fact the critic must not reopen, e.g. "Ledger.post is the only Command on Ledger; all reads are Queries">
REVISION REQUESTS: <"[section] — reason — route to <role>" or "none">
OPEN RISKS: <design assumptions and non-blocking defaults, or "none">
NEXT: critic
```

Good: two `PRODUCED` lines `[ACCEPTED]`, a `DECISIONS` item naming the CQS or contradiction rule,
`STOP TEST … -> pass`.
Bad: a method tagged both Command and Query, or a test name with no mapped signature.

`STATE: settled` means the operator resolved every public-shape `DECISION` at the `question` gate.
Internal Demeter rewiring is resolved by the contractor and logged in the work file, not gated.
`NEXT` names the role the orchestrator dispatches; the contractor never calls it.
