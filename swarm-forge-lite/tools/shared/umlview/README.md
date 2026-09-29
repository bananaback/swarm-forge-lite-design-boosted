# umlview — a lightweight, data-driven Python UML view

The design source of truth is a JSON model. `render.py` turns it into one standalone
HTML page (inline SVG) you reload with F5. No server, no realtime, no mailbox, no Quil,
no agent bridge — the only communication is you and the agent in chat.

Adapted from unclebob/uml-viewer: the same idea (a small typed IR, components → classes →
typed edges, a levels-derived dependency rule that paints violations red), stripped to the
part that pays off in a text-only agent workflow.

## Files

| File | Role |
|---|---|
| `render.py` | model.json → standalone `*.html`; computes the findings |
| `template.html` | the page: dagre layout + inline SVG, hover/click JS, findings panel |
| `vendor/dagre.min.js` | the layout engine, bundled so the HTML works offline (no CDN at view time) |
| `scan_python.py` | optional: Python source → model.json (a starting point) |
| `example.model.json` | a clean design (evidence recorder) |
| `example.violation.model.json` | deliberate violations, to see the red |

The format is documented in `swarm-forge-lite/reference/model-format.md`.

## Quickstart

```bash
cd swarm-forge-lite/tools/shared/umlview
python3 render.py example.model.json            # writes example.model.html
python3 render.py example.violation.model.json  # red violations demo
```

Open the `.html` in a browser; edit the JSON, re-run `render.py`, press F5.
`--check` exits 1 when any error-severity finding exists (useful in the critic gate).

Layout is done by **dagre** (bundled in `vendor/`), so a component with many classes is
laid out as a graph, not a column. The page has no external requests.

**Navigate:** drag to pan, wheel to zoom at the cursor, `+` / `−` / `Fit` in the corner,
or keys `+` `-` `0` (100%) and `f` (fit).

Scan existing code (starting point only — secrets, core/shell and levels are authored):

```bash
python3 scan_python.py /path/to/src --out /tmp/model.json --title "my app"
python3 render.py /tmp/model.json
```

## The data

A model is `{title, task?, levels?, components[], edges[], states?}`. A component holds
classes; a class has `id, name, stereotype, core, secret, responsibility, fields, ops`;
an op has `cqs` (`command`/`query`), `pre`, `post`, `invariant`; edges carry a UML `kind`.
Full field list: `reference/model-format.md`.

## What the view makes visible

The logic is **exactly upstream's** (`unclebob/uml-viewer`): normalize edges, merge per
pair by kind-rank, then mark a violation when a `dependency` runs inner → outer with both
ends ranked from `levels`. Findings are upstream-only:

- **`dep-rule`** — the dependency rule (red edge).
- **`dup-id`**, **`bad-edge`** — structural errors upstream throws on; reported here and the
  page still renders.

Design annotations (`core`, `secret`, `responsibility`, op `cqs`/`pre`/`post`/`invariant`)
are drawn as colour, badges, and the detail panel, but they are **not** findings — upstream
has no such rules. Hover a finding to highlight its classes; hover a class to trace edges.

## Use in the design phase

The mapping from the design artifacts to this model is `reference/model-format.md`.

- The **modeler** writes `design/<task>/model.json` — CRC cards as classes with dotted ids,
  collaborators as edges with deliberate kinds, `levels` ordered **core-inner → shell-outer**
  so a DIP break shows as his red `dependency`, and `secret`/`core`/`responsibility` under
  `annotations`. It renders `model.html`.
- The **contractor** gives every op its contract under `annotations` (`cqs`, `pre`, `post`,
  `invariant`); it shows as `[C]`/`[Q]` and in the detail panel.
- The **critic** renders with `--check` (only `dep-rule` + structural), then checks by hand
  what upstream does not: level order, no floating classes, every op tagged, and that the
  model matches the `SKELETON`.

The **Secrets** panel makes Parnas visible (class → secret, hover to highlight); the header
counts core, shell, and secrets.

`BLUEPRINT.md` stays the accepted text record; `model.json` is its projection. If they
disagree, the blueprint wins and the model is regenerated.

## Provenance

- **Model and logic** — a faithful port of `unclebob/uml-viewer`'s domain: `domain/ir.clj`
  normalization, `domain/policy.clj` ranks, edge merge, and the dependency rule. Findings
  are upstream-only (`dep-rule`, plus the structural `dup-id`/`bad-edge`).
- **Language analysis** — `scan_python.py` mirrors `graph_clojure.clj` for Python (one node
  per module; imports → `dependency`; Protocol/ABC → `interface` + `implements`; externals
  → `foreign`).
- **Layout engine** — **dagre** (`@dagrejs/dagre`, vendored in `vendor/`). This is *not*
  Uncle Bob's engine; his is a hand-rolled Mermaid-style layout inside a live Clojure/Quil
  app (`engine/layout.clj`).
- **Renderer** — ours: `render.py` (model → page) and `template.html` (SVG, pan/zoom,
  hover/click, panels).

## Not carried over from unclebob/uml-viewer

No Quil canvas, no Grok/tmux companion, no mailbox files, no drill-down proposals, no
CRAP/mutation overlay, no source-jump window. Those serve a live, coupled agent loop; this
serves a static, reloadable view of a data file.
