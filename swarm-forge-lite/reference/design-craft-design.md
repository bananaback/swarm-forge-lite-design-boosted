# Design Craft — the design techniques

Read on demand. The workflow names a technique; this explains what it is, how to
apply it, and the failure it prevents. Reach for the named concept when a decision is
unclear. The front-end techniques are in `design-craft-front.md`.

## Parnas — information hiding / secrets (1972)
- A module is a decision likely to change (storage, vendor SDK, algorithm, wire format).
- One secret per module. If two modules guard the same volatile decision, merge. If one
  guards two unrelated ones, split.
- What good looks like: you can name the one thing that would change inside the module
  and nothing outside it changes.
- Failure prevented: a change rippling across the system because a decision was never
  contained.

## Abbott — noun-verb grammar analysis (1983)
- Nouns -> candidate classes/attributes; verbs -> candidate methods (`verb — subject: noun`);
  adjectives -> attributes/subtypes; prepositional phrases -> relationships.
- Merge synonyms; log the discarded alias. Stop when a second pass adds nothing.
- Cross-cutting verbs (`validate`, `persist`, `log`, `retry`, `notify`) get one owning
  card, not a copy per card.
- Failure prevented: classes invented from intuition instead of from the requirement's own
  words.

## Meyer — Design by Contract + Command-Query Separation (1988)
- Precondition (what must hold on entry), postcondition (what is guaranteed on return),
  invariant (a domain truth always true between calls).
- A **Command** mutates and returns nothing. A **Query** returns data and mutates nothing.
  Never both: split into a Query that computes and a Command that applies.
- What good looks like: the contract is one clause each; a caller can trust it without
  reading the body.
- Failure prevented: invisible side effects on read paths.

## Beck & Cunningham — CRC cards (1989)
- One card per class: **Class | Responsibility | Collaborator**.
- Walk every acceptance check card to card, passing an imaginary token; a step with no
  owning card creates one now.
- Failure prevented: a responsibility with no home, discovered only at code time.

## Tell, Don't Ask + Law of Demeter (1988–89)
- Do not pull data out of an object to decide outside it; command the object to decide.
- A method speaks only to self, its parameters, and its locals — no chain deeper than one
  dot past those.
- Failure prevented: a class coupled to its collaborators' internal topology.

## Functional Core / Imperative Shell
- Tag each responsibility I/O or PURE; split any that is both into a fetch step and a
  decide step.
- All-PURE class = Core; any-I/O class = Shell. Core owns the decisions; Shell owns the
  messiness.
- Failure prevented: business rules tangled with the network, disk, clock, or SDK.

## SOLID as operational questions
- **SRP:** "Who is the one actor that can demand this class change?" Two answers -> split.
- **OCP:** "Can a new requirement be a new file instead of an edit?" An `elif` before a
  branch is the smell.
- **LSP:** "Can I swap any implementation without the caller knowing?" Thrown
  "not supported" or an ignored parameter is a violation.
- **ISP:** "Does a client know methods it never calls?" Trim to 1–2 role-based methods.
- **DIP:** "Does policy depend on mechanism?" Core declares a small interface in its own
  vocabulary; Shell implements it. State it as "core needs X, shell satisfies X" — never
  as ports, adapters, entities, or bounded contexts.

## Beck's Four Rules of Simple Design (late 1990s), in priority order
1. Passes the tests.
2. Reveals intention (name says what/why).
3. No duplication (one policy, one place).
4. Fewest elements (no speculative abstraction).

## Quality definitions — what good looks like
- **CRC card:** a responsibility sentence with no "and"; collaborators are the fewest that
  let every acceptance check walk through.
- **Secret:** one volatile decision, nameable in a phrase, invisible outside the class.
- **Contract:** one clause pre, one clause post, one invariant; exactly one CQS tag.
- **Interface:** 1–2 methods, each needed by a real client, contract-matched by every
  implementer.
- **Test name:** a plain `test_<criterion>` that names the observable behavior, not the
  implementation.
