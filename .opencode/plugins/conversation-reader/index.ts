/**
 * conversation-reader — read any OpenCode conversation straight from the local
 * SQLite database, exposed as Code Mode tools.
 *
 * Why a plugin: inside Code Mode (`execute`) there is no shell and no filesystem,
 * so the DB file cannot be opened directly. A server plugin runs in the OpenCode
 * server process (Bun), can open the DB read-only with `bun:sqlite`, and registers
 * tools with `codemode: true` so they appear in the Code Mode catalog.
 *
 * Tools (namespace `convo`):
 *   convo_list   — list sessions (id, agent, msgs, tokens, cost, title)
 *   convo_read   — full transcript: user/assistant text, reasoning, tool calls + results
 *   convo_search — substring search across messages of one or all sessions
 *
 * Handles both storage generations:
 *   v2  session_v2 + session_message   (current: one row per message, JSON parts)
 *   v1  session + message + part       (older: message row + separate part rows)
 *
 * Read-only. Never writes to the database.
 */

import { Plugin } from "@opencode/plugin"
import { Database } from "bun:sqlite"
import { homedir } from "node:os"
import { join } from "node:path"

const DB_PATH =
  process.env.OPENCODE_DB ?? join(homedir(), ".local", "share", "opencode", "opencode.db")

const OMIT = -1

// --------------------------------------------------------------------------- //
// data model
// --------------------------------------------------------------------------- //

type Part = {
  type: string
  text?: string
  name?: string
  tool?: string
  state?: any
  [k: string]: any
}

type Msg = {
  id: string
  role: string
  time?: number
  agent?: string
  model?: any
  cost?: number
  tokens?: any
  error?: any
  parts: Part[]
}

type Session = {
  id: string
  parent_id?: string | null
  title?: string | null
  directory?: string | null
  agent?: string | null
  model?: string | null
  cost?: number | null
  tokens_input?: number | null
  tokens_output?: number | null
  tokens_reasoning?: number | null
  time_created?: number | null
  time_updated?: number | null
  _tbl: "v1" | "v2"
}

function connect(): Database {
  return new Database(DB_PATH, { readonly: true })
}

function hasTable(db: Database, name: string): boolean {
  return !!db
    .query("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?")
    .get(name)
}

// --------------------------------------------------------------------------- //
// sessions
// --------------------------------------------------------------------------- //

const SESSION_COLS =
  "id,parent_id,slug,title,directory,agent,model,cost,tokens_input,tokens_output," +
  "tokens_reasoning,tokens_cache_read,tokens_cache_write,time_created,time_updated"

function allSessions(db: Database): Session[] {
  const out: Session[] = []
  const seen = new Set<string>()
  const pull = (tbl: string, tag: "v1" | "v2") => {
    if (!hasTable(db, tbl)) return
    for (const r of db.query(`SELECT ${SESSION_COLS} FROM ${tbl}`).all() as any[]) {
      if (seen.has(r.id)) continue
      seen.add(r.id)
      out.push({ ...r, _tbl: tag })
    }
  }
  // v2 preferred (listed first), then v1 fill-ins
  pull("session_v2", "v2")
  pull("session", "v1")
  out.sort((a, b) => (b.time_updated || 0) - (a.time_updated || 0))
  return out
}

function resolveSession(db: Database, ref: string): Session {
  const sessions = allSessions(db)
  const exact = sessions.find((s) => s.id === ref)
  if (exact) return exact
  const matches = sessions.filter((s) => s.id.startsWith(ref))
  if (matches.length === 0) throw new Error(`no session matches: ${ref}`)
  if (matches.length > 1) {
    const list = matches.slice(0, 20).map((s) => `  ${s.id}  ${s.title ?? ""}`).join("\n")
    throw new Error(`ambiguous session ref ${ref}; candidates:\n${list}`)
  }
  return matches[0]
}

// --------------------------------------------------------------------------- //
// messages
// --------------------------------------------------------------------------- //

