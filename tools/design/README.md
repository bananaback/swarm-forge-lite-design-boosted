# Design specs and the design surface

A spec is the engineering contract for one subsystem: how it is built, how a
frame or a call moves through it, and how to extend it without breaking the
shape. Behavior is not here — `tests/features/` is its only statement — and
neither are tests or acceptance criteria. Those belong to the specifier and the
coder.

## The spec

Every `<PROJECT>/<docs_root>/specs/NN-<subsystem>.md` has the same six sections
(`docs_root`, and the `specs` list that names each file, are entries in the
selected project's block in `config/pack.json`):

| Section | Holds |
|---|---|
| **Responsibility** | what the subsystem owns and refuses to own, in technical terms |
| **Structure** | packages, core vs shell, dependency direction, composition root, the seam |
| **Classes** | one row per class: what it does and who it works with. This is the legend for the class diagram |
| **Flow** | the mechanism in order: what receives, stores, decides, emits |
| **Design rules** | constraints to preserve, and the sanctioned way to extend |
| **Rejected** | shapes refused, with the reason |

Then one footer line: the feature that pins the behavior.

Open `<PROJECT>/<docs_root>/diagrams.html` on one side and the spec on the other: every box in the
diagram has a row in `## Classes`, every arrow is explained by `## Flow` or
`## Design rules`. `## Flow` answers "how do I achieve it"; `## Design rules`
answers "how do I extend it".

Rule: a spec carries **no test path, test name, acceptance criterion or
requirement id**. If a class is added, renamed or moved, the same change updates
its row and any flow step that names it.

## The model and the views

```sh
python3 <PACK>/tools/design/arch.py classes ls|show|deps|validate
python3 <PACK>/tools/design/arch.py runtime ls|show|validate
python3 <PACK>/tools/design/arch.py docs validate
python3 <PACK>/tools/design/arch.py render [classes|runtime|all]
```

- `classes` scans the code on every call; there is no stored class model to drift.
- `classes add node` stores the `--layer` it is given on the node, so the class
  view renders it without a later `annotate`.
- `classes add edge` accepts `--from`/`--to`; the positional id is optional and is
  derived as `<from>-><to>` when omitted. The legacy `<id> <from> <to>` form works.
- `runtime` reads `<PACK>/architecture/runtime.json`; `validate` fails when a
  subsystem under `app/pipeline` has no box.
- `docs validate` checks every spec against the model: all six sections present,
  every class described, no test or acceptance reference, and every class named in
  a `## Classes` table exists in the scanned code or is declared in the design
  overlay.
- `<PROJECT>/<docs_root>/diagrams.html` and `ARCHITECTURE.html` are generated outputs. Never edit them.

`umlview` remains the module-grade view (CRAP, dependency-rule violations) and is
not involved here.

There is no test map and no design archive. Tests mirror the app layout
so an agent finds them by path.
