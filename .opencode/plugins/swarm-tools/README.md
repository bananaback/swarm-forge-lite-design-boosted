# swarm-tools

The SwarmForge workflow as **Code Mode tools**. Every pipeline command is available
as `tools.swarm.*` inside `execute`. Each returns compact JSON. Parse it with
`JSON.parse(result)`.

## Why

The roles call the pack Python over `shell`. Each shell call puts the whole
stdout into the model context. Inside Code Mode a tool result stays in the JS
runtime, and only the `return` value of the block enters the context.

**Design rule: the default output is small.** A summary carries counts, not rows.
So even a lazy verbatim `return await tools.swarm.ruff(...)` beats the shell tool.
A role that composes several calls pays almost nothing.

Measured on this repo (bytes):

| Call | shell | `swarm` default | yield |
|---|---|---|---|
| `crapper` (full table) | 9804 | 68 | 144x |
| `ruff4py` (with frames) | 2678 | 88 | 30x |
| `harness.py decisions` | 2606 | 92 | 28x |
| `harness.py guide` | 6504 | 2195 (or 1755 via `forms`) | 3x |
| `harness.py status` | 872 | 534 | 1.6x |
| 4-part terminal gate | ~4 logs | 309 | large |

## Which pack answered

The workspace holds two packs: the project copy and the staging clone. The same
tool name exists in both. Every result carries `pack`, the absolute path of the
pack that served the call. Read it when a path or a number looks wrong.

```js
const r = JSON.parse(await tools.swarm.status({ subsystem: "clip" }))
r.pack   // "/home/<user>/.../swarm-forge-lite"
```

## Views (the list tools)

Every list tool (`ruff`, `dry`, `crap`, `check`, `lintRecord`, `gherkinDry`) has:

- **`summary` (default)** - counts and `byCode` tallies only. No rows.
- **`view:"rows"`** - inline rows: a `cols` header plus arrays, capped by `limit`.
- **`view:"all"`** - a paging **handle**. Fetch more rows with `swarm.page({handle,offset})`.

`full:true` is an alias for `view:"rows"`.

## Aggregators (no loop needed)

- **`swarm.gate({subsystem,feature})`** - `dry` + `ruff` + `pytest` + `acceptance` in
  one call. Returns one verdict per check plus `pass`. `checks` selects a subset.
- **`swarm.ready({role,subsystem})`** - `check` + `lint-record` + `decisions` in one
  call. Returns each verdict plus `pass`.
- **`swarm.triage({subsystem})`** - a fast read-only snapshot: `status` + `ruff` +
  `decisions`. `checks` may add `pytest` or `check`.

These make the win independent of the caller's code.

## Tool catalog

| Tool | Purpose | Default |
|---|---|---|
| `status({wiring})` | roots and lane | map + `missing` |
| `config()` | the wiring | full |
| `envelope({role,subsystem})` | dispatch fields + ENV + stop test | full text (pass-through) |
| `guide({role,subsystem,items})` | form names, titles, stop test | names only |
| `forms({role})` | form file names | smallest |
| `form({role,file})` | one form's items | full |
| `fix({code})` | the fix for a finding code | one line |
| `check({role,subsystem,view,limit})` | lint the written record | verdict + `byCode` |
| `lintRecord({subsystem,view})` | lint the subsystem record | verdict + `byCode` |
| `decisions({role,subsystem,all})` | the decision ledger | **open rows only** |
| `initWork({role,subsystem})` | write empty forms | names |
| `clean({target,subsystem})` | clear a disposable root | counts |
| `checkEnvelope({text})` | the duplicate-block rule and the cite hint (no size limit) | verdict |
| `vocabRename({old,new,files})` | bulk rename | counts |
| `ruff({paths,view})` | ruff findings | `total` + `byCode` |
| `dry({paths,view})` | duplicate pairs | `total` |
| `pytest({k,paths,scope})` | test counts + failures | summary |
| `crap({filters,all})` | CRAP rows | **above CRAP 10 only** |
| `acceptance({feature})` | acceptance run | summary |
| `gherkinParse({feature,names})` | feature -> IR | counts |
| `gherkinDry({ir,view})` | dry report | counts |
| `umlRender({model,check})` | model -> html | one line |
| `umlSync({model,source,crap})` | overlay metrics | one line |
| `umlScan({root,out})` | source -> model | one line |
| `uml({op,model,dryRun,...})` | query/mutate model.json (one op per call) | op result + rows |
| `page({handle,offset,limit})` | fetch a page of rows | page |
| `gate({subsystem,feature,checks})` | the terminal gate | one verdict |
| `ready({role,subsystem,checks})` | the record gate | one verdict |
| `triage({subsystem,checks})` | fast snapshot | one verdict |
| `docs()` | the catalog | full |

## Absolute paths

```
python3 <pack>/tools/shared/swarm_json.py status
python3 <pack>/tools/shared/swarm_json.py check '{"role":"architect","subsystem":"clip"}'
python3 <pack>/tools/shared/swarm_json.py gate '{"subsystem":"clip","feature":"clip_recording"}'
python3 <pack>/tools/shared/swarm_json.py docs
```

## Help

Three ways to learn a tool:

```
python3 <pack>/tools/shared/swarm_json.py --help        # the whole catalog, grouped
python3 <pack>/tools/shared/swarm_json.py ruff --help   # one tool's usage page
python3 <pack>/tools/shared/swarm_json.py help gate      # the same, by name
```

In Code Mode:

```js
await tools.swarm.docs()                // the compact catalog: name, group, summary, example
await tools.swarm.help()                // the catalog with groups
await tools.swarm.help({tool:'ruff'})   // one tool: params, defaults, return shape, example, output
```

Each `help` entry carries the purpose, the shell command it replaces, the roles
that use it, every param (name, type, default, meaning), the return shape, a call
example, an example output, and a note.

## Lanes

Pass `subsystem: "<name>"` to any tool. The backend sets `SWARM_LANE`, so the
disposable roots stay per subsystem. Relative paths resolve against the workspace
root, then the pack root, then the server cwd.

## Configuration

`SWARM_PACK` overrides the pack location. Default: `<project>/swarm-forge-lite`.
The plugin finds the project from its own file path, so the server cwd does not
matter.
