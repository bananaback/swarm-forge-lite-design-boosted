# umlmodel

Query and mutate a uml `model.json` through one small op catalog, so an agent
edits the model through the tool instead of rewriting thousands of lines of JSON
by hand. The format is the one `reference/model-format.md` documents. The
renderer (`tools/shared/umlview/`) is untouched by this tool.

```bash
python3 <pack>/tools/shared/umlmodel list
python3 <pack>/tools/shared/umlmodel stats   --model design/subsystems/<subsystem>/model.json
python3 <pack>/tools/shared/umlmodel violations --model design/subsystems/<subsystem>/model.json
python3 <pack>/tools/shared/umlmodel add-class --model m.json --id core.New --name New --package core
python3 <pack>/tools/shared/umlmodel add-edge  --model m.json --from shell.Svc --to core.New --kind dependency
python3 <pack>/tools/shared/umlmodel remove-class --model m.json --id core.New --dry-run
```

## Usage

`python3 .../umlmodel <op> --model MODEL.json [--dry-run] [--json] [flags...]`

- `list` prints every op with its one-line purpose. That is the discovery entry.
- `<op> --help` prints one op's params, their examples, and its example call.
- `--json` prints one compact JSON object. The `swarm.uml` Code Mode tool reads it.
- `--args '<json>'` supplies named params in one shot; an explicit flag wins.

The `swarm.uml` Code Mode tool wraps this module. It returns
`{model, op, ok, changed, exit, stdout}` plus the row data of a query. Any key
other than `op`, `model`, `dryRun`, `subsystem`, `view` and `limit` is an op
param. `swarm.help({tool:'uml'})` serves the same catalog as this tool's `list`.

## Ops

Query: `list`, `classes`, `class`, `ops`, `packages`, `levels`, `edges`,
`edges-of`, `violations`, `unassigned`, `dups`, `bad-edges`, `orphans`,
`annotations`, `stats`, `check`.

Mutate: `add-class`, `set-class`, `remove-class`, `rename-class`, `move-class`,
`add-op`, `set-op`, `remove-op`, `add-field`, `set-field`, `add-edge`,
`set-edge-kind`, `remove-edge`, `set-levels`, `set-annotation`, `add-foreign`,
`remove-foreign`, `set-title`, `set-direction`.

## Guarantees

- One op per call: load, validate, apply the op, validate again, then write.
- The writer follows the input file's style: its `ensure_ascii` escape, its
  indent, and its trailing newline. A file that escapes its non-ASCII text stays
  escaped, so one small edit never rewrites the whole file.
- The write is atomic: a temp file in the model's directory plus `os.replace`. A
  reader never sees a half-written model.
- A rejected op exits non-zero with one clear message and leaves the file
  byte-identical.
- An op that changes nothing writes nothing, so the file stays byte-identical.
- `--dry-run` prints the diff and writes nothing.
- `check` validates without an edit, lists every error and warning, and exits
  non-zero only on a real error.

## Validation

An error blocks the write. A warning is reported and allowed.

| check | severity |
|---|---|
| class ids are unique and are namespaces `component.Name` | error |
| an edge endpoint resolves to a class or a `foreign` id | error |
| `kind` is one of `inheritance implements association dependency aggregation composition` | error |
| `stereotype` is one of `class interface abstract enum` | error |
| `direction` is `tb` or `lr` | error |
| `packages[]` each have `id` and `label` | error |
| a class whose first id segment is absent from `levels` | warning (`unassigned`) |

## Files

| File | Holds | Job |
|---|---|---|
| `errors.py` | `UmlModelError` | the one refused-op failure |
| `model.py` | `load`, `dumps`, `write_atomic` | read, canonical text, atomic write |
| `validate.py` | `findings`, `errors`, `warnings` | the invariants |
| `policy.py` | `violations`, `rank_of` | the upstream rank rule |
| `query.py` | `q_*` | the read-only ops |
| `mutate.py` | `add_*`, `set_*`, `remove_*`, ... | the edit ops |
| `diff.py` | `render` | the dry-run diff |
| `ops.py` | `OPS`, `entry` | the op catalog and its help |
| `cli.py` | `main`, `parse`, `run` | the CLI and the one-op pipeline |
| `__main__.py` | entry point | run the directory as a script |
