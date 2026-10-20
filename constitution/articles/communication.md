# Communication Rules

## The Model

The operator talks to the orchestrator. The orchestrator dispatches roles. A
role talks back to the orchestrator. Roles never talk to each other, and the
operator never has to relay between them.

A role runs as a delegated agent — a subagent, a task, or a separate session,
depending on the platform. The role prompts are written in those terms only, so
they carry over unchanged.

## Handoffs

A handoff is one thing: a **report** to the orchestrator.

The code is already shared — every role edits the same files — so there is no
commit, no copy, no merge, and no mailbox to cross. The next role reads the
files.

The operator commits when the operator judges the task done — never on a role's
initiative.

## Reporting

End with a short report in plain prose:

- what you changed, by file;
- each command that proves the work, and the exit status it returned;
- what you could not do, and the decision you need.

No template and no header tokens. "Tests pass" is not a report; naming the
command and its exit status is. If you are blocked, say so in one sentence and
stop — do not guess past it.

## Operator Gates

Ask the operator only for these:

- scope: which behavior, which module, how far;
- ambiguity that changes observable behavior;
- approval of a specification before implementation starts;
- a conflict you cannot resolve inside your ownership.

Ask once, in one message, with the options and your recommendation. Never ask
for permission to run a tool the role already owns.

## Scope

- Do the task you were given. Do not add features, rename unrelated things, or
  fix another role's backlog.
- If the task is smaller than your role, say so and finish early rather than
  manufacturing work.
- If you find a defect outside the task, report it in one line. Do not fix it.
- A task may be **read-only**. Then it overrides your role's write steps: verify,
  report, change nothing. Do not resolve the contradiction in favour of writing.
