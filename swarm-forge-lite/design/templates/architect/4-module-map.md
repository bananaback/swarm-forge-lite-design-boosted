## 4. MODULE MAP - the cut and the freeze (Parnas + caller closure)

One row for each module. The `Owns` sets must be disjoint. The map is frozen
when the checklist in `<pack>/reference/module-rules.md` passes.

| Module | Owns (write set) | Provides | Requires | Secret |
|---|---|---|---|---|
| | | | | |

### 4a. SHARED FILES - serialize

A file that two modules must edit. The orchestrator orders the edits.

| File | Modules that touch it | Order |
|---|---|---|
| | | |

### 4b. ACCEPTANCE WALK - every check across the modules

Walk every accepted check before the freeze. A crossing with no frozen interface
blocks the freeze.

| Acceptance check | Module path (B1 -> B2 -> ...) | Frozen interface it crosses |
|---|---|---|
| | | |

- Open crossing with no frozen interface: <none / the check>
- Freeze checklist: disjoint write sets <yes/no> - acyclic <yes/no> - one secret each <yes/no> - caller closure <yes/no> - two-way door <yes/no>

### 4c. VISUAL

- Rendered model: `<subsystem>/model.json` -> `<subsystem>/model.html` (run `umlview render.py`). The
  model is the source; the HTML is a view. Record `--check` findings here.
- Findings not fixed (with reason):
