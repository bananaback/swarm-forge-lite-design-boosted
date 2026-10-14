# Diagram Model - the IR of unclebob/uml-viewer, in JSON

The model and every rule are a port of the domain of `unclebob/uml-viewer` (`domain/ir.clj` normalization, `domain/policy.clj` ranks + dependency rule). Only two things differ: the display is HTML/SVG instead of Quil, and the language analysis (`tools/shared/umlview/scan_python.py`) reads Python instead of Clojure. There are no new concepts.

Agents write `design/subsystems/<subsystem>/model.json`. `tools/shared/umlview/render.py` turns it into one `model.html` that loads Tailwind and jQuery from two pinned CDN URLs, so it needs the network to open (dagre layout). The JSON is the source of truth. Reload with F5.

## Shape (upstream IR)

```json
{
  "title": "Lending library",
  "direction": "tb",
  "levels": [["domain"], ["app"]],
  "packages": [
    { "id": "domain", "label": "Domain",
      "classes": [
        { "id": "domain.book", "name": "Book", "stereotype": "class",
          "fields": [{"text": "isbn : String"}],
          "ops": [{"name": "find", "args": ["isbn"], "returns": "Book"}] }
      ] },
    { "id": "app", "label": "Application",
      "classes": [ { "id": "app.repo", "name": "CatalogRepo", "stereotype": "interface" } ] }
  ],
  "foreign": ["sqlalchemy"],
  "edges": [
    { "from": "app.repo", "to": "domain.book", "kind": "dependency" },
    { "from": "domain.book", "to": "sqlalchemy", "kind": "dependency" }
  ],
  "edge-kinds": { "app.repo->domain.book": "association" },
  "omit-edges": [["app.repo", "domain.book"]]
}
```

`components` is accepted as an alias of `packages`. A hierarchical form with a flat `classes` list and an `order` is also accepted (the tool groups classes by their first dotted segment).

## Fields (upstream)

- `packages[]` - `{id, label, classes[]}`.
- `class` - `{id, name, stereotype?, ns?, level?, hide-members?, fields?, ops?}`.
  - `id` is a **namespace**, lower-cased, spaces -> `-` (`as-id`).
  - `stereotype`: `class` | `interface` | `abstract` | `enum`.
  - `fields` / `ops` are members: a string, or `{name, args?, type?, returns?, private?, ...}`.
    - A field row draws its member: a plain string as it is, else `text` (the live source line that `sync_python.py` writes), else `name: type`. Both shapes are accepted; the live overlay writes `{"text": "..."}`, an authored record writes `{"name": ..., "type": ...}`.
- `edge` - `{from, to, kind?, label?, violating?}`. `kind` defaults to **`association`**. The set is `inheritance` `implements` `association` `dependency` `aggregation` `composition`.
- `levels` - inner-first groups of segments. A small rank is inner. `rank-of` matches a class id by its longest dotted prefix, so the **first segment of a class id must appear in `levels`**.
- `foreign` - prefixes rendered as external ovals. Edge ids under a prefix collapse to it.
- `edge-kinds` - `{"from->to": kind}` remap. `omit-edges` - `[["from","to"]]` to drop.
- `direction` - `tb` (default) or `lr`. `title`.

## Annotations (ours, namespaced, never a finding)

The normalizer upstream drops unknown keys, so our design annotations live under an `annotations` object that the IR does not otherwise use. The IR stays in the shape of the upstream tool:

```json
{ "id": "domain.Clip", "name": "Clip",
  "annotations": {"core": true, "secret": "the on-disk segment format",
                  "responsibility": "Hold the ordered frames of one clip."},
  "ops": [ { "name": "add_frame", "args": [{"name": "f", "type": "Frame"}], "returns": "None",
             "annotations": {"cqs": "command", "pre": "f.ts is monotonic", "post": "frames contains f"} } ] }
```

- Class annotations: `core` (`true` = functional core), `secret`, `responsibility`.
- Op annotations: `cqs` (`command`/`query`), `pre`, `post`, `invariant`, `visibility`.

