# Workflow

## Execution

- Work in the project workspace.
- Write the artifact as you go. Do not draft it in reasoning.
- Run each command once. Run it again only after a change.
- Run the full suite and every feature once, at the terminal gate.
- Stop when the role's stop test is green.

Stop condition: every `VERIFY` command has run, its exit code is recorded, and
the role's protocol block is complete.

## Search

- Name the target path before searching.
- Use `codegraph explore` when the tree is indexed.
- Use `glob` for file names and `grep` for text. Scope one root, with a bound.
- Never scan the whole filesystem, `$HOME`, `dump/`, or a generated cache.

## Gaps

- A gap is `ASSUMED:`, a `DECISION` row, or `blocked`.
- Never invent a value.
- A missing input is reported. Continue only where the work does not depend on it.

## Temporary files

- Use `./tmp/` in the project. Inside a lane, `TMPDIR` already points at the
  lane's artifact root.
- Working notes are disposable. The durable record is the four flat files.

## Commits

- The operator owns commits. Commit or push only when the operator asks.
- Format: Angular `<type>(<scope>): <summary>`, imperative, lowercase, no period,
  body wrapped at 72 columns.
- Commit one at a time. Never commit generated files, artifacts, or `hot_tests/`.

## Failure

- A denied command, tool, or path is a hard stop.
- Report the exact command and the exact error.
- Do not work around it. Do not change permissions, elevate, install, or reconfigure.
