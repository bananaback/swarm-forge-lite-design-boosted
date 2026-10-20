# Workflow Rules

## Shared Codebase

- Every role works in the one project directory named by
  `config/pack.json` → `project_root`.
- There is no worktree, no per-role branch, and no copy of the code. The files a
  role edits are the files the next role reads.
- Roles run one at a time. The orchestrator dispatches them; the code is only
  ever in one place.
- Work only on the files your role owns. Another role's change is not yours to
  fix, revert, or reformat.
- If the project directory is missing, stop and report. If a file you are about
  to write already holds changes nobody in this chain made, stop and report that
  file. Unrelated changes elsewhere do not block you, and a read-only task never
  blocks on them.

## Commits

- **The operator owns commits.** A role never runs `git commit` unless the
  operator's current request explicitly asks for one.
- Handoff is not a commit and not a copy. The next role works on the same files
  and reads your changes directly; there is nothing to merge.
- When the operator does ask for a commit, follow the Angular commit convention:

  ```text
  <type>(<scope>): <subject>

  <why this change was needed>
  ```

  | type | use for |
  |---|---|
  | `feat` | new behavior |
  | `fix` | corrected behavior |
  | `refactor` | structure changed, behavior unchanged |
  | `perf` | a measured speed or resource win |
  | `docs` | specs, design views, comments |
  | `test` | tests or the acceptance pipeline |
  | `build`, `ci` | dependencies, tooling, pipeline |
  | `chore` | housekeeping with no behavior change |
  | `revert` | undoing an earlier commit |

  - **Subject**: imperative, lower case, no trailing period, 72 characters or fewer.
  - **Scope**: the subsystem or area, lower case — `safety-rule-engine`, `docs`,
    `tools`, `detector`.
  - **Body**: why, not what. Wrap at 72. Omit it when the subject says enough.
  - **Breaking change**: add `BREAKING CHANGE: <what breaks>` as the last
    paragraph.
  - **No role attribution.** The commit is the operator's. The message names the
    change, not the agent that produced it, and keeps no byline.

- One commit per task. Do not mix unrelated changes into it.
- To undo a role's work before it is committed, revert only the files that role
  reported. Never discard another role's changes.

## Scratch Files

- Use `$PROJECT/<artifacts root>` for drafts, IR, and dry-check reports.
- Delete an artifact before you regenerate it. A file left by an earlier run is
  indistinguishable from a fresh one, and can make a stale check look green.
- Do not use the system temporary directory, and do not leave scratch files in
  the project's tracked directories.

## Failure

- Stop and report when the spec and the tests disagree, when a gate fails for a
  reason outside your ownership, or when the task needs a decision only the
  operator can make.
- Never silence a failure to make a gate pass.
