# specifier

The specifier's final message.

```
TASK: <stable task name>
STATUS: done | blocked | needs-input
APPROVED: yes | no
SUMMARY: <one line: feature path, the behavior pinned>
FILES: <feature path, IR path, dry path>
VERIFY: <parse + dry-check command> => exit <n>
ASSUMPTIONS: <non-blocking defaults you took; else "none">
NEXT: <modeler | interrogator>
ASK: <only when STATUS is not done>
```

Good: `STATUS: done`, `APPROVED: yes`, `SUMMARY: login.feature; one behavior per scenario`, `VERIFY: gherkin-parser ... && ir-dry-checker ... => exit 0`, `ASSUMPTIONS: none`
Bad: `SUMMARY: wrote a spec`

`APPROVED: yes` means the operator answered `Approve` at the `question` gate. Approval is the
quality gate on clear business requirements; it opens the design phase. The orchestrator next
dispatches the **modeler**, never the coder. The feature is the business acceptance contract the
design team reads and must not change.

Before writing Gherkin the specifier **inspects the accepted requirement record** — GOAL,
CONSTRAINTS, EXCLUSIONS, REQUIREMENTS, the requirement document `docs/specs/NN-<task>.md`, and
`work/01-interrogator.md` — as a second party: the author does not inspect their own record. The
document must match the record one-to-one on Rn/ACn, and must exist (refined or created by the
interrogator). A non-zero stop-test count, a requirement with no
verification method, an acceptance check the goal's vocabulary cannot express, or a document that
disagrees with the record is a defect:
report it as `[REVISION REQUEST] — <section> — <reason> — route to interrogator` in `ASK`, set
`NEXT: interrogator`, and write no Gherkin.

On `Request changes`, revise and re-ask; on `Stop`, report and stop.

`NEXT` names the role the orchestrator dispatches next. The specifier never calls it.