The renderer draws them (core/shell color, `[C]`/`[Q]` badges, the Secrets panel, the detail panel), but they produce **no findings**: upstream has no such rules. For backward compatibility, a top-level `core`/`secret`/`cqs`/... is still accepted and folded into `annotations`.

## Live overlay (`sync_python.py`, ours)

`tools/shared/umlview/sync_python.py` writes `<model>.live.json` from the accepted model, the real source, and a crapper report. It keeps every authored annotation and adds:

- `op.metrics` = `{cc, coverage (0..1), crap}` from a crapper report.
- `op.live` and `class.live` = `{status: synced | new | missing | ambiguous, source?}`.
- `op.code` = the source lines of the method.
- top-level `live` = `{source_root, crap, counts}`, shown as a **LIVE** badge.

The accepted model is never touched. Render the live file over the diagram (`render.py <model>.live.json --out model.html`). `render.py` pools and grades the CRAP in Python and emits the result into the page as data; the template only draws it. The viewer prints `crap` beside each method, and the right panel lists signatures with a CRAP/coverage/CC table. Click a method row to expand its source code.

## The CRAP grade - ported from upstream

`CRAP = CC^2 * (1 - cov)^3 + CC`. The grade is a faithful port of `unclebob/uml-viewer`: `src/uml_viewer/domain/config.clj` (`crap-risk`, `crap-grade`, `pool-crap`, `combined-grade`) against the cases in `spec/uml_viewer/domain/config_spec.clj`. The mutation half of the upstream model is **not** ported, so the box colour is the CRAP grade alone.

- `crap-risk` = `mu + sigma` of a pooled sample.
- `crap-grade` maps the risk onto the stops, piecewise-linear, and clamps outside them:

| risk (mu+sigma) | scaled | grade | band |
|---|---|---|---|
| `<= 8` (`crap-thresholds.green`) | `grade-best` | `10.0` | green |
| `= 12` (`crap-thresholds.yellow`) | `grade-mid` | `5.5` | yellow |
| `>= 20` (`crap-thresholds.red`) | `grade-worst` | `1.0` | red |

A missing score is `grade-worst` (1.0), never unknown.

- `pool-crap` pools a subtree (a class, or the classes of a package), with the function scores as the sample. `n` is the function count, `mu` the mean, `max` the worst function (never a sum), and `sigma` the **population** standard deviation.
  - A module that has functions but no CRAP data counts as the red threshold (20) once per op.
  - A module with no functions at all (an enum or a data holder) is not graded: it contributes no group, and it carries no pooled `crap`, `risk`, `grade` or `band`.
  - Groups combine weighted by `n`: `mu = sum(n_i * mu_i) / sum(n_i)`; `sigma = sqrt(max(0, sum(n_i * (sigma_i^2 + mu_i^2)) / sum(n_i) - mu^2))`; `max = max(max_i)`. Values round to 0.1.
  - A summary that already pools a subtree (`rolled`) wins over the module's own ops.
- `combined-grade` is the mean of the present grades. With mutation dropped, only the CRAP grade is present, so the page colours a box by its CRAP grade alone.

---

## The mapping of the design team - CRC card -> class, collaborator -> edge

How the artifacts of the design team (CRC cards, Parnas secrets, the SOLID concerns) project onto this IR. The mapping adds **no new viewer logic**: the only rule that the viewer enforces is the dependency rule.

### The id convention

A class id is a namespace: `component.Name` (lower-case, dotted). Its **first segment must appear in `levels`**, because the rule ranks a class by its longest dotted prefix.

```json
"packages": [
  { "id": "domain", "label": "Domain", "classes": [
      { "id": "domain.Clip", "name": "Clip", "annotations": {"core": true, "secret": "..."} } ] },
  { "id": "adapters", "label": "Adapters", "classes": [
      { "id": "adapters.DiskStore", "name": "DiskStore", "annotations": {"core": false} } ] }
],
"levels": [["domain"], ["application"], ["adapters"]]
```

