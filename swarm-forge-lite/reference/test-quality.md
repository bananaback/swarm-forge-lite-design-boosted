# Test Quality

Grounded in Beck, Martin (FIRST), Feathers, Meszaros/Fowler, Meyer, Myers/Beizer, DeMillo. Decide every rule below by a line, a grep, or a run - never by taste.

## A good test, and how you measure it

- **One behavior.** The name states it. The body is arrange-act-assert. *Fail* if one test asserts two behaviors or its name states none.
- **In memory, isolated, repeatable.** *Fail* if it uses the real clock, network, filesystem, or random, or reads state that another test wrote. Grep the test for `time`, `now(`, `random`, `socket`, `requests`, `open(`, or a module-level value shared between tests.
- **A real oracle.** *Fail* if the only assertion is `is not None`, a truthiness check, a status code, or `raises(Exception)`. The oracle must be an exact value or the exact typed error.
- **Mutation-honest.** Name the plausible wrong implementation that it fails. *Fail* if you cannot.
- **A fake, not a mock of the subject.** *Fail* if a Mock replaces the thing under test or an internal collaborator whose outcome is observable, or the assertion is that a method was called or called in a given order. A fake behind a seam, asserted by outcome, passes.
- **Chosen cases.** For each behavior: one happy path, at least one boundary (zero, one, many, empty, max, off-by-one), and at least one refusal or failure path. *Fail* if the module has several success paths and no boundary and no failure.
- **Binds the symbol, not the literal.** A test that depends on a declared value reads it from the declaration (`WINDOW`, `declaration.window()`), never scans a source or data file for the literal (`"30.0"`). *Fail* if changing the declared value forces the test's logic to change.

## The smells - fail when you can point to it

| Smell | The observable that fails it |
|---|---|
| No oracle / Assertion Roulette | an assert that is `is not None` / truthy / `raises(Exception)`, or many asserts with no message |
| Eager Test / Lazy Test | one test asserting several behaviors, or several tests asserting one |
| Mystery Guest | a path, file, or fixture that the test reads but does not create |
| Invented fixture | a payload or schema that the real code rejects |
| Erratic Test / shared fixture | the two runs differ, or a value left by another test |
| Fragile Test | an assert on a private name, an extra unrelated key, or an exact call order |
| Slow Test | runtime in seconds, not milliseconds |
| Duplicated setup | the same arrange block as a neighbor where a fixture exists |
| Over-Mocking | a Mock where a fake fits, or the subject mocked |
| Coverage chasing | a test whose only assert is that a call happened |
| Framework boilerplate | an assert that a dataclass set a field, or an ORM round-tripped a string |
| God Test | one long walk that asserts many things, where the first failure hides the rest |
| Value-coupled test | the test greps a source or data file for the literal of a value that a declaration owns; bind the symbol instead |
| Stale check | the test is not in the accepted design, or a check was edited to pass |

## Verdict

Reject when you can point to a no-oracle, non-isolated, non-mutation-honest, over-mocking, or happy-path-saturated test. Accept otherwise, with at most a few cosmetic notes, each logged.
A finding states the test, the smell by name, the line or run that fails it, and the fix.

Evidence: run the suite, run it again, and note the runtime.
