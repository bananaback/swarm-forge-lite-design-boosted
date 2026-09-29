# hotfixer

The hotfixer's final message. It is standalone — the operator talks to it directly and it ends
the run itself, so there is no `NEXT`. Plain text.

```
STATUS: fixed | blocked
BUG: <one line: the symptom and how it is reproduced>
CAUSE: <one line: the defect>
FIX: <the change>
LAYERS: <the layers touched and their twin updates, e.g. code + unit test; design CONTRACTS; feature scenario>
VERIFY:
- <pytest command> => exit <n>
- <run_acceptance feature> => exit <n>
- <ruff4py command> => exit <n>
RISKS: <what could still break, or "none">
ASK: <only when blocked: the owner decision needed>
```

Good: `STATUS: fixed`, `BUG: an empty version map crashes — reproduced by test_empty_version_map_is_refused`,
`LAYERS: code + unit test; design CONTRACTS updated`, every `VERIFY` `=> exit 0`, `RISKS: none`.
Bad: `STATUS: fixed` with no reproduction, or a `VERIFY` that ends `=> exit 1`.

`blocked` is only for a missing input or an owner decision the artifacts cannot settle — never
"call the team". The hotfixer updates whatever layer the change touches and keeps the layers
consistent.
