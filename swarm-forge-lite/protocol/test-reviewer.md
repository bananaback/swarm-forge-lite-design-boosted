# test-reviewer

The test-reviewer's final message.

```
TASK: <stable task name>
STATUS: done | blocked | needs-input
VERDICT: accept | reject
SUMMARY: <tests reviewed; findings; the runtime of the chunk's tests>
FILES: <the authored test files reviewed>
VERIFY: <the pytest command, run one and run two> => exit <n>
FINDINGS:
- <test> — <smell by name> — <the exact violation> — fix: <the concrete change>
MUTATION: <for the accepted tests, one line: the wrong implementation each catches>
ASSUMPTIONS: <non-blocking defaults you took; else "none">
NEXT: refactorer
ASK: <only when STATUS is not done>
```

`VERDICT: accept` -> `NEXT: refactorer`. `VERDICT: reject` -> `NEXT: coder`; the orchestrator
re-dispatches the coder with the findings and loops until accept.

Good: `VERDICT: reject`, `FINDINGS: - test_check_reads_config — Over-Mocking — it mocks the fs
and asserts read_text was called — fix: inject the in-memory fake and assert the finding`.
Bad: `VERDICT: reject` with "tests could be cleaner" (no smell, no violation, no fix), or
`VERDICT: accept` while `raises(Exception)` remains.

The reviewer never edits files and never uses the `question` tool. `NEXT` names the role the
orchestrator dispatches; the test-reviewer never calls it.