function normV2(row: any): Msg {
  const d = JSON.parse(row.data)
  const type = row.type as string
  const base: Msg = {
    id: row.id,
    role: type,
    time: d?.time?.created ?? row.time_created,
    agent: d?.agent,
    model: d?.model,
    cost: d?.cost,
    tokens: d?.tokens,
    error: d?.error,
    parts: [],
  }
  if (type === "user") {
    base.parts = [{ type: "text", text: d.text ?? "" }]
    if (d.files?.length) base.parts.push({ type: "files", files: d.files })
    if (d.agents?.length) base.parts.push({ type: "agents", agents: d.agents })
  } else if (type === "assistant") {
    base.parts = Array.isArray(d.content) ? d.content : []
  } else if (type === "synthetic") {
    base.parts = [{ type: "text", text: d.text ?? "" }]
  } else if (type === "compaction") {
    base.parts = [{ type: "text", text: d.summary ?? JSON.stringify(d) }]
  } else {
    const txt = d.text ?? d.description ?? JSON.stringify(d)
    base.parts = [{ type: "text", text: String(txt) }]
  }
  return base
}

function messagesV1(db: Database, sid: string): Msg[] {
  if (!hasTable(db, "message")) return []
  const rows = db
    .query("SELECT id,data,time_created FROM message WHERE session_id=? ORDER BY time_created")
    .all(sid) as any[]
  const parts: Record<string, Part[]> = {}
  if (hasTable(db, "part")) {
    for (const p of db
      .query("SELECT message_id,data FROM part WHERE session_id=? ORDER BY time_created")
      .all(sid) as any[]) {
      try {
        ;(parts[p.message_id] ??= []).push(JSON.parse(p.data))
      } catch {
        /* skip malformed */
      }
    }
  }
  return rows.map((m) => {
    const d = JSON.parse(m.data)
    return {
      id: m.id,
      role: d.role ?? "?",
      time: d?.time?.created ?? m.time_created,
      agent: d.agent,
      model: d.modelID ? { providerID: d.providerID, id: d.modelID } : undefined,
      cost: d.cost,
      tokens: d.tokens,
      error: d.error,
      parts: parts[m.id] ?? [],
    } satisfies Msg
  })
}

function messagesFor(db: Database, session: Session): Msg[] {
  if (session._tbl === "v2" && hasTable(db, "session_message")) {
    const rows = db
      .query(
        "SELECT id,type,seq,data,time_created FROM session_message " +
          "WHERE session_id=? ORDER BY seq,time_created",
      )
      .all(session.id) as any[]
    if (rows.length) return rows.map(normV2)
  }
  return messagesV1(db, session.id)
}

// --------------------------------------------------------------------------- //
// rendering
// --------------------------------------------------------------------------- //

const BANNER = "=".repeat(90)

function ts(ms: number | null | undefined): string {
  if (!ms) return "-"
  return new Date(ms).toLocaleString()
}

function clip(text: string, n: number): string {
  if (n <= 0 || text.length <= n) return text
  return text.slice(0, n) + `\n... [truncated ${text.length - n} chars]`
}

function indent(text: string, pad = "    "): string {
  return text
    .split("\n")
    .map((l) => pad + l)
    .join("\n")
}

function toolName(p: Part): string {
  return p.name ?? p.tool ?? "?"
}

function toolInput(p: Part): string {
  return JSON.stringify(p.state?.input ?? {}, null, 2)
}

function toolResult(p: Part): { text: string; omitted: number } {
  const st = p.state ?? {}
  // v2: state.content is an array of blocks; v1: state.output is a string
  if (Array.isArray(st.content)) {
    const text = st.content
      .map((c: any) =>
        typeof c === "string" ? c : c?.type === "text" ? c.text ?? "" : JSON.stringify(c),
      )
      .join("\n")
    return { text, omitted: 0 }
  }
  if (typeof st.output === "string") return { text: st.output, omitted: 0 }
  if (st.output != null) return { text: JSON.stringify(st.output, null, 2), omitted: 0 }
  return { text: "", omitted: 0 }
}

type RenderOpts = {
  reasoning: boolean
  tools: boolean
  toolOutput: number
  toolInput: number
  maxText: number
  role?: string | null
}

