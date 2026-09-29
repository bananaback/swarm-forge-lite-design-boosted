# Project Facts

Durable, operator-owned project facts: the environment and the conventions the
feature/IR will not state. The orchestrator reads this file and copies `ENV` and
`CONVENTIONS` into every dispatch; roles learn them from the dispatch.

These are claims, not facts. If the workspace contradicts a field, do not trust the
file: stop and ask the operator to verify. Update a field only when it is missing,
when the operator asks, or when a role reports a conflict and the operator resolves
it. Never infer a field from a role's message.

## ENV

_Not set. The operator — or the wiring agent, per `WIRING.md` §1 — records the
target project's environment here before the first run._

## CONVENTIONS

_Not set. The operator — or the wiring agent, per `WIRING.md` §1 — records the
target project's conventions here before the first run._
