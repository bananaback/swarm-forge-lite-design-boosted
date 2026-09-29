# Gherkin Craft

A feature is a set of falsifiable claims about externally observable behavior.
The scenarios are the contract; the implementation is the variable.

Lineage: structured analysis (DeMarco; Constantine & Yourdon), design by
contract (Meyer), information hiding (Parnas), structured programming
(Dijkstra), conceptual integrity (Brooks), behavior-driven development (North).
The rules below are those disciplines applied to one feature file.

## A correct, high-quality scenario

It passes four tests.

1. **Falsifiable** (Dijkstra). Name a plausible wrong implementation that fails
   it. If you cannot, it asserts nothing; a test shows a bug's presence, never
   its absence.
2. **Implementation-free** (Parnas). Rewrite the internals and it still runs
   unchanged. It states what an observer sees, never how it is made — no
   widgets, selectors, functions, fields, endpoints, storage, schema, call
   order, algorithm.
3. **Contract-shaped** (Meyer). `Given` is the precondition, `When` the one
   event, `Then` the postcondition. The outcome follows from the trigger, never
   echoing the setup, or a wrong implementation passes by repeating its input.
4. **One job** (Constantine; Mills; Martin). One rule per scenario, one
   observation per step, exactly one `When`. Two rules give a failure that
   cannot localize; two observations in a step give a pass of ambiguous meaning.

## The disciplines

- **High cohesion, low coupling.** A scenario uses `Background` and its own
  steps, nothing else. It passes alone, first, last, in any order.
- **Hide the representation.** Name concepts, not tables or types. If renaming
  storage edits a scenario, design leaked in.
- **Ubiquitous language** (Evans). Domain words, spelled one way. No code
  identifiers. Reuse one step shape before inventing a near-identical one.
- **Conceptual integrity** (Brooks). One feature per file, one vocabulary, one
  style; it reads as one mind's work.
- **Determinism** (Hoare). Concrete values, present tense, third person.
  Replace `some`, `several`, `valid`, `appropriate`, `quickly`, `soon`; no
  `I`/`you`, no `should`, no `if`/`for each`.
- **Parameterize variation, delete constants** (Hunt & Thomas). Every
  `<placeholder>` names an example column, and every column is read by one. A
  column constant across all rows is a plain scenario in costume.
- **Boundaries first** (Gilb; Weinberg). Pin empty, zero, one, many, maximum,
  duplicate, missing, exact threshold. A happy path alone proves little.
- **Bad news is explicit** (Hoare). Errors are first-class scenarios that state
  the observable failure — rejected, refused, unchanged, exits 2 — never "an
  error occurs".
- **Minimal context.** `Given` states only what the `When` needs; incidental
  detail hides the rule and couples the scenario to unrelated parts.
- **As short as its rule allows** (Beck). A long scenario hides more than it
  says.

## Bad patterns

- Mechanism leaked: `click #login`, `the sessions table holds a non-null token`.
- Vague: `several results are returned quickly`.
- Tautology: `Given 100 / When withdraw 120 / Then balance 100`.
- Two rules joined: `Then denied and balance unchanged and an alert sent`.
- Order dependence: scenario 2 assumes scenario 1 ran.
- Failure by omission: `Then the command fails`.
- Synonym drift: one idea, three spellings; one shape, three handlers.
- Costume outline: an `Examples` table with one distinct value.
