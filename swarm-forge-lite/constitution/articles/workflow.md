# Workflow

## Workspace
- Work in the shared project directory. No worktrees, branch switches, or other branches unless directed.
- Never inspect, diff, merge, or rebase another role's uncommitted work.

## Reading
- Read only the inbound message, the feature/IR, and the contracts your role names. Do not re-read your role prompt or the constitution.

## Commits
- Angular: `<type>(<scope>): <summary>`, imperative, lowercase, no period; body wrapped at 72 columns. Types: build, ci, docs, feat, fix, perf, refactor, test.
- The operator owns commits. A role commits or pushes only when the operator explicitly asks; use the operator's message, or the Angular form above when none is given. Never commit unrelated changes or generated artifacts.
- Handoffs never wait for, require, or reference a commit.

## Temp Files
- Use `./tmp/` in the project directory, not `/tmp`. Parse and dry-check into the artifacts root.

## Failure
- Missing project directory or required inputs: stop and report; do not guess.
