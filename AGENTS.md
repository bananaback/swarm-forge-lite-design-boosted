# Agent instructions

Read and obey `swarm-forge-lite/constitution.md`, then your role in `.opencode/agents/`.
The constitution points at the protocol in `swarm-forge-lite/protocol/`.
To wire the harness to a project (or back to itself), follow
`swarm-forge-lite/WIRING.md`.

## Search
Probe first, do not sweep. Name the target path before you search.
Skip the cache and generated trees: `node_modules`, `.git`, `.pytest_cache`, `.ruff_cache`, `.hypothesis`, `.codegraph`, `dump/`.
Heavy reference trees are real but slow. `swarm-forge-lite/PROJECT.md` names them. Search one on purpose — name the file or subtree, never in a broad sweep.
Use `codegraph explore`, `glob`, or `grep` with a path. Widen only on a miss. Stop a long scan and narrow it.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

## Code Mode

Inside `execute`, only `tools.convo.*`, `tools.swarm.*`, and `tools.opencode.*` exist. `read`, `shell`, `glob`, `grep`, and `codegraph_explore` are top-level tools, not available inside `execute`. Code Mode is a JavaScript sandbox: no `require`, no `fs`, no Node.js. Use `shell` for filesystem access. Do not write Python inside `execute`.

## Tools

`ruff4py` and `dryer` are package directories, not binaries. Run ruff as `python3 <pack>/tools/shared/ruff4py ...`. Run dryer as `python3 -m dryer` with `<pack>/tools/shared` on `PYTHONPATH`. Run pytest and ruff through the lane wrapper: `<pack>/tools/shared/lane <subsystem> ...`. Never run them directly. A direct run lacks `SWARM_PACK`, `SWARM_TEST_DATA`, and `PYTHONPATH`.

