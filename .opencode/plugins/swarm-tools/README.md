# swarm-tools

Registers the `swarm.*` Code Mode namespace. Every tool forwards one JSON call to
`python3 <pack>/tools/shared/swarm_json.py <command> '<json-args>'` and returns a
JSON string. Parse it. Every result carries `pack`, the absolute path of the pack
that answered.

The plugin resolves the pack from `SWARM_PACK` (only when it holds
`harness.json`), then the plugin-relative pack, then an upward walk from cwd.

## Tools (30)

| Group | Tools |
|---|---|
| resolve | `status`, `envelope`, `modules`, `interface`, `goal`, `doctor` |
| method | `guide` |
| record | `check`, `lintRecord`, `genDoc`, `decisions`, `initWork`, `clean`, `checkEnvelope`, `vocabRename`, `genRecord`, `report` |
| quality | `ruff`, `dry`, `crap`, `pytest`, `acceptance` |
| gherkin | `gherkinParse`, `gherkinDry` |
| uml | `uml` |
| aggregate | `page`, `gate`, `ready` |
| meta | `docs`, `help` |

Regenerate this table with `python3 <pack>/tools/shared/swarm_json.py docs
'{"table":true}'`. A test keeps it equal to the catalog.

## Compact results

- Default: summary counts only.
- `view:'rows'`: inline `cols` + `rows`, capped by `limit`.
- `view:'all'`: full rows saved under `<artifacts>/handles`, fetched with `page`.
- An error returns `{"error": "..."}` with exit 0. Check the `error` key.

## The flat record

- `initWork({role,subsystem,flat:true})` writes one file:
  `requirements.md`, `architecture.md`, `review.md`, or `modules/<module>.md`.
- `genRecord({subsystem})` projects `SKELETON.md` from the module files and
  returns counts from `model.json`. It writes no `COUNTS.md` or `CONTRACTS.md`.
- `uml({op:'render',subsystem})` writes `model.html`. Agents never read it.
- `uml({op:'sync',subsystem})` overlays real signatures and CRAP into
  `model.json`, then `render` updates the page.

## Gate

`gate({subsystem,feature,crap:true})` runs dry, ruff, format, pytest, acceptance,
and CRAP. Each verdict has an explicit `ok`; `pass` is true only when every `ok`
is true and no check errored. `ready({role,subsystem})` fails closed on a check
error.

## CLI

The same backend is callable:

```
python3 <pack>/tools/shared/swarm_json.py docs
python3 <pack>/tools/shared/swarm_json.py help gate
python3 <pack>/tools/shared/swarm_json.py gate '{"subsystem":"clip","feature":"clip_recording","crap":true}'
```

`python3 <pack>/tools/shared/swarm_json.py --help` prints the catalog.
