import { Plugin } from "@opencode/plugin/tui"
import { TextAttributes } from "@opentui/core"
import { useTerminalDimensions } from "@opentui/solid"
import { For, Show, createMemo, createSignal } from "solid-js"

type Context = Plugin.Context
type Route = ReturnType<Context["ui"]["router"]["current"]>

type State = {
  /** Live session: the default root when none is picked. */
  sessionID: string
  /** Root session whose family is plotted. Any member works too. */
  rootID: string
  /** Top plot: the prompt/output pair, or output alone. */
  top: "tokens" | "output"
  previous: Route | undefined
}
type Tokens = { input: number; output: number; reasoning: number; cache: { read: number; write: number } }
type Info = {
  id: string
  parentID?: string
  title?: string
  agent?: string
  cost?: number
  /** Cumulative over the session's whole life. */
  tokens?: Tokens
  time?: { created?: number; updated?: number }
  revert?: { messageID?: string }
}
/** One bar per role: fresh + cached prompt, generation, deepest context window, and cost. */
type Column = { label: string; fresh: number; cached: number; output: number; context: number; cost: number }
/** One row of a rendered plot: a y-axis label and the bar cell per column. */
type Line = { label: string; tick: boolean; cells: { text: string; tone: Tone }[] }

const num = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 })
const count = new Intl.NumberFormat("en-US")
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 })

/** Space kept between adjacent columns, so bars and labels never touch. */
const GAP = 2
/** Width of one bar; a role's input/output pair sits side by side with a gap. */
const BAR = 2
/** Horizontal padding around the page content. */
const CHROME = 4
/** Quarter lines on the y axis: the "four meters" of the window. */
const METERS = 4
/** Session panel on the right, as 1/RESERVE of the width. */
const RESERVE = 4
/** Sub-cell fill, so a short bar still rises by a fraction of a row. */
const EIGHTHS = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"] as const

const sum = (tokens: Tokens | undefined) =>
  tokens ? tokens.input + tokens.output + tokens.reasoning + tokens.cache.read + tokens.cache.write : 0

/** Prompt tokens not served from cache. */
const freshTokens = (tokens: Tokens | undefined) => tokens?.input ?? 0

/** Prompt tokens served from, or written to, the cache. */
const cachedTokens = (tokens: Tokens | undefined) => (tokens?.cache.read ?? 0) + (tokens?.cache.write ?? 0)

/** Inclusive generation: visible output plus reasoning. */
const outputTokens = (tokens: Tokens | undefined) => (tokens?.output ?? 0) + (tokens?.reasoning ?? 0)

type Message = { id: string; type: string; status?: string; tokens?: Tokens }

/**
 * Ported from `lastAssistantWithUsage` in the host's util/session.ts: the most
 * recent assistant message that carried usage, after the last completed
 * compaction and inside the session's revert boundary. Its tokens are the
 * session's current context window, the number the built-in Context block shows.
 */
function lastAssistantWithUsage(messages: ReadonlyArray<Message>, boundary?: string) {
  const boundaryIndex = boundary ? messages.findIndex((message) => message.id === boundary) : -1
  if (boundary && boundaryIndex === -1) return undefined
  const end = boundaryIndex === -1 ? messages.length : boundaryIndex
  const compactionIndex = messages.findLastIndex(
    (message, index) => message.type === "compaction" && message.status === "completed" && index < end,
  )
  return messages.findLast(
    (message, index) =>
      message.type === "assistant" && message.tokens !== undefined && index > compactionIndex && index < end,
  )
}

const clip = (value: string, width: number) =>
  value.length <= width ? value : `${value.slice(0, Math.max(1, width - 1))}…`

type Tone = "error" | "warning" | "success" | "info"
const stepTone = (value: number, thresholds: readonly number[], tones: readonly Tone[]) => {
  for (let index = 0; index < thresholds.length; index++) {
    if (value < thresholds[index]) return tones[index]
  }
  return tones[tones.length - 1]
}

/** Fixed ceiling of the context-window plot, split into four quarter marks. */
const CONTEXT_MAX = 1_000_000
/** Context colors, keyed to the marks: green through 250K, amber to 750K, then red. */
const CONTEXT_TONES: Tone[] = ["success", "warning", "error"]
/**
 * Curvature of the top plot's y axis. 1 is linear; lower values stretch the
 * small numbers (output) upward. 0.5 is a square root.
 */
