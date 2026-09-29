# coder

The coder's final message.

```
TASK: <stable task name>
STATUS: done | blocked | needs-input
SUMMARY: <one line: files touched, the skeleton methods filled, and the VERIFY result>
FILES: <created or changed paths>
VERIFY: <the exact command> => exit <n>
ASSUMPTIONS: <non-blocking defaults you took; else "none">
NEXT: refactorer
ASK: <only when STATUS is not done>
```

Good: `SUMMARY: src/cart.py, unit/test_cart.py; Cart.add_body filled per contract; VERIFY green (12 passed)` with `VERIFY: ... => exit 0` and `ASSUMPTIONS: cents are integers`
Bad: `SUMMARY: done`

`NEXT` names the role the orchestrator dispatches next. The coder never calls it.
