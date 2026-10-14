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
| `render.py` | model.json → standalone `*.html`; computes the findings and the CRAP grades |
| `template.html` | the page: Tailwind utility classes + jQuery, dagre layout + inline SVG, panels |
| `vendor/dagre.min.js` | the layout engine, bundled so the HTML works offline (no CDN at view time) |
| `scan_python.py` | optional: Python source → model.json (a starting point) |
| `sync_python.py` | design model.json + real source (+ crapper report) → `model.live.json` |
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
laid out as a graph, not a column. The page has **two external requests**, both pinned:

| Library | Pinned URL |
|---|---|
| Tailwind CSS (Play CDN, `darkMode: "class"`) | `https://cdn.tailwindcss.com/3.4.16` |
| jQuery | `https://code.jquery.com/jquery-3.7.1.min.js` |

So the page **needs the network to render**. Everything else (dagre, the model, the findings)
is inline. The theme toggle, the panels and every interaction are Tailwind classes and jQuery.

**Navigate:** drag to pan, wheel to zoom at the cursor, `+` / `−` / `Fit` in the corner,
or keys `+` `-` `0` (100%) and `f` (fit).

**Select:** the panel opens on the entity list — every class with its description. Click a
class box, or a row in that list, to select the entity: the canvas centers and zooms its box
and the panel shows its detail, with the method table and the code expand. A click on empty
canvas, or the `← all entities` link, clears the selection and brings the list back.
`window.umlview = {select, deselect, view}` drives the same selection from an embedding page.

Scan existing code (starting point only — secrets, core/shell and levels are authored):

```bash
python3 scan_python.py /path/to/src --out /tmp/model.json --title "my app"
python3 render.py /tmp/model.json
```

## Refresh the view from the implementation

Once code exists, overlay the real signatures and metrics onto the accepted skeleton and
render a live view. The accepted `model.json` is never modified.

```bash
# 1. CRAP report (stdout) from the vendored crapper, to a file
#    Point --root at the same subtree as --source, so the namespaces match.
PYTHONPATH=swarm-forge-lite/tools/refactorer python3 -m crapper \
  --root <task subtree> --source-root <task subtree> --use-existing-coverage > dump/crap.txt

# 2. overlay the real source: signatures + metrics -> model.live.json
python3 sync_python.py design/subsystems/<subsystem>/model.json \
  --source <task subtree> --crap dump/crap.txt

# 3. render the live overlay over the diagram, then reload model.html
python3 render.py design/subsystems/<subsystem>/model.live.json --out design/subsystems/<subsystem>/model.html
```

The live page shows a **LIVE** badge and prints each method's CRAP. The right panel is a
signature/CRAP table; click a method row to expand its source. A method added after the
skeleton reads `+ new in implementation`; a skeleton method the code does not contain reads
`- not in implementation`. Point `--source` at the task's own subtree so a class name shared
across tasks stays unambiguous.

## The CRAP grade

`render.py` pools and grades the CRAP in Python and emits it into the page as data. The
template only draws. The grade is a faithful port of `unclebob/uml-viewer`:
`src/uml_viewer/domain/config.clj` (`crap-risk`, `crap-grade`, `pool-crap`,
`combined-grade`), against the cases in `spec/uml_viewer/domain/config_spec.clj`. The
mutation half of the upstream model is **not** ported, so a box shows the CRAP grade alone.

`crap-risk` = `mu + sigma`. `crap-grade` maps the risk piecewise-linear onto the stops
`8 → 12 → 20`, landing on `10.0 → 5.5 → 1.0`, and clamps outside them:

| risk (mu+sigma) | grade | band |
|---|---|---|
| `<= 8` (`crap-thresholds.green`) | `10.0` (`grade-best`) | green |
| `= 12` (`crap-thresholds.yellow`) | `5.5` (`grade-mid`) | yellow |
| `>= 20` (`crap-thresholds.red`) | `1.0` (`grade-worst`) | red |

A missing score is `grade-worst` (1.0), never unknown. `pool-crap` pools a subtree with the
function scores as the sample: `n` is the function count, `mu` the mean, `max` the worst
function (never a sum), `sigma` the population standard deviation. A module that has
functions but no CRAP data counts as the red threshold (20) once per op. A module with no
functions at all — an enum or a data holder — is not graded: it contributes no group.
Groups combine weighted by `n`, and a summary that already pools a subtree wins over the
module's own ops. `combined-grade` is the mean of the present grades.

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

- The **architect** writes `design/subsystems/<subsystem>/model.json` — CRC cards as classes with dotted ids,
  collaborators as edges with deliberate kinds, `levels` ordered **core-inner → shell-outer**
  so a DIP break shows as his red `dependency`, and `secret`/`core`/`responsibility` under
  `annotations`. It renders `model.html`.
- The **designer** gives every op its contract under `annotations` (`cqs`, `pre`, `post`,
  `invariant`); it shows as `[C]`/`[Q]` and in the detail panel.
- The **critic** renders with `--check` (only `dep-rule` + structural), then checks by hand
  what upstream does not: level order, no floating classes, every op tagged, and that the
  model matches the `SKELETON`.

The **Secrets** panel makes Parnas visible (class → secret, hover to highlight); the header
counts core, shell, and secrets.

The `design/subsystems/<subsystem>/` record stays the accepted text record; `model.json` is its projection. If they
disagree, the record wins and the model is regenerated.

## Provenance

- **Model and logic** — a faithful port of `unclebob/uml-viewer`'s domain: `domain/ir.clj`
  normalization, `domain/policy.clj` ranks, edge merge, and the dependency rule. Findings
  are upstream-only (`dep-rule`, plus the structural `dup-id`/`bad-edge`).
- **Language analysis** — `scan_python.py` mirrors `graph_clojure.clj` for Python (one node
  per subsystem; imports → `dependency`; Protocol/ABC → `interface` + `implements`; externals
  → `foreign`).
- **Layout engine** — **dagre** (`@dagrejs/dagre`, vendored in `vendor/`). This is *not*
  Uncle Bob's engine; his is a hand-rolled Mermaid-style layout inside a live Clojure/Quil
  app (`engine/layout.clj`).
- **Renderer** — ours: `render.py` (model → page, and the ported grade logic) and
  `template.html` (Tailwind utility classes + jQuery, SVG, pan/zoom, hover/click, panels).

## Not carried over from unclebob/uml-viewer

No Quil canvas, no Grok/tmux companion, no mailbox files, no drill-down proposals, no
mutation metric, no source-jump window. Those serve a live, coupled agent loop; this
serves a static, reloadable view of a data file.
