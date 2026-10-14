# GOAL — <subsystem>

operator intent: <the ask, one line>
draft spec: <docs/specs/NN-<subsystem>.md, or none>
lane: <subsystem>

## Pipeline
| step | role | state | artifact |
|---|---|---|---|
| 1 | interrogator | | design/subsystems/<subsystem>/01-interrogator/ |
| 2 | specifier | | |
| 3 | architect | | design/subsystems/<subsystem>/02-architect/ARCHITECTURE.md |
| 4 | designers | | design/subsystems/<subsystem>/modules/ |
| 5 | critic | | design/subsystems/<subsystem>/SKELETON.md |
| 6 | coder | | |
| 7 | test-reviewer | | |
| 8 | refactorer | | |

States: `todo`, `running`, `open` (waiting on the operator), `blocked`, `done`.

Keep this shape. One state cell and one log line for each step. Replace the row in
place. Write no prose in the log. The scratchpad holds the states, the paths, the
open decisions, and the one next action — nothing else.

## Modules
| module | designer | state | conflict |
|---|---|---|---|

## Open decisions
- <ARCH-D1, DES-D2, ... — the question, or "none">

## Next
<the single next action>

## Log
- <one line for each step: role, result, path>
