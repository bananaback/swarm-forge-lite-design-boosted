# Design Craft — the front end (requirement before design)

Read on demand. The workflow names a technique; this explains what it is, how to
apply it, and the failure it prevents. Reach for the named concept when a decision is
unclear. The design techniques are in `design-craft-design.md`.

These run before any structure exists, and before any Gherkin is written. Each names the
artifact it produces.

## Context-free questions — Gause & Weinberg (1989)
- Ask before a solution exists: who is the *real* client; what is a successful solution; what
  is the real reason for the ask; what would make it fail; who decides.
- The requirement lives in the person, not the words. No matter what they tell you, the problem
  is never stated the way you need it.
- Failure prevented: solving the stated problem instead of the real one.

## Perfect-technology filter — essential systems analysis (McMenamin & Palmer, 1984)
- Describe the behaviour as if the machine were free and instantaneous. What must be true about
  the world, ignoring how any technology would achieve it.
- Failure prevented: design decisions written as requirements.

## SCR — Parnas's tabular requirements (Parnas et al., 1978, NRL A-7E)
- The behaviour is a set of **tables**, not prose. The four-variable model: **monitored**
  (environment → system), **controlled** (system → environment), **input** and **output**
  (internal, derived). A requirement relates monitored and controlled variables only.
- Tabulate: the **mode transition table** (mode × event → next mode), the **event table**
  (event × condition → `@T` / `@F` / `@C`), and the **condition table** (condition × mode → T/F).
- The correctness property is the point: **completeness** — every mode × event has an entry;
  **disjointness** — no mode × event has two. A hole is an unstated behaviour; a double is two
  rules that disagree. Both are defects found before code.
- Failure prevented: behaviour nobody stated, and rules that silently contradict.
- Verify the exact table set against Parnas/NRL sources before citing it in a spec.

## KAOS — goals, obstacles, anti-goals (Dardenne, van Lamsweerde, Fickas, 1993)
- Refine the goal AND/OR until a leaf can be satisfied by **one agent**; that leaf is a requirement.
- For every goal leaf ask what could obstruct it. An obstacle refines until it is **resolved** by a
  requirement or **explicitly excluded** with a reason. Write one **anti-goal** per top goal.
- Failure prevented: a goal with no owner, and the consequence of an exclusion never questioned.

## Fit criterion — Gilb (1988, 2005)
- Scale · Meter · Target on every requirement. No fit criterion, no requirement.
- Failure prevented: "fast", "robust", "user-friendly" reaching code.

## EARS — sentence patterns (Mavin et al., 2009)
- Five patterns: Ubiquitous, Event-driven (`When …`), State-driven (`While …`),
  **Unwanted behaviour** (`If …, then …`), Optional feature (`Where …`).
- Every requirement matches exactly one pattern; no match means it is not one requirement.
- Failure prevented: compound, ambiguous requirement sentences.

## Cockburn's extensions (2001)
- Every numbered step of the main success scenario gets its own numbered extensions list: what
  can go wrong *at that step*.
- Failure prevented: only the happy path specified.

## Fagan inspection (1976) — the second pair of eyes
- The author does not inspect their own record. A second party runs the checklist and reports
  defects; the report is the proof the checklist ran.
- Failure prevented: a self-reported checklist with no evidence it was ever run.

## Traceability matrix
- Rn → ACn → scenario → contract → test, **both directions**. A row that cannot be completed is
  the defect: an unowned requirement, or an orphan test.
- Failure prevented: drift between what was required and what was built.