function renderPart(p: Part, o: RenderOpts): string[] {
  const out: string[] = []
  const t = p.type
  if (t === "reasoning") {
    if (!o.reasoning) return out
    const txt = (p.text ?? "").trim()
    if (txt) out.push("    ~ reasoning ~", indent(clip(txt, o.maxText)))
  } else if (t === "text") {
    const txt = (p.text ?? "").trim()
    if (txt) out.push(indent(clip(txt, o.maxText)))
  } else if (t === "tool") {
    if (!o.tools) return out
    const st = p.state ?? {}
    const status = st.status ?? "?"
    out.push(`    >> tool ${toolName(p)} [${status}]`)
    const inputStr = toolInput(p).replace(/\n/g, " ")
    out.push(
      "       input: " + (o.toolInput === OMIT ? "<omitted>" : clip(inputStr, o.toolInput)),
    )
    if (st.error) out.push("       error: " + clip(JSON.stringify(st.error), o.toolOutput))
    const res = toolResult(p)
    if (o.toolOutput === OMIT) {
      out.push(`       output: <omitted ${res.text.length} chars>`)
    } else if (res.text) {
      out.push("       output:", indent(clip(res.text, o.toolOutput), "         "))
    }
    if (st.metadata) out.push("       meta: " + clip(JSON.stringify(st.metadata), o.maxText))
  } else if (t === "files") {
    for (const f of p.files ?? []) {
      out.push("    [file] " + (typeof f === "string" ? f : f.name ?? f.path ?? JSON.stringify(f)))
    }
  } else if (t === "agents") {
    out.push("    [agents] " + JSON.stringify(p.agents))
  } else if (t === "step-finish") {
    if (o.tools) {
      const tk = p.tokens ?? {}
      out.push(
        `    -- step-finish in=${tk.input ?? "?"} out=${tk.output ?? "?"} ` +
          `reason=${tk.reasoning ?? "?"} cache_read=${tk.cache?.read ?? "?"}`,
      )
    }
  }
  // step-start and anything else is intentionally silent in text mode
  return out
}

function renderMessage(m: Msg, o: RenderOpts): string[] {
  if (o.role && m.role !== o.role) return []
  const out: string[] = []
  let head = `\n[${ts(m.time)}] ${m.role.toUpperCase()}`
  if (m.agent) head += `  agent=${m.agent}`
  if (m.model?.id) head += `  model=${m.model.providerID ?? "?"}/${m.model.id}`
  if (m.tokens) {
    head +=
      `  (in=${m.tokens.input ?? 0} out=${m.tokens.output ?? 0}` +
      ` reason=${m.tokens.reasoning ?? 0} cache_read=${m.tokens.cache?.read ?? 0})`
  }
  if (m.cost) head += `  cost=$${m.cost.toFixed(4)}`
  out.push(head)
  if (m.error) out.push("    !! error: " + clip(JSON.stringify(m.error), o.maxText))
  for (const p of m.parts) out.push(...renderPart(p, o))
  return out
}

function sessionHeader(s: Session, count: number): string[] {
  const lines: string[] = []
  lines.push(BANNER)
  lines.push(`SESSION ${s.id}`)
  lines.push(`  title:   ${s.title ?? ""}`)
  lines.push(`  agent:   ${s.agent ?? "?"}   dir: ${s.directory ?? "?"}`)
  lines.push(`  parent:  ${s.parent_id ?? "-"}   storage: ${s._tbl}`)
  lines.push(
    `  created: ${ts(s.time_created)}   updated: ${ts(s.time_updated)}   messages: ${count}`,
  )
  lines.push(
    `  tokens:  in=${s.tokens_input ?? 0} out=${s.tokens_output ?? 0} ` +
      `reason=${s.tokens_reasoning ?? 0}   cost=$${(s.cost ?? 0).toFixed(4)}`,
  )
  lines.push(BANNER)
  return lines
}

function sessionLine(db: Database, s: Session): string {
  let msgs = 0
  try {
    msgs = messagesFor(db, s).length
  } catch {
    msgs = -1
  }
  const title = (s.title ?? "").replace(/\n/g, " ").slice(0, 60)
  return (
    `${s.id}  ${ts(s.time_updated)}  [${s.agent ?? "?"}]  ` +
    `msgs=${String(msgs).padStart(4)}  cost=$${(s.cost ?? 0).toFixed(4)}  ${title}`
  )
}

// --------------------------------------------------------------------------- //
// plugin
// --------------------------------------------------------------------------- //

