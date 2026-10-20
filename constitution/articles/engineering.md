# Engineering Rules

## Design And Testability

- Work in small, reviewable increments. Prefer the simplest design that
  supports the current behavior.
- Keep new behavior in testable modules. Put code that opens GUIs, touches
  devices, or hangs under automation behind small adapter boundaries.
- Adapters must not reimplement a domain question. If a high-level module
  already answers it, call that module and translate the result.
- Keep tests separate from test helpers.

## Behavior Before Code

- Write the failing test first, and make it fail for the intended reason.
- Then write only enough production code to pass it.
- Do not treat generated acceptance tests as a substitute for unit tests.
- Keep unit tests fast. Use property tests only where the role owns them.

## Acceptance Pipeline

- Gherkin is the behavioral specification. Its tools come from the Acceptance
  Pipeline Specification, vendored under `tools/shared/aps/`.
- Normal run: `gherkin-parser` → JSON IR → `gherkin-ir-dry-checker` →
  project acceptance generator → generated tests → project runner.
- Keep generated acceptance tests separate from unit tests, and never edit
  generated files by hand.
- Gherkin acceptance mutation and language mutation are **not part of this
  pack**. Do not run them, install them, or imitate them.

## Verification

- Run every command from the project root, exactly as written in
  `tools/README.md`. Do not invent proxies, and do not treat a homegrown script
  as one of the named tools.
- Clean means the command exits 0. Findings printed by an analysis tool are
  advisory — report the counts, do not edit code to silence them unless the task
  asks for that.
- Run heavy tools one at a time. Never run lint, tests, duplicate analysis, and
  CRAP concurrently.
- Format the files you touch. If a file was never formatted, say so in your
  report: a whole-file reformat buries the functional change inside noise.
- A claim of green requires the exact command and its exit status. A count is
  not a verdict.

## Guardrails

- Do not touch unrelated files or generated artifacts.
- Replace a bare `except:` with the narrowest exception you can name. If you
  cannot name one, use `except Exception` and say why; never `BaseException`.
- Do not edit analysis manifests or reports by hand.
- Before relying on an unfamiliar command, read `tools/README.md` or its
  `--help`.