const STRETCH = 0.5
/**
 * Curvature of a bar's internal split. Same idea, applied to each segment's
 * share so a small slice (fresh input) still reads. 1 is proportional.
 */
const SHARE_STRETCH = 0.6
/** The three stacked-bar colors, shared by every role so each bar reads the same. */
const INPUT_TONE: Tone = "info"
const CACHE_TONE: Tone = "warning"
const OUTPUT_TONE: Tone = "success"
/** Cache-hit-rate bands: under 95% red, under 98% amber, 98%+ green. */
const RATE_TONES: Tone[] = ["error", "warning", "success"]

/**
 * Root-anchored family walk, mirroring `sessionFamily` in the host's
 * util/session.ts, with one addition: the root row comes first.
 */
function family(all: readonly Info[], from: string): Info[] {
  const byID = new Map(all.map((session) => [session.id, session]))
  const start = byID.get(from)
  if (!start) return []

  const children = new Map<string, Info[]>()
  for (const session of all) {
    if (!session.parentID) continue
    const group = children.get(session.parentID)
    if (group) group.push(session)
    else children.set(session.parentID, [session])
  }

  const rootOf = (session: Info): Info => {
    const parent = session.parentID ? byID.get(session.parentID) : undefined
    return parent ? rootOf(parent) : session
  }

  const rows: Info[] = []
  const walk = (parentID: string) => {
    for (const session of children.get(parentID) ?? []) {
      rows.push(session)
      walk(session.id)
    }
  }

  const top = rootOf(start)
  rows.push(top)
  walk(top.id)
  return rows
}

/**
 * Make a session's whole family readable from the reactive store. Sync up first
 * so the true root is known, then walk down with `children: true` — the runtime
 * option the plugin type omits — so subagents at any allowed depth are loaded.
 * Without the downward walk a cold TUI, or a freshly picked root, shows only the
 * root and none of its subagent sessions.
 */
async function ensureFamily(context: Context, sessionID: string) {
  const sync = context.data.session.sync as (id: string, options?: { children?: boolean }) => Promise<void>
  const syncOne = (id: string) => sync(id).catch(() => undefined)

  if (!context.data.session.get(sessionID)) await syncOne(sessionID)
  let id = sessionID
  for (let depth = 0; depth < 8; depth++) {
    const parentID = context.data.session.get(id)?.parentID
    if (!parentID) break
    if (!context.data.session.get(parentID)) await syncOne(parentID)
    id = parentID
  }
  const rootID = context.data.session.root?.(sessionID) ?? id

  const seen = new Set<string>()
  const load = async (node: string) => {
    if (seen.has(node)) return
    seen.add(node)
    await sync(node, { children: true }).catch(() => undefined)
    // The context window comes from the transcript, so load messages too.
    await context.data.session.message.sync(node).catch(() => undefined)
    const children = (context.data.session.list() as Info[]).filter((session) => session.parentID === node)
    await Promise.all(children.map((child) => load(child.id)))
  }
  await load(rootID)
}

const fmtWhen = (value?: number) => (value ? new Date(value).toLocaleDateString() : "")

/** Root sessions for the picker: prefer the server's full list, fall back to the store. */
async function listRoots(context: Context): Promise<Info[]> {
  const store = context.data.session.list() as Info[]
  try {
    const raw: any = await context.client.session.list({ limit: 200, order: "desc", parentID: "null" })
    const data: Info[] = Array.isArray(raw)
      ? raw
      : Array.isArray(raw?.data)
        ? raw.data
        : Array.isArray(raw?.data?.data)
          ? raw.data.data
          : []
    if (data.length > 0) {
      const merged = new Map<string, Info>()
      for (const session of store) merged.set(session.id, session)
      for (const session of data) merged.set(session.id, session)
      return [...merged.values()].filter((session) => !session.parentID)
    }
  } catch {
    // Offline or older client: the store is still good enough.
  }
  return store.filter((session) => !session.parentID)
}

function mostRecentRoot(context: Context): string | undefined {
  const roots = [...(context.data.session.list() as Info[])].filter((session) => !session.parentID)
  roots.sort((a, b) => (b.time?.updated ?? 0) - (a.time?.updated ?? 0))
  return roots[0]?.id
}

