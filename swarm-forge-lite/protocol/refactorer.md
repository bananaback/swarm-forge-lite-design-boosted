# refactorer

The refactorer's final message.

```
TASK: <stable task name>
STATUS: done | blocked | needs-input
SUMMARY: <one line: files touched; max CRAP, DRY, coverage; suite state>
FILES: <created or changed paths>
VERIFY: <the verification command> => exit <n>
ASSUMPTIONS: <non-blocking defaults you took; else "none">
NEXT: operator
ASK: <only when STATUS is not done>
```

Good: `SUMMARY: src/cart.py; CRAP max 6, DRY clean, unit+acceptance green`, `ASSUMPTIONS: none`
Bad: `SUMMARY: cleaned up`

`NEXT` is `operator` when the terminal gate passes: the run ends and the orchestrator relays the verdict. On a failing gate, `STATUS` is not done and `ASK` names the failure; the orchestrator surfaces it and stops. The refactorer never calls `subagent` itself.
