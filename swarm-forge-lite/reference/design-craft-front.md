# Design Craft - the front end (requirement before design)

Read on demand. Each technique states how to apply it and the failure that it prevents. Use the named concept when a decision is unclear. The design techniques are in `design-craft-design.md`.

Apply these techniques before any structure exists and before any Gherkin is written. Each one names the artifact that it produces.

## Context-free questions - Gause & Weinberg (1989)
- Ask before a solution exists: who is the *real* client, what is a successful solution, what is the real reason for the ask, what would make it fail, who decides.
- The requirement lives in the person, not the words. No matter what they tell you, the problem is never stated the way you need it.
- Failure prevented: a fix for the stated problem rather than the real problem.

## Perfect-technology filter - essential systems analysis (McMenamin & Palmer, 1984)
- Describe the behavior as if the machine were free and instantaneous. State what must be true about the world, and ignore how any technology would achieve it.
- Failure prevented: design decisions written as requirements.
- The test is lexical, so it is cheap. A requirement, a constraint, a definition or a scope line names NO token in code marks, NO path, NO file name, NO class or element name, NO framework or library name. Write the words of the operator's world: the subject, the action and the value.
- Every item below leaks a machine noun: a token in code marks (`Latch`, `cache-size`, `duration`, `nvdsosd`, `SOURCE_KIND`), a path (`app/pipeline/source/source.py`, `docker/host/apply.sh`), a file extension, a class or callback name (`KeptState`, `handle_metadata`), a library call (`Node.set()`, `pipeline.stop()`), and a framework name (`pyservicemaker`, `onnx`).
- A class name and a path belong to the DESIGN record, and nowhere else. The design record is the one place that names the machine. `record.py` reads every line of the business sections and of the spec document, and it exempts the design record.

## SCR - the tabular requirements of Parnas (Parnas et al., 1978, NRL A-7E)
- The behavior is a set of **tables**, not prose. The four-variable model: **monitored** (environment -> system), **controlled** (system -> environment), **input** and **output** (internal, derived). A requirement relates monitored and controlled variables only.
- Tabulate: the **mode transition table** (mode x event -> next mode), the **event table** (event x condition -> `@T` / `@F` / `@C`), and the **condition table** (condition x mode -> T/F).
- The correctness property is the point. **completeness** - every mode x event has an entry. **disjointness** - no mode x event has two. A hole is an unstated behavior. A double is two rules that disagree. Both are defects found before code.
- Failure prevented: behavior that nobody stated, and rules that contradict in silence.
- Verify the exact table set against the Parnas/NRL sources before you cite it in a spec.

## KAOS - goals, obstacles, anti-goals (Dardenne, van Lamsweerde, Fickas, 1993)
- Refine the goal AND/OR until **one agent** can satisfy a leaf. That leaf is a requirement.
- For every goal leaf, ask what can obstruct it. An obstacle refines until a requirement **resolves** it or an explicit exclusion with a reason **excludes** it. Write one **anti-goal** for each top goal.
- Failure prevented: a goal with no owner, and the consequence of an exclusion that nobody questions.

## Fit criterion - Gilb (1988, 2005)
- Scale - Meter - Target on every requirement. No fit criterion, no requirement.
- Failure prevented: "fast", "robust", and "user-friendly" that reach the code.

## EARS - sentence patterns (Mavin et al., 2009)
- Five patterns: Ubiquitous, Event-driven (`When ...`), State-driven (`While ...`), **Unwanted behavior** (`If ..., then ...`), Optional feature (`Where ...`).
- Every requirement matches exactly one pattern. No match means it is not one requirement.
- Failure prevented: compound, ambiguous requirement sentences.

## Cockburn's extensions (2001)
- Every numbered step of the main success scenario gets its own numbered extension list: what can go wrong *at that step*.
- Failure prevented: only the happy path specified.

## Fagan inspection (1976) - the second pair of eyes
- The author does not examine their own record. A second party runs the checklist and reports the defects. The report is the proof that the checklist ran.
- Failure prevented: a self-reported checklist with no evidence that it ever ran.

## Traceability matrix
- Rn -> ACn -> scenario -> contract -> test, **in both directions**. A row that you cannot complete is the defect: an unowned requirement, or an orphan test.
- Failure prevented: drift between what was required and what was built.
