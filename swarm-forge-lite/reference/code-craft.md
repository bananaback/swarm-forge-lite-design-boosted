# Code Craft - Clean Code, and readability first

Read on demand. This file holds the code-writing rules for the `coder`, the
`refactorer`, and the `hotfixer`. The design rules are in `design-craft-design.md`;
the test rules are in `test-quality.md`.

## Readability first

- Code is read far more than it is written. Write for the next reader.
- Simple presentation, correct logic. Make the code easy to read. Never make the
  logic dumber to make it shorter.
- **No one-liners.** One statement for each line. Do not pack a call chain, a
  comprehension, or a nested conditional into one dense line.
- **Do not show off.** Use no clever trick, no shiny new library, no
  metaprogramming, no magic, when a plain loop, a plain function, or a plain `if`
  does the job. A plain loop the reader can follow beats a clever one-line
  comprehension.
- Name things so the reader needs no comment. If a line needs a comment to be
  understood, rewrite the line.
- Delete commented-out code. Version control remembers it.

## Naming

- A name reveals intent: a reader learns what it is and why.
- No disinformation, and no noise word (`data`, `info`) that adds nothing.
- No encoding: no Hungarian notation, no type prefix.
- Searchable and pronounceable. The length follows the scope: a short name for a
  short scope, a long name for a long scope.
- A class is a noun. A method is a verb.

## Functions

- Small, and then smaller.
- One thing, at one level of abstraction.
- Few arguments. 0-2 is ideal. 3 is a smell. A boolean flag argument is a smell:
  split the function.
- No hidden side effect. A **Command** changes state and returns nothing. A
  **Query** returns data and changes nothing.
- Prefer an exception to an error code.
- Extract the body of a `try` / `catch` into its own function.
- DRY. Duplication is the root of much evil. One policy, one place.

## Comments

- A comment is often a failure to express yourself in the code.
- Keep: a legal note, an intent note, a warning, a `TODO`, a public API doc.
- Delete: a redundant comment, a misleading comment, noise, commented-out code.

## Docstrings

- A docstring says what the function does and why, in plain language. It never
  restates the signature, the types, or the obvious.
- Keep it short: one line for a simple function, one short paragraph for a real
  contract. A wall of text helps nobody.
- **No design id in code.** Never cite a record id (`C68`, `R80`, `AC5`, `D11`) in a
  docstring or a comment. The code stands alone; the id belongs in the record.
- Document the contract only when it is not obvious: a precondition, a postcondition,
  an invariant, an error it raises, or a surprising behavior. Nothing else.
- A private helper whose name already says what it does needs no docstring. A
  redundant docstring is worse than none.
- Do not narrate the body line by line. The code says how; the docstring says why.

## Formatting

- One team style. The tool (`ruff`) holds it.
- Related code stays vertically close.
- The newspaper: the high level at the top, the detail below.

## Objects and data structures

- An object hides its data and exposes behavior.
- A data structure exposes its data and has no behavior.
- Law of Demeter: do not chain through the internals of another object
  (`a.get_b().get_c().do_x()`).

## Error handling

- Use an exception, not a return code.
- Do not return `None` and do not pass `None`. Use a special-case object or an
  empty collection.
- Wrap a third-party API behind your own interface.

## Boundaries

- Isolate third-party code behind your own interface.
- Write a learning test for an external library.

## Unit tests

- TDD, three laws: write a failing test first; write only enough test to fail;
  write only enough code to pass.
- A test is clean too. F.I.R.S.T.: Fast, Independent, Repeatable, Self-validating,
  Timely.
- One concept for each test. Readability counts as much as in the source.
- The full rubric is in `test-quality.md`.

## Classes

- Small, with one responsibility: one reason to change.
- High cohesion: the methods use the class's fields.
- Open/Closed. Depend on an abstraction (Dependency Inversion).

## Systems

- Separate construction from use (injection, a factory).
- Keep a cross-cutting concern separate.
- Grow the architecture as the code needs it. Do not plan it all up front.

## Emergence - Beck's four rules of simple design, in order

1. It runs all the tests.
2. It has no duplication.
3. It expresses intent.
4. It minimizes the classes and the methods.

## Concurrency

- Keep the concurrent code separate. Limit the shared data and its scope.
- Use a copy of the data. Keep a synchronized section small.

## Smells and heuristics

Rigidity, fragility, immobility, needless complexity, needless repetition, dead
code, an inconsistent convention, a magic number, feature envy, a long parameter
list.

## Earn its keep (economy)

Every class and every helper earns its keep: a guard, a boundary, or a scope
answer. Otherwise it is a name, not a guard. Keep the plain value or the plain
function. Never trade a guard for fewer lines. The full test is in
`design-craft-design.md` section Economy.

## The Boy Scout rule

Leave the code a little cleaner than you found it.