function Page(props: {
  context: Context
  state: readonly [State, (mutation: (draft: State) => void) => void]
  /** Root sessions shown in the right-hand list. */
  roots: () => Info[]
  /** Highlighted row in that list. */
  cursor: () => number
}) {
  const context = props.context
  // `context.theme` is a getter over the live theme signal, so read it through a
  // function: snapshotting it once would freeze the colors on a theme switch.
  const theme = () => context.theme
  const dimensions = useTerminalDimensions()
  const [ui] = props.state

  // One bar per role name. Input and output tokens add up across a role's
  // sessions; the context window does not, so a role reports its deepest one.
  const columns = createMemo<Column[]>(() => {
    const rootID = ui.rootID || ui.sessionID
    if (!rootID) return []
    const map = new Map<string, Column>()
    for (const session of family(context.data.session.list() as Info[], rootID)) {
      const key = session.agent ?? "main"
      const entry = map.get(key) ?? { label: key, fresh: 0, cached: 0, output: 0, context: 0, cost: 0 }
      const last = lastAssistantWithUsage(
        context.data.session.message.list(session.id) as Message[],
        session.revert?.messageID,
      )
      entry.fresh += freshTokens(session.tokens)
      entry.cached += cachedTokens(session.tokens)
      entry.output += outputTokens(session.tokens)
      entry.context = Math.max(entry.context, sum(last?.tokens))
      entry.cost += session.cost ?? 0
      map.set(key, entry)
    }
    return [...map.values()]
  })

  const contentWidth = createMemo(() => dimensions().width - CHROME)

  // The two plots split the page height between them so none is wasted at the
  // bottom; the top takes the floor, the bottom the remainder.
  const heights = createMemo(() => {
    const rows = Math.max(METERS * 2, dimensions().height - 10)
    const top = Math.max(METERS, Math.floor(rows / 2))
    return { top, bottom: Math.max(METERS, rows - top) }
  })

  // Width of the session panel: 1/RESERVE of the page, floored so it never collapses.
  const reserve = createMemo(() => Math.max(6, Math.round(contentWidth() / RESERVE)))

  /**
   * Both plots as plain strings, sharing one geometry so their bars line up
   * column-for-column. Each role gets a pair of side-by-side bars on the top
   * plot — the input bar stacked cached-under-fresh — and one wider bar spanning
   * that pair on the context plot. A cost row labels the top plot; role names
   * label the bottom.
   */
  const chart = createMemo(() => {
    const cols = columns()
    if (cols.length === 0)
      return { labelWidth: 1, token: [], context: [], baseline: "", names: "", costs: "", topLabel: [] }

    // The top plot uses a power curve: cached prompt volume dwarfs generation, so
    // a linear axis would hide every output bar, while a log axis over-stretches
    // it. sqrt lifts small values into view without flattening the two together.
    const promptMax = Math.max(1, ...cols.map((column) => column.fresh + column.cached))
    const outputMax = Math.max(1, ...cols.map((column) => column.output))
    const stretchOf = (max: number) => (value: number) => Math.pow(Math.max(0, value) / max, STRETCH)
    const promptScale = stretchOf(promptMax)
    const outputScale = stretchOf(outputMax)
    // Round tick values, thinned top-down so their rows stay at least two apart.
    const topRow = heights().top
    const marksFor = (max: number, scale: (value: number) => number) => {
      const candidates: number[] = []
      for (let decade = 0; decade <= Math.ceil(Math.log10(max)); decade++)
        for (const multiple of [5, 2, 1]) {
          const value = multiple * 10 ** decade
          if (value <= max) candidates.push(value)
        }
      candidates.push(max)
      const marks: number[] = []
      let previousRow = -Infinity
      for (const value of [...new Set(candidates)].sort((a, b) => b - a)) {
        const row = Math.max(0, Math.min(topRow - 1, Math.round((1 - scale(value)) * topRow)))
        if (row - previousRow >= 2) {
          marks.push(value)
          previousRow = row
        }
        if (marks.length >= 5) break
      }
      return marks
    }
    const promptMarks = marksFor(promptMax, promptScale)
    const outputMarks = marksFor(outputMax, outputScale)
    const contextMarks = Array.from({ length: METERS }, (_, index) => (CONTEXT_MAX * (index + 1)) / METERS)
    // One shared axis column sized to every plot keeps them all left-aligned, so a
    // bar sits over the same name in any plot and the layout does not shift when
    // the top plot toggles.
    const labelWidth = Math.max(
      1,
      ...[...promptMarks, ...outputMarks, ...contextMarks].map((value) => num.format(value).length),
    )

    const usable = contentWidth() - (labelWidth + 2) - reserve()
    const plotWidth = Math.max(cols.length, usable)
    const slots = cols.map((_, index) => {
      const start = Math.round((index * plotWidth) / cols.length)
      const end = Math.round(((index + 1) * plotWidth) / cols.length) - 1
      return { start, cell: Math.max(1, end - start + 1) }
    })
    // One bar width for every column, sized to the narrowest cell so bars stay
    // uniform however the columns round.
    const bar = Math.max(1, Math.min(BAR, Math.floor((Math.min(...slots.map((slot) => slot.cell)) - GAP - 1) / 2)))
    const pair = bar * 2 + 1
    const left = slots.map((slot) => slot.start + Math.max(0, Math.floor((slot.cell - pair) / 2)))
    const after = left.map((value) => value + pair)

    // A label sits on the row its ratio rounds to, so marks stay even at any height.
    const labelsAt = (H: number, marks: readonly { ratio: number; value: number }[]) => {
      const map = new Map<number, string>()
      for (const mark of marks) map.set(Math.min(H - 1, Math.round((1 - mark.ratio) * H)), num.format(mark.value))
      return map
    }
    // A bar's total height comes from the scale, but its segments split by a
    // stretched share: `value/total` raised to SHARE_STRETCH. A value-faithful
    // split makes a small segment (fresh input) an unreadable sliver, so the
    // split is deliberately exaggerated to keep every segment visible.
    const fill = (
      values: number[],
      scale: (value: number) => number,
      tones: readonly Tone[],
      H: number,
      bottom: number,
    ) => {
      const total = values.reduce((a, b) => a + b, 0)
      const height = Math.round(scale(total) * H * 8)
      const weights = values.map((value) => (total > 0 ? Math.pow(value / total, SHARE_STRETCH) : 0))
      const weightTotal = weights.reduce((a, b) => a + b, 0)
      const bounds: number[] = []
      let accumulated = 0
      let previous = 0
      values.forEach((value, index) => {
        accumulated += weights[index] ?? 0
        const share = weightTotal > 0 ? Math.round(height * (accumulated / weightTotal)) : 0
        const next = Math.min(height, Math.max(previous + (value > 0 ? 1 : 0), share))
        bounds.push(next)
        previous = next
      })
      const eighths = Math.max(0, Math.min(8, height - bottom * 8))
      const middle = bottom * 8 + eighths / 2
      let segment = 0
      while (segment < bounds.length - 1 && middle >= bounds[segment]) segment++
      return { eighths, tone: tones[segment] }
    }

    const hitRate = (column: Column) => {
      const prompt = column.cached + column.fresh
      return prompt > 0 ? (column.cached / prompt) * 100 : 0
    }

    const showOutput = () => ui.top === "output"
    const topScale = () => (showOutput() ? outputScale : promptScale)
    const topMarks = () => (showOutput() ? outputMarks : promptMarks)

    const tokenLines = (H: number): Line[] => {
      const labels = labelsAt(
        H,
        topMarks().map((value) => ({ ratio: topScale()(value), value })),
      )
      return Array.from({ length: H }, (_, row) => {
        const bottom = H - 1 - row
        const cells: Line["cells"] = []
        cols.forEach((column, index) => {
          const lead = Math.max(0, left[index] - (index === 0 ? 0 : after[index - 1]))
          if (showOutput()) {
            const generated = fill([column.output], topScale(), [OUTPUT_TONE], H, bottom)
            cells.push({ text: " ".repeat(lead) + EIGHTHS[generated.eighths].repeat(pair), tone: generated.tone })
            return
          }
          const prompt = fill([column.cached, column.fresh], topScale(), [CACHE_TONE, INPUT_TONE], H, bottom)
          const generated = fill([column.output], topScale(), [OUTPUT_TONE], H, bottom)
          cells.push({ text: " ".repeat(lead) + EIGHTHS[prompt.eighths].repeat(bar), tone: prompt.tone })
          cells.push({ text: " " + EIGHTHS[generated.eighths].repeat(bar), tone: generated.tone })
        })
        return { label: labels.get(row) ?? "", tick: labels.has(row), cells }
      })
    }

    // A row of colored labels above the top plot, centered over each role exactly
    // like the cost row below: cache-hit rate, or the exact output count.
    const topLabel = (() => {
      const output = showOutput()
      const cells: Line["cells"] = []
      let cursor = 0
      cols.forEach((column, index) => {
        const slot = slots[index]
        const rate = hitRate(column)
        const text = output ? count.format(column.output) : rate.toFixed(2) + "%"
        const tone = output ? OUTPUT_TONE : stepTone(rate, [95, 98], RATE_TONES)
        const clipped = clip(text, Math.max(1, slot.cell - (output ? 1 : GAP)))
        const offset = slot.start + Math.floor((slot.cell - clipped.length) / 2)
        cells.push({ text: " ".repeat(Math.max(0, offset - cursor)) + clipped, tone })
        cursor = offset + clipped.length
      })
      return cells
    })()

    const contextLines = (H: number): Line[] => {
      const labels = labelsAt(
        H,
        contextMarks.map((value) => ({ ratio: value / CONTEXT_MAX, value })),
      )
      const scale = (value: number) => value / CONTEXT_MAX
      return Array.from({ length: H }, (_, row) => {
        const bottom = H - 1 - row
        const cells: Line["cells"] = []
        cols.forEach((column, index) => {
          const lead = Math.max(0, left[index] - (index === 0 ? 0 : after[index - 1]))
          const tone = stepTone(scale(column.context), [0.25, 0.75], CONTEXT_TONES)
          const meter = fill([column.context], scale, [tone], H, bottom)
          cells.push({ text: " ".repeat(lead) + EIGHTHS[meter.eighths].repeat(pair), tone: meter.tone })
        })
        return { label: labels.get(row) ?? "", tick: labels.has(row), cells }
      })
    }

    // A row of labels, one centered over each column and clipped to its room.
    const labelRow = (texts: string[]) => {
      const cells = Array.from({ length: plotWidth }, () => " ")
      slots.forEach((slot, index) => {
        const text = clip(texts[index], Math.max(1, slot.cell - GAP))
        const offset = slot.start + Math.floor((slot.cell - text.length) / 2)
        for (let i = 0; i < text.length; i++) cells[offset + i] = text[i]
      })
      return cells.join("")
    }

    return {
      labelWidth,
      token: tokenLines(heights().top),
      context: contextLines(heights().bottom),
      baseline: "─".repeat(plotWidth),
      names: labelRow(cols.map((column) => column.label)),
      costs: labelRow(cols.map((column) => usd.format(column.cost))),
      topLabel,
    }
  })

  const heading = createMemo(() => {
    const n = columns().length
    const what = ui.top === "output" ? "Output tokens" : "Input/output tokens"
    return `${what} & context by role · ${n} role${n === 1 ? "" : "s"}`
  })

  // The list keeps the cursor in view: it renders a window of the roots whose
  // size matches the chart column, so a long history never overflows.
  const sessions = createMemo(() => {
    const list = props.roots()
    const visible = Math.max(1, heights().top + heights().bottom + 7)
    if (list.length <= visible) return { start: 0, items: list }
    const start = Math.min(Math.max(0, props.cursor() - (visible >> 1)), list.length - visible)
    return { start, items: list.slice(start, start + visible) }
  })

  const Plot = (input: { lines: Line[] }) => (
    <For each={input.lines}>
      {(line) => (
        <box flexDirection="row">
          <text fg={theme().text.muted} wrapMode="none">
            {line.label.padStart(chart().labelWidth) + " " + (line.tick ? "┤" : "│")}
          </text>
          <For each={line.cells}>
            {(cell) => (
              <text fg={theme().text.feedback[cell.tone].base} wrapMode="none">
                {cell.text}
              </text>
            )}
          </For>
        </box>
      )}
    </For>
  )

  const Baseline = () => (
    <box flexDirection="row">
      <text fg={theme().text.muted} wrapMode="none">
        {"0".padStart(chart().labelWidth) + " └"}
      </text>
      <text fg={theme().text.muted} wrapMode="none">
        {chart().baseline}
      </text>
    </box>
  )

  return (
    <box width="100%" height="100%" flexDirection="column" backgroundColor={theme().background.base}>
      <box flexDirection="row" justifyContent="space-between" paddingLeft={2} paddingRight={2} flexShrink={0}>
        <text fg={theme().text.base} attributes={TextAttributes.BOLD}>
          {heading()}
        </text>
        <text fg={theme().text.muted}>esc back</text>
      </box>

      <Show
        when={columns().length > 0}
        fallback={<text fg={theme().text.muted}>No sessions loaded. Press s to pick one.</text>}
      >
        <box flexGrow={1} minHeight={0} paddingLeft={2} paddingRight={2} flexDirection="row">
          <box width={Math.max(0, contentWidth() - reserve())} flexShrink={0} flexDirection="column">
            <box flexDirection="row" gap={2}>
              <Show when={ui.top === "tokens"}>
                <text fg={theme().text.feedback[CACHE_TONE].base} wrapMode="none">
                  {"█ input cached"}
                </text>
                <text fg={theme().text.feedback[INPUT_TONE].base} wrapMode="none">
                  {"█ input fresh"}
                </text>
              </Show>
              <text fg={theme().text.feedback[OUTPUT_TONE].base} wrapMode="none">
                {"█ output"}
              </text>
              <text fg={theme().text.muted} wrapMode="none">
                √ scale
              </text>
            </box>
            <box flexDirection="row">
              <text fg={theme().text.muted} wrapMode="none">
                {" ".repeat(chart().labelWidth + 2)}
              </text>
              <For each={chart().topLabel}>
                {(cell) => (
                  <text fg={theme().text.feedback[cell.tone].base} wrapMode="none">
                    {cell.text}
                  </text>
                )}
              </For>
            </box>
            <Plot lines={chart().token} />
            <Baseline />
            <box flexDirection="row">
              <text fg={theme().text.muted} wrapMode="none">
                {" ".repeat(chart().labelWidth + 2)}
              </text>
              <text fg={theme().text.base} wrapMode="none">
                {chart().costs}
              </text>
            </box>

            <box height={1} />
            <text fg={theme().text.muted} wrapMode="none">
              context window per role
            </text>
            <Plot lines={chart().context} />
            <Baseline />

            <box flexDirection="row">
              <text fg={theme().text.muted} wrapMode="none">
                {" ".repeat(chart().labelWidth + 2)}
              </text>
              <text fg={theme().text.base} wrapMode="none">
                {chart().names}
              </text>
            </box>
          </box>

          <box width={reserve()} flexShrink={0} flexDirection="column" paddingLeft={1}>
            <text fg={theme().text.muted} wrapMode="none">
              Sessions
            </text>
            <For each={sessions().items}>
              {(session, index) => {
                const selected = () => sessions().start + index() === props.cursor()
                const viewed = () => session.id === ui.rootID
                return (
                  <text fg={selected() ? theme().text.base : theme().text.muted} wrapMode="none">
                    {`${selected() ? "▸" : viewed() ? "•" : " "} ${clip(
                      session.title ?? "(untitled)",
                      Math.max(1, reserve() - 3),
                    )}`}
                  </text>
                )
              }}
            </For>
          </box>
        </box>
      </Show>

      <box flexDirection="row" gap={2} paddingLeft={2} paddingRight={2} flexShrink={0}>
        <text fg={theme().text.muted}>↑↓ select</text>
        <text fg={theme().text.muted}>enter open</text>
        <text fg={theme().text.muted}>s pick</text>
        <text fg={theme().text.muted}>{`t plot: ${ui.top === "output" ? "output" : "input/output"}`}</text>
      </box>
    </box>
  )
}

