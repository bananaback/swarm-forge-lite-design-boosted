# TASK BOARD

One row per active unit of work. The orchestrator claims the row before it
dispatches, keeps it current, and removes it when the work is done.

Another session's row is context, not a lock. A change you did not make belongs
to the row that names it. Check this board before you call a change a bug.

| Session | Subsystem | Doing |
|---|---|---|
