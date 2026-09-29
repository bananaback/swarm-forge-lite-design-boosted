# Diagram Model — unclebob/uml-viewer's IR, in JSON

The model and every rule are a port of `unclebob/uml-viewer`'s domain
(`domain/ir.clj` normalization, `domain/policy.clj` ranks + dependency rule). Only two
things differ: the display is HTML/SVG instead of Quil, and the language analysis
(`tools/shared/umlview/scan_python.py`) reads Python instead of Clojure. No new concepts.

Agents write `design/<task>/model.json`; `tools/shared/umlview/render.py` turns it into a
standalone `model.html` (dagre layout). The JSON is the source of truth; reload with F5.

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

`components` is accepted as an alias of `packages`; a hierarchical form with a flat
`classes` list and an `order` is also accepted (classes are grouped by their first dotted
segment).

## Fields (upstream)

- `packages[]` — `{id, label, classes[]}`.
- `class` — `{id, name, stereotype?, ns?, level?, hide-members?, fields?, ops?}`.
  - `id` is a **namespace**, lower-cased, spaces → `-` (`as-id`).
  - `stereotype`: `class` | `interface` | `abstract` | `enum`.
  - `fields` / `ops` are members: a string, or `{name, args?, type?, returns?, private?, …}`.
- `edge` — `{from, to, kind?, label?, violating?}`. `kind` defaults to **`association`**;
  the set is `inheritance` `implements` `association` `dependency` `aggregation`
  `composition`.
- `levels` — inner-first groups of segments; small rank = inner. `rank-of` matches a class
  id by its longest dotted prefix, so a class id's **first segment must appear in `levels`**.
- `foreign` — prefixes rendered as external ovals; edge ids under a prefix collapse to it.
- `edge-kinds` — `{"from->to": kind}` remap; `omit-edges` — `[["from","to"]]` to drop.
- `direction` — `tb` (default) or `lr`. `title`.

## Annotations (ours; namespaced, never a finding)

Upstream's normalizer drops unknown keys, so our design annotations live under an
`annotations` object the IR does not otherwise use — the IR stays his shape:

```json
{ "id": "domain.Clip", "name": "Clip",
  "annotations": {"core": true, "secret": "the on-disk segment format",
                  "responsibility": "Hold the ordered frames of one clip."},
  "ops": [ { "name": "add_frame", "args": [{"name": "f", "type": "Frame"}], "returns": "None",
             "annotations": {"cqs": "command", "pre": "f.ts is monotonic", "post": "frames contains f"} } ] }
```

- Class annotations: `core` (`true` = functional core), `secret`, `responsibility`.
- Op annotations: `cqs` (`command`/`query`), `pre`, `post`, `invariant`, `visibility`.

They are drawn (core/shell colour, `[C]`/`[Q]` badges, the Secrets panel, the detail panel)
but produce **no findings** — upstream has no such rules. For backward compatibility a
top-level `core`/`secret`/`cqs`/… is still accepted and folded into `annotations`.

---

## The design team's mapping — CRC card → class, collaborator → edge

How the design team's artifacts (CRC cards, Parnas secrets, the SOLID concerns) project onto
this IR. It adds **no new viewer logic** — the only rule the viewer enforces is the dependency
rule.

### The id convention

A class id is a namespace: `component.Name` (lower-case, dotted). Its **first segment must
appear in `levels`**, because the rule ranks a class by its longest dotted prefix.

```json
"packages": [
  { "id": "domain", "label": "Domain", "classes": [
      { "id": "domain.Clip", "name": "Clip", "annotations": {"core": true, "secret": "..."} } ] },
  { "id": "adapters", "label": "Adapters", "classes": [
      { "id": "adapters.DiskStore", "name": "DiskStore", "annotations": {"core": false} } ] }
],
"levels": [["domain"], ["application"], ["adapters"]]
```

### CRC card → class

| Card field | Model |
|---|---|
| Class name | `class.name`; id `component.Name` |
| Responsibility | `class.annotations.responsibility` |
| Secret (Parnas) | `class.annotations.secret` |
| Core / shell | `class.annotations.core` **and** the component's place in `levels` |

### Collaborator → edge (kind matters)

The kind decides whether the dependency rule can fire.

| CRC relation | `kind` | subject to the rule? |
|---|---|---|
| shell realizes a core interface | `implements` | no — always exempt |
| A uses / calls B | `dependency` | **yes** |
| whole → part, owned | `composition` | yes |
| whole → part, shared | `aggregation` | yes |
| is-a | `inheritance` | no |
| incidental reference | `association` | no |

One edge per `[from, to]` survives (strongest kind wins), so do not express two relations
between the same pair — pick the strongest that is true.

### Levels are the architectural spine — this is the DIP check

Order `levels` **core-inner first, shell-outer last**. Then a core class depending on a shell
class is an inner → outer `dependency`, and the viewer paints it **red by his rule**. You do
not add a DIP finding; you order the levels and let the rule do its job. A shell implementing
a core interface is `implements`, so it stays clean.

### Ops → contracts

Each op is a member; its contract is an annotations object (drawn as `[C]`/`[Q]` and in the
detail panel, never as a finding):

```json
{ "name": "add_frame", "args": [{"name": "f", "type": "Frame"}], "returns": "None",
  "annotations": {"cqs": "command", "pre": "f.ts is monotonic", "post": "frames contains f", "invariant": "frames is ordered"} }
```

### Working rule

- `BLUEPRINT.md` is the source of truth for design intent; `model.json` is its projection.
- If they disagree, **the blueprint wins** and the model is regenerated. A mismatch is a
  defect the critic must catch.
- Render before every gate and open `design/<task>/model.html`; fix the model, never the HTML.

## What the renderer does (upstream order)

1. **Normalize** (`ir.clj`): `as-id`, `as-class`, `as-edge` (kind defaults to `association`),
   duplicate id and unknown edge endpoint are errors.
2. **Collapse** (`policy.clj collapse-graph`): remap foreign ids to their listed prefix, drop
   self-edges, then **merge**.
3. **Merge** (`merge-edges`): one edge per `[from, to]`, the strongest by **kind-rank**
   (`implements`/`inheritance` 4 > `composition` 3 > `aggregation` 2 > `association` 1 >
   `dependency` 0). A violation survives only if the strongest is a `dependency`.
4. **Mark violations** (`violating-dependency?`): **only a `dependency`** edge, **both ends
   ranked** from `levels`, violating iff `rank(from) < rank(to)` (inner → outer). Same rank
   is allowed. No `levels` ⇒ nothing ranked ⇒ nothing marked.
5. **Rank classes** (`with-levels`), then **apply `edge-kinds` / `omit-edges`**; a non-
   `dependency` edge loses any violation.

## Findings — upstream only

| code | source | meaning |
|---|---|---|
| `dep-rule` | `policy.clj` | a `dependency` from an inner to an outer rank |
| `dup-id` | `ir.clj` (throws) | duplicate class id |
| `bad-edge` | `ir.clj` (throws) | edge naming an unknown class |

Errors upstream throws on are reported here and the page still renders.

## Rendering

```bash
python3 swarm-forge-lite/tools/shared/umlview/render.py design/<task>/model.json
# writes design/<task>/model.html; open it, F5 to reload
python3 .../render.py model.json --check    # exit 1 on any violation or structural error
```

Layout is dagre (vendored). Drag to pan, wheel to zoom, `+ / − / Fit`, keys `+ - 0 f`.