### CRC card -> class

| Card field | Model |
|---|---|
| Class name | `class.name`, id `component.Name` |
| Responsibility | `class.annotations.responsibility` |
| Secret (Parnas) | `class.annotations.secret` |
| Core / shell | `class.annotations.core` **and** the place of the component in `levels` |

### Collaborator -> edge (the kind matters)

The kind decides whether the dependency rule can fire.

| CRC relation | `kind` | subject to the rule? |
|---|---|---|
| shell realizes a core interface | `implements` | no - always exempt |
| A uses / calls B | `dependency` | **yes** |
| whole -> part, owned | `composition` | yes |
| whole -> part, shared | `aggregation` | yes |
| is-a | `inheritance` | no |
| incidental reference | `association` | no |

One edge for each `[from, to]` survives (the strongest kind wins), so do not express two relations between the same pair. Pick the strongest kind that is true.

### Levels are the architectural spine - this is the DIP check

Order `levels` **core-inner first, shell-outer last**. Then a core class that depends on a shell class is an inner -> outer `dependency`, and the viewer paints it **red by the rule of the upstream tool**. Do not add a DIP finding. Order the levels and let the rule do its job. A shell that implements a core interface is `implements`, so it stays clean.

### Ops -> contracts

Each op is a member. Its contract is an annotations object (drawn as `[C]`/`[Q]` and in the detail panel, never as a finding):

```json
{ "name": "add_frame", "args": [{"name": "f", "type": "Frame"}], "returns": "None",
  "annotations": {"cqs": "command", "pre": "f.ts is monotonic", "post": "frames contains f", "invariant": "frames is ordered"} }
```

### Working rule

- The `design/subsystems/<subsystem>/` record is the source of truth for design intent. `model.json` is its projection.
- When they disagree, **the record wins** and the model is generated again. A mismatch is a defect that the critic must catch.
- Render before every gate and open `design/subsystems/<subsystem>/model.html`. Fix the model, never the HTML.

## What the renderer does (upstream order)

1. **Normalize** (`ir.clj`): `as-id`, `as-class`, `as-edge` (kind defaults to `association`). A duplicate id and an unknown edge endpoint are errors.
2. **Collapse** (`policy.clj collapse-graph`): remap foreign ids to their listed prefix, drop self-edges, then **merge**.
3. **Merge** (`merge-edges`): one edge for each `[from, to]`, the strongest by **kind-rank** (`implements`/`inheritance` 4 > `composition` 3 > `aggregation` 2 > `association` 1 > `dependency` 0). A violation survives only when the strongest is a `dependency`.
4. **Mark violations** (`violating-dependency?`): **only a `dependency`** edge, **both ends ranked** from `levels`, violates if and only if `rank(from) < rank(to)` (inner -> outer). The same rank is permitted. No `levels` => nothing ranked => nothing marked.
5. **Rank classes** (`with-levels`), then **apply `edge-kinds` / `omit-edges`**. A non-`dependency` edge loses any violation.

## Findings - upstream only

| code | source | meaning |
|---|---|---|
| `dep-rule` | `policy.clj` | a `dependency` from an inner to an outer rank |
| `dup-id` | `ir.clj` (throws) | duplicate class id |
| `bad-edge` | `ir.clj` (throws) | edge that names an unknown class |

Upstream throws on these errors. This tool reports them, and the page still renders.

## Rendering

```bash
python3 swarm-forge-lite/tools/shared/umlview/render.py design/subsystems/<subsystem>/model.json
# writes design/subsystems/<subsystem>/model.html; open it, F5 to reload
python3 swarm-forge-lite/tools/shared/umlview/render.py design/subsystems/<subsystem>/model.json --check    # exit 1 on any violation or structural error
```

The layout is dagre (vendored). Drag to pan, wheel to zoom, `+ / - / Fit`, keys `+ - 0 f`. The page loads Tailwind CSS and jQuery from two pinned CDN URLs, so it needs the network to render.
