# Workflow

The working rules that every role shares: where to work, when to stop, what to
read, how to search, the commit format, the temporary files, and the failure rule.

## Workspace
- Work in the shared project directory.

## Execution
- Write the artifact as you go. Do not draft it in reasoning. Fill the section, run the check of your role, fix the finding, and move on.
- Stop condition: stop when the command of your role is green. Do not re-derive the record and do not explore after it passes.
- Run each command once. Re-run it only after a change. The full suite and every feature run once, at the terminal gate.
- A gap you cannot fill is an `ASSUMED:` line, a `DECISION`, or a `blocked` report. Never invent a value to close a cell.

## Reading
- Read the inbound message, the feature or IR, and the contracts that your role names.

## Search
- CodeGraph is available in an indexed repository. Use it when it fits the task, for example a symbol's source, a call path, or the blast radius of a change. Choose the tool that the task needs.
- Find a file with the `glob` tool, and find text with the `grep` tool. Prefer them to a shell search.
- Resolve a known path first with `<pack>/tools/shared/harness.py status` (PACK, WORKSPACE, SOURCE, PERSIST, FEATURES, SPECS). Then search that path.
- Do not scan the whole filesystem, `$HOME`, or a wide tree when a known path exists. This applies to `find`, a recursive `grep`, `locate`, and every slow search. A wide scan is slow and returns little.
- Run a wide search only when the task truly needs it. Scope it to one root, bound the depth (`-maxdepth`), and stop when the result is found.

## Commits
- Angular format: `<type>(<scope>): <summary>`. Use the imperative form, lowercase, and no period. Wrap the body at 72 columns. Types: build, ci, docs, feat, fix, perf, refactor, and test.
- The operator owns the commits. Use the message from the operator. When the operator gives no message, use the Angular format above.
- Commit one at a time. The project is a git repository. Two sessions that commit at the same time contend on `.git/index.lock`.

## Temporary Files
- Use `./tmp/` in the project directory, not `/tmp`. In a lane, `TMPDIR` already points to the artifacts root of this lane. Parse and dry-check into the artifacts root.

## Failure
- If the project directory or a required input is missing, report it and continue where you can.
- If a command, a tool, or a path is not permitted, stop. Report the exact command and the exact error with the blocked status of your role. Do not work around the denial. Do not change permissions or ownership. Do not use elevated privilege. Do not install, configure, or change the environment. The operator performs the action.