export default Plugin.define({
  id: "acme.subagent.tokens",
  setup(context) {
    // A fresh key, so the new defaults take effect on reload: `storage.memory`
    // values are shared across plugin generations, so reusing an older key would
    // keep fields from dropped views.
    const state = context.storage.memory<State>("tokens-v5", {
      initial: { sessionID: "", rootID: "", top: "tokens", previous: undefined },
    })
    const [ui, setUi] = state
    const [roots, setRoots] = createSignal<Info[]>([])
    const [cursor, setCursor] = createSignal(0)

    // Rebuild the sidebar list and park the cursor on the session being viewed.
    const refreshRoots = async () => {
      const list = await listRoots(context)
      setRoots(list)
      const at = list.findIndex((session) => session.id === ui.rootID)
      setCursor((current) => (at >= 0 ? at : Math.min(Math.max(0, current), Math.max(0, list.length - 1))))
    }

    const moveCursor = (delta: number) =>
      setCursor((current) => {
        const count = roots().length
        return count === 0 ? 0 : (current + delta + count) % count
      })

    const openRoot = async (index: number) => {
      const pick = roots()[index]
      if (!pick) return
      await ensureFamily(context, pick.id)
      setUi((draft) => {
        draft.rootID = pick.id
        draft.sessionID = pick.id
      })
    }

    const close = () => {
      const previous = ui.previous
      context.ui.router.navigate(previous ?? { type: "home" })
    }

    const pickSession = async () => {
      const list = await listRoots(context)
      if (list.length === 0) {
        context.ui.toast.show({ message: "No sessions found", variant: "warning" })
        return
      }
      const pick = await context.ui.dialog.select({
        title: "Open session",
        current: ui.rootID,
        options: list.map((session) => ({
          title: session.title ?? "(untitled)",
          value: session.id,
          description: `${session.agent ?? "main"} · ${fmtWhen(session.time?.updated)}`,
        })),
      })
      if (!pick) return
      await ensureFamily(context, pick)
      setUi((draft) => {
        draft.rootID = pick
        draft.sessionID = pick
      })
      await refreshRoots()
    }

    context.ui.router.register({
      name: "tokens",
      render: () => <Page context={context} state={state} roots={roots} cursor={cursor} />,
    })

    context.ui.slot({
      append: "app",
      render() {
        // Registered on the always-mounted app slot, not inside the page. A layer
        // created in the page's mount effect is not in the keymap until that
        // effect flushes, which is what swallowed the first keypress after
        // opening. `enabled` scopes it to the tokens route instead.
        context.keymap.layer(() => ({
          mode: "global",
          enabled: () => {
            const route = context.ui.router.current()
            return route.type === "plugin" && route.name === "tokens"
          },
          commands: [
            { id: "tokens.back", bind: "escape", title: "Back", group: "Tokens", run: close },
            { id: "tokens.up", bind: "up,k", title: "Previous session", group: "Tokens", run: () => moveCursor(-1) },
            { id: "tokens.down", bind: "down,j", title: "Next session", group: "Tokens", run: () => moveCursor(1) },
            { id: "tokens.enter", bind: "return", title: "Open session", group: "Tokens", run: () => openRoot(cursor()) },
            {
              id: "tokens.top",
              bind: "t",
              title: "Toggle input/output plot",
              group: "Tokens",
              run: () =>
                setUi((draft) => {
                  draft.top = draft.top === "output" ? "tokens" : "output"
                }),
            },
            { id: "tokens.session", bind: "s", title: "Pick session", group: "Tokens", run: pickSession },
          ],
        }))

        context.keymap.layer(() => ({
          mode: "global",
          commands: [
            {
              id: "acme.tokens.open",
              title: "Tokens & context by role",
              description: "Stacked input/output tokens and current context window per role in a session family",
              group: "Session",
              palette: true,
              slash: { name: "tokens" },
              async run() {
                const current = context.ui.router.current()
                if (current.type === "plugin" && current.name === "tokens") return
                const sessionID = current.type === "session" ? current.sessionID : undefined
                if (sessionID) {
                  await ensureFamily(context, sessionID)
                  setUi((draft) => {
                    draft.sessionID = sessionID
                    draft.rootID = sessionID
                  })
                } else if (!ui.rootID) {
                  const root = mostRecentRoot(context)
                  if (root) setUi((draft) => void (draft.rootID = root))
                }
                setUi((draft) => void (draft.previous = { ...current }))
                await refreshRoots()
                context.ui.router.navigate({ type: "plugin", name: "tokens" })
              },
            },
          ],
        }))

        return null
      },
    })
  },
})
