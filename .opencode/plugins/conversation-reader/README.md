# conversation-reader

Read any OpenCode conversation straight from the local SQLite database, as
**Code Mode tools**. Project-scoped - lives in this repository, not in the
global config, so it only loads for this project.

## Why

Inside Code Mode (`execute`) there is no shell and no filesystem access, so the
database file cannot be opened directly. A server plugin runs inside the
OpenCode server process (Bun), can open the DB read-only with `bun:sqlite`, and
registers its tools with `options.codemode = true` so they appear in the Code
Mode catalog.

## Location

```
<project>/.opencode/plugins/conversation-reader/index.ts
```

Discovered automatically for this project only. OpenCode hot-reloads it; no
restart needed. Verify with `opencode plugin list`.

## Tools

Namespace `convo` (callable in Code Mode as `tools.convo.*`).

| Tool | Purpose |
| --- | --- |
| `convo.list({ limit?, search?, all?, main? })` | List sessions: id, updated, agent, message count, cost, title. |
| `convo.read({ session, offset?, limit?, subs?, reasoning?, tools?, toolOutput?, toolInput?, maxText?, role?, format? })` | Transcript by id or unique prefix, including tool calls and their results. |
| `convo.search({ query, session?, scan?, limit? })` | Substring search across messages (one session, or the newest `scan`). |

`session` accepts any unique id prefix (`ses_ee52fc86` works).

## Bounded by default, fully expandable

`convo.read` never floods the context by default, but nothing is permanently
hidden. Defaults produce one page:

| Option | Default | Notes |
| --- | --- | --- |
| `limit` | `20` messages | `0` = all messages |
| `maxText` | `3000` chars | per text/reasoning block; `0` = no cap |
| `toolOutput` | `3000` chars | per tool result; `0` = no cap, `-1` = omit |
| `toolInput` | `1500` chars | per tool input; `0` = no cap, `-1` = omit |
| `reasoning` | `true` | pass `false` to drop reasoning blocks |
| `tools` | `true` | pass `false` to drop tool calls/results |
| `subs` | `false` | include sub-sessions recursively |
| `format` | `"text"` | `"json"` returns `{total,offset,returned,next,messages}` |

Every page ends with a footer that teaches the next move, e.g.:

```
-- messages 0..20 of 185 --
-- more: call again with offset=20 --
-- caps: maxText=3000 toolOutput=3000 toolInput=1500 (pass 0 for no cap, -1 to omit) --
```

So the agent pages with `offset=20`, or calls `limit: 0` with caps set to `0`
to pull everything in one shot. Oversized results are spilled by the harness to
`~/.local/share/opencode/tool-output/tool_<id>`, which the agent can then read
in chunks with the `read` tool.

`role` filters the message stream **before** paging, so `total`, `next`, and the
page footer describe the filtered set. `convo.list` counts messages with one
grouped query per storage table, never one transcript read per session.

## Usage

```js
// one bounded page (the default)
const page = await tools.convo.read({ session: "ses_ee50c4179f" });

// continue paging
const next = await tools.convo.read({ session: "ses_ee50c4179f", offset: 20 });

// everything, untruncated (expect a large string / spilled file)
const full = await tools.convo.read({
  session: "ses_ee50c4179f", limit: 0, maxText: 0, toolOutput: 0, toolInput: 0,
});

// search across recent sessions
const hits = await tools.convo.search({ query: "longcat", scan: 50 });
```

## Storage generations handled

- **v2** - `session_v2` + `session_message` (one row per message, JSON content
  blocks: `reasoning`, `text`, `tool`, `step-finish`, ...).
- **v1** - `session` + `message` + `part` (fallback for databases that predate
  the v2 migration; tool results live in `part.state.output`).

Read-only; the database is never written.

## Configuration

Set `OPENCODE_DB` to point at a different database file. Default:

```
~/.local/share/opencode/opencode.db
```

## Related

- `opencode_sessions.py` (workspace root) - the same data as a standalone Python
  CLI with compact/verbatim/export views, reading the DB directly.
- Alternative without a plugin: Code Mode can also `fetch` the running server's
  HTTP API (`/api/session`, `/api/session/{id}/message`) using the port and
  password from `~/.config/opencode/service.json`.
