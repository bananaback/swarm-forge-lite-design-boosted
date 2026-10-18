# Design Craft - the design techniques

Read on demand. Each technique states how to apply it and the failure that it prevents. Use the named concept when a decision is unclear. The front-end techniques are in `design-craft-front.md`.

## The record boundary - where a machine name may live
- The requirement record (`requirements.md`) and the spec document (`docs/specs/NN-<subsystem>.md`) state the business only. A class name, a method name, a path, a file name, a config key and a library call do not appear there. `record.py` reports each one as a `machine-noun` finding.
- The design record (`architecture.md` and `modules/<module>.md`) is the one place that names the machine. Name the classes, the modules, the paths and the interfaces there, with no restraint.
- Failure prevented: a design decision that the spec freezes as a requirement, so a later rename costs a spec change and a requirement change across eight documents.

## Parnas - information hiding / secrets (1972)
- A module is a decision that can change (storage, vendor SDK, algorithm, wire format).
- One secret for each module. When two modules guard the same volatile decision, merge them. When one module guards two unrelated decisions, split it.
- Good: you can name the one thing that changes in the module, and nothing outside the module changes.
- Failure prevented: a change that moves across the system because a decision was never contained.

## Abbott - noun-verb grammar analysis (1983)
- Nouns -> candidate classes and attributes. Verbs -> candidate methods (`verb - subject: noun`). Adjectives -> attributes and subtypes. Prepositional phrases -> relationships.
- Merge synonyms. Log the discarded alias. Stop when a second pass adds nothing.
- A cross-cutting verb (`validate`, `persist`, `log`, `retry`, `notify`) gets one owning card, not a copy for each card.
- Failure prevented: classes invented from intuition instead of from the words of the requirement.

## Meyer - Design by Contract + Command-Query Separation (1988)
- Precondition (what must hold on entry), postcondition (what is guaranteed on return), invariant (a domain truth that is always true between calls).
- A **Command** changes state and returns nothing. A **Query** returns data and changes nothing. Never both: split into a Query that computes and a Command that applies.
- Good: one clause for each part of the contract. A caller can trust it without reading the body.
- Failure prevented: invisible side effects on read paths.

## Beck & Cunningham - CRC cards (1989)
- One card for each class: **Class | Responsibility | Collaborator**.
- Walk every acceptance check card to card with an imaginary token. A step with no owning card creates one now.
- Failure prevented: a responsibility with no home, found only at code time.

## Tell, Don't Ask + Law of Demeter (1988-89)
- Do not pull data out of an object to decide outside it. Command the object to decide.
- A method speaks only to self, its parameters, and its locals. No chain deeper than one dot past those.
- Failure prevented: a class coupled to the internal topology of its collaborators.

## Functional Core / Imperative Shell
- Tag each responsibility I/O or PURE. Split a responsibility that is both into a fetch step and a decide step.
- All-PURE class = Core. Any-I/O class = Shell. Core owns the decisions. Shell owns the messiness.
- Failure prevented: business rules tangled with the network, the disk, the clock, or the SDK.

## SOLID as operational questions
- **SRP:** "Who is the one actor that can demand a change to this class?" Two answers -> split.
- **OCP:** "Can a new requirement be a new file instead of an edit?" An `elif` before a branch is the smell.
- **LSP:** "Can I swap any implementation without the knowledge of the caller?" A thrown "not supported" or an ignored parameter is a violation.
- **ISP:** "Does a client know methods that it never calls?" Trim to 1-2 role-based methods.
- **DIP:** "Does policy depend on mechanism?" Core declares a small interface in its own vocabulary. Shell implements it. State it as "core needs X, shell satisfies X" - never as ports, adapters, entities, or bounded contexts.

## Beck's Four Rules of Simple Design (late 1990s), in priority order
1. Passes the tests.
2. Reveals intention (the name says what and why).
3. No duplication (one policy, one place).
4. Fewest elements (no speculative abstraction).

## Economy - does the abstraction earn its keep? (Beck Rule 4; YAGNI)
Ask this of every class, interface, seam, and split:
**what does this catch that the plain value or the plain function would not?**

An abstraction earns its keep for one of three reasons, and no other:
1. **A guard.** It refuses an invalid value, holds an invariant, or stands on a
   boundary the app already exposes. A type, a contract, a test.
2. **A boundary.** It sits where an external system or a test seam already is.
3. **A scope answer.** The scope gate names a near-term use case that needs it.

If none holds, it is a **name, not a guard**. Keep the plain value or the plain
function. Do not make a file for a concept that carries no guard and no answer.

- **Never trade a guard for fewer lines.** Economy removes structure that is not a
  guard. It never removes a type, a contract, a test, or an invariant. Minimal code
  with no guards is a bug farm, not economy.
- **Balance with readability.** A split must lower the load of the reader. When it
  only adds files to open, it is fragmentation, not separation. One responsibility,
  one file. One secret, one module. Not one value, one file.
- **YAGNI.** Do not add an extension point, an interface, or a split for a future
  the scope gate excludes. A speculative seam is a defect, not a gift.

## Quality definitions - what good looks like
- **CRC card:** a responsibility sentence with no "and". The collaborators are the fewest that let every acceptance check walk through.
- **Secret:** one volatile decision, nameable in a phrase, invisible outside the class.
- **Contract:** one clause pre, one clause post, one invariant. Exactly one CQS tag.
- **Interface:** 1-2 methods, each needed by a real client, contract-matched by every implementer.
- **Test name:** a plain `test_<criterion>` that names the observable behavior, not the implementation.