export default Plugin.define({
  id: "conversation-reader",
  async setup(ctx) {
    await ctx.tool.transform((editor) => {
      editor.namespace({
        name: "convo",
        description: "Read OpenCode conversation history from the local SQLite database.",
      })

      editor.add({
        name: "list",
        description:
          "List OpenCode sessions (newest first). Shows id, updated time, agent, message count, " +
          "cost and title. Optionally filter by substring and include sub-sessions.",
        input: {
          type: "object",
          properties: {
            limit: { type: "integer", description: "max sessions (default 30)" },
            search: { type: "string", description: "substring match on title/agent/dir" },
            all: { type: "boolean", description: "include sub-sessions (default false)" },
            main: { type: "boolean", description: "only top-level sessions" },
          },
          additionalProperties: false,
        },
        options: { namespace: "convo", codemode: true },
        async execute(input: any) {
          const db = connect()
          try {
            const limit: number = input.limit ?? 30
            let sessions = allSessions(db)
            if (input.main) sessions = sessions.filter((s) => !s.parent_id)
            else if (!input.all) sessions = sessions.filter((s) => !s.parent_id)
            if (input.search) {
              const q = String(input.search).toLowerCase()
              sessions = sessions.filter((s) =>
                `${s.title ?? ""} ${s.agent ?? ""} ${s.directory ?? ""}`
                  .toLowerCase()
                  .includes(q),
              )
            }
            const rows = sessions.slice(0, limit)
            const body = rows.map((s) => sessionLine(db, s)).join("\n")
            return {
              content: `${rows.length} session(s):\n\n${body}`,
              metadata: { count: rows.length, db: DB_PATH },
            }
          } finally {
            db.close()
          }
        },
      })

      editor.add({
        name: "read",
        description:
          "Read a conversation transcript by session id or unique prefix. Returns a BOUNDED page by " +
          "default (20 messages, each long text/tool block capped) so it never floods the context. " +
          "Nothing is permanently hidden: raise the caps or page for more.\n" +
          "Paging: output ends with '-- messages X..Y of N --' and a next offset when more remain; " +
          "call again with offset=Y. limit:0 returns the whole session (oversized output is spilled to " +
          "a tool-output file by the harness).\n" +
          "Detail: maxText/toolOutput/toolInput cap block sizes; 0 = no cap, -1 = omit that part. " +
          "reasoning and tools default on (pass false to drop). subs adds sub-sessions. " +
          "format:'json' returns {total,offset,returned,next,messages}.",
        input: {
          type: "object",
          properties: {
            session: { type: "string", description: "session id or unique prefix (required)" },
            subs: { type: "boolean", description: "also read sub-sessions of this session" },
            offset: { type: "integer", description: "start at message index N (default 0)" },
            limit: { type: "integer", description: "max messages per call (default 20); 0 = all" },
            reasoning: { type: "boolean", description: "include reasoning blocks (default true)" },
            tools: { type: "boolean", description: "include tool calls/results (default true)" },
            toolOutput: {
              type: "integer",
              description: "cap each tool result at N chars; 0 = no cap (default 1200), -1 omit",
            },
            toolInput: {
              type: "integer",
              description: "cap each tool input at N chars; 0 = no cap (default 800), -1 omit",
            },
            maxText: {
              type: "integer",
              description: "cap each text/reasoning block at N chars; 0 = no cap (default 1500)",
            },
            role: { type: "string", enum: ["user", "assistant"], description: "only this role" },
            format: { type: "string", enum: ["text", "json"], description: "output format" },
          },
          required: ["session"],
          additionalProperties: false,
        },
        options: { namespace: "convo", codemode: true },
        async execute(input: any) {
          const db = connect()
          try {
            const o: RenderOpts = {
              reasoning: input.reasoning !== false,
              tools: input.tools !== false,
              toolOutput: input.toolOutput ?? 1200,
              toolInput: input.toolInput ?? 800,
              maxText: input.maxText ?? 1500,
              role: input.role ?? null,
            }
            const root = resolveSession(db, String(input.session))
            const sessions: Session[] = [root]
            if (input.subs) {
              const all = allSessions(db)
              const childrenOf = (id: string) => all.filter((s) => s.parent_id === id)
              const stack = [root.id]
              while (stack.length) {
                const cur = stack.shift() as string
                for (const c of childrenOf(cur)) {
                  sessions.push(c)
                  stack.push(c.id)
                }
              }
            }

            // Flat message stream across the selected sessions, then page over it.
            const groups = sessions.map((s) => ({ s, msgs: messagesFor(db, s) }))
            const counts = new Map(groups.map((g) => [g.s.id, g.msgs.length]))
            const entries: { s: Session; m: Msg }[] = []
            for (const g of groups) for (const m of g.msgs) entries.push({ s: g.s, m })
            const total = entries.length
            const offset = Math.max(0, input.offset ?? 0)
            const limit = input.limit ?? 20
            const page = limit > 0 ? entries.slice(offset, offset + limit) : entries.slice(offset)

            if (input.format === "json") {
              const payload = {
                total,
                offset,
                returned: page.length,
                next: offset + page.length < total ? offset + page.length : null,
                messages: page.map((e) => ({ session_id: e.s.id, ...e.m })),
              }
              return { content: JSON.stringify(payload, null, 2) }
            }

            const lines: string[] = []
            let cur: Session | null = null
            for (const e of page) {
              if (e.s !== cur) {
                cur = e.s
                if (lines.length) lines.push("")
                lines.push(...sessionHeader(e.s, counts.get(e.s.id) ?? 0))
              }
              const rendered = renderMessage(e.m, o)
              if (rendered.length) lines.push(...rendered)
            }
            const range = total === 0 ? "0 of 0" : `${offset}..${offset + page.length} of ${total}`
            lines.push(`\n-- messages ${range} --`)
            if (offset + page.length < total) {
              lines.push(`-- more: call again with offset=${offset + page.length} --`)
            }
            const caps: string[] = []
            if (o.maxText > 0) caps.push(`maxText=${o.maxText}`)
            if (o.toolOutput > 0) caps.push(`toolOutput=${o.toolOutput}`)
            if (o.toolInput > 0) caps.push(`toolInput=${o.toolInput}`)
            if (caps.length) {
              lines.push(`-- caps: ${caps.join(" ")} (pass 0 for no cap, -1 to omit) --`)
            }
            return {
              content: lines.join("\n"),
              metadata: { sessions: sessions.length, total, offset, returned: page.length, db: DB_PATH },
            }
          } finally {
            db.close()
          }
        },
      })

      editor.add({
        name: "search",
        description:
          "Substring search across conversation messages. Searches one session when `session` is given, " +
          "otherwise the newest `scan` sessions. Matches user/assistant text and tool input/output.",
        input: {
          type: "object",
          properties: {
            query: { type: "string", description: "substring to find (required)" },
            session: { type: "string", description: "limit search to this session id/prefix" },
            scan: { type: "integer", description: "how many recent sessions to scan (default 100)" },
            limit: { type: "integer", description: "max matches to return (default 40)" },
          },
          required: ["query"],
          additionalProperties: false,
        },
        options: { namespace: "convo", codemode: true },
        async execute(input: any) {
          const db = connect()
          try {
            const q = String(input.query)
            const needle = q.toLowerCase()
            const scan = input.scan ?? 100
            const limit = input.limit ?? 40
            const sessions = input.session
              ? [resolveSession(db, String(input.session))]
              : allSessions(db).slice(0, scan)
            const hits: string[] = []
            for (const s of sessions) {
              for (const m of messagesFor(db, s)) {
                for (const p of m.parts) {
                  let hay = ""
                  if (p.type === "text" || p.type === "reasoning") hay = p.text ?? ""
                  else if (p.type === "tool")
                    hay = `${toolName(p)} ${toolInput(p)} ${toolResult(p).text}`
                  if (hay.toLowerCase().includes(needle)) {
                    const at = hay.toLowerCase().indexOf(needle)
                    const snippet = hay.slice(Math.max(0, at - 60), at + 120).replace(/\n/g, " ")
                    hits.push(`[${s.id}] ${m.role}/${p.type}: ...${snippet}...`)
                    if (hits.length >= limit) break
                  }
                }
                if (hits.length >= limit) break
              }
              if (hits.length >= limit) break
            }
            return {
              content: hits.length
                ? `${hits.length} match(es) for ${JSON.stringify(q)}:\n\n${hits.join("\n")}`
                : `no matches for ${JSON.stringify(q)}`,
              metadata: { matches: hits.length },
            }
          } finally {
            db.close()
          }
        },
      })
    })
  },
})
