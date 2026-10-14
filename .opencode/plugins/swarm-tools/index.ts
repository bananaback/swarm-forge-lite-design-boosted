/**
 * swarm-tools — the SwarmForge workflow as Code Mode tools.
 *
 * Why: the pipeline roles call the pack Python over `shell`. Each shell call puts
 * the whole stdout into the model context. Inside Code Mode (`execute`) a tool
 * result stays in the JS runtime, and only the `return` value enters the context.
 *
 * These tools return COMPACT JSON by default. A summary carries counts, not rows.
 * The caller asks for rows (`view:"rows"`) or for a paging handle
 * (`view:"all"` + `swarm.page`). So even a lazy verbatim return is cheap, and a
 * role that composes several calls pays almost nothing.
 *
 * `swarm.gate`, `swarm.ready`, and `swarm.triage` aggregate several checks in one
 * call, so the win does not depend on the caller writing loops.
 *
 * Every tool is a thin wrapper over `swarm-forge-lite/tools/shared/swarm_json.py`,
 * which reuses the same tested Python the shell tools use. No rule moves.
 *
 * Namespace: `swarm` (call in Code Mode as `tools.swarm.*`). Each execute returns
 * a JSON string; parse it with `JSON.parse(result)`.
 *
 * Set `SWARM_PACK` to override the pack location. Default: `<project>/swarm-forge-lite`.
 */

import { Plugin } from "@opencode/plugin"
import { spawnSync } from "node:child_process"
import { existsSync } from "node:fs"
import { dirname, join, resolve } from "node:path"

/** The directory of this plugin file, whatever the server cwd is. */
function pluginDir(): string {
  const meta: any = import.meta as any
  if (meta?.dirname) return meta.dirname
  if (meta?.url) return dirname(new URL(meta.url).pathname)
  return resolve(process.cwd())
}

function findPack(): string {
  const override = process.env.SWARM_PACK
  if (override && existsSync(join(override, "harness.json"))) return override
  const project = resolve(pluginDir(), "..", "..", "..")
  const fromPlugin = join(project, "swarm-forge-lite")
  if (existsSync(join(fromPlugin, "harness.json"))) return fromPlugin
  let dir = resolve(process.cwd())
  for (let i = 0; i < 8; i++) {
    const candidate = join(dir, "swarm-forge-lite")
    if (existsSync(join(candidate, "harness.json"))) return candidate
    if (existsSync(join(dir, "harness.json")) && dir.endsWith("swarm-forge-lite")) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return fromPlugin
}

type Outcome = { ok: boolean; value: any; error?: string }

function call(command: string, args: Record<string, any> = {}): Outcome {
  const pack = findPack()
  const script = join(pack, "tools", "shared", "swarm_json.py")
  if (!existsSync(script)) {
    return { ok: false, value: null, error: `no swarm_json.py at ${script}` }
  }
  // `full:true` is an alias for `view:"rows"`.
  const payload: Record<string, any> = { ...(args ?? {}) }
  if (payload.full === true && payload.view === undefined) payload.view = "rows"
  let res
  try {
    res = spawnSync("python3", [script, command, JSON.stringify(payload)], {
      encoding: "utf8",
      maxBuffer: 128 * 1024 * 1024,
      cwd: pack,
      timeout: 900_000,
    })
  } catch (error: any) {
    return { ok: false, value: null, error: `spawn failed: ${error?.message ?? error}` }
  }
  if (res.error) {
    return { ok: false, value: null, error: `spawn error: ${String((res.error as any)?.message ?? res.error)}` }
  }
  const stdout = (res.stdout ?? "").trim()
  if (!stdout) {
    return { ok: false, value: null, error: `no output (exit ${res.status}); stderr: ${(res.stderr ?? "").trim().slice(0, 500)}` }
  }
  try {
    const value = JSON.parse(stdout)
    if (value && typeof value === "object" && "error" in value) {
      return { ok: false, value, error: String(value.error) }
    }
    if (value === null) {
      return { ok: false, value: null, error: `backend printed null (status ${res.status})` }
    }
    return { ok: true, value }
  } catch {
    return { ok: false, value: null, error: `bad JSON from backend: ${stdout.slice(0, 500)}` }
  }
}

function reply(outcome: Outcome) {
  const content = outcome.ok
    ? JSON.stringify(outcome.value)
    : JSON.stringify({ error: outcome.error ?? "unknown error" })
  return { content, metadata: { ok: outcome.ok, error: outcome.error ?? null } }
}

const SUBSYSTEM = {
  type: "string",
  description: "The subsystem name. Sets SWARM_LANE, so disposable roots stay per subsystem. Same string as the lane and design/subsystems/<subsystem>/.",
}
const ROLE = {
  type: "string",
  description: "The role id: interrogator | architect | designer | critic | specifier | coder | test-reviewer | refactorer | hotfixer.",
}
const VIEW = {
  type: "string",
  enum: ["summary", "rows", "all"],
  description: "summary (default) = counts only. rows = inline rows (cols+rows), capped by limit. all = a paging handle.",
}
const LIMIT = { type: "integer", description: "Max rows when view is rows (default 50)." }

export default Plugin.define({
  id: "swarm-tools",
  async setup(ctx) {
    await ctx.tool.transform((editor) => {
      editor.namespace({
        name: "swarm",
        description:
          "The SwarmForge workflow as Code Mode tools. Compact JSON by default; ask for rows with view:'rows' or a handle with view:'all'. " +
          "Parse each result with JSON.parse. Aggregators: swarm.gate, swarm.ready, swarm.triage. " +
          "For one tool's params, defaults, return shape, and example, call swarm.help({tool:'ruff'}).",
      })

      const add = (
        name: string,
        description: string,
        properties: Record<string, any>,
        command: string,
        schema: Record<string, any> = {},
      ) => {
        editor.add({
          name,
          description,
          input: { type: "object", properties, additionalProperties: false, ...schema },
          options: { namespace: "swarm", codemode: true },
          async execute(input: any) {
            return reply(call(command, input ?? {}))
          },
        })
      }

      // ---- resolve and dispatch -------------------------------------------- //

      add(
        "status",
        "Resolve every configured root and the active lane. Returns {lane, roots:{LABEL:path}, missing:[LABEL]}. " +
          "Pass subsystem to resolve as that lane. Pass wiring:true for the full wiring map. Example: tools.swarm.status({subsystem:'clip'})",
        { subsystem: SUBSYSTEM, wiring: { type: "boolean", description: "Also return the full wiring map (large)." } },
        "status",
      )

      add(
        "modules",
        "The module map, the frozen interfaces, and the module layout of a subsystem. " +
          "Returns {architecture, interfaces:[{id,path}], modules:[{id,design,skeleton}], split_ready}. " +
          "Use it to split the designers. Example: tools.swarm.modules({subsystem:'clip'})",
        { subsystem: SUBSYSTEM },
        "modules",
      )

      add(
        "interface",
        "The frozen interface text of one module. Returns {path,text}. Only the architect edits it. " +
          "Example: tools.swarm.interface({subsystem:'clip',module:'engine-read-view'})",
        { subsystem: SUBSYSTEM, module: { type: "string", description: "The module id (required)." } },
        "interface",
      )

      add(
        "goal",
        "Read or write the orchestrator's scratchpad: design/subsystems/<subsystem>/GOAL.md. " +
          "Returns {path,exists,text}. Pass text to write it. Example: tools.swarm.goal({subsystem:'clip'})",
        {
          subsystem: SUBSYSTEM,
          text: { type: "string", description: "The new scratchpad text. Omit to read." },
        },
        "goal",
      )

      add(
        "envelope",
        "Build a dispatch envelope for one role: every resolved path, the ENV lines, and the stop-test line. " +
          "Returns {fields,env,stop_test,text}. Paste `text` into the subagent prompt. Pass module for a designer. " +
          "Example: tools.swarm.envelope({role:'designer',subsystem:'clip',module:'engine-read-view'})",
        {
          role: ROLE,
          subsystem: SUBSYSTEM,
          module: { type: "string", description: "For a designer: the module id. Sets WORK to modules/<module>/ and LANE to <subsystem>.<module>." },
        },
        "envelope",
      )

      // ---- method map ------------------------------------------------------ //

      add(
        "guide",
        "The method map of a role: form file names, titles, the stop test, and a fetch hint. Compact. " +
          "Use swarm.form for one form, swarm.fix for a finding fix. items:true adds the detail of every item. " +
          "Example: tools.swarm.guide({role:'architect',subsystem:'clip'})",
        { role: ROLE, subsystem: SUBSYSTEM, items: { type: "boolean", description: "Include the instrument and rule of every item." } },
        "guide",
      )

      add(
        "forms",
        "Just the form file names and titles of a role. The smallest method map. " +
          "Example: tools.swarm.forms({role:'architect'})",
        { role: ROLE },
        "forms",
      )

      add(
        "form",
        "One form. For the interrogator: its items, with the instrument and rule of each. " +
          "For every other role: the template file's text. Example: " +
          "tools.swarm.form({role:'architect',file:'3-structure.md'})",
        { role: ROLE, file: { type: "string", description: "The form file name (required)." } },
        "form",
      )

      add(
        "fix",
        "The one-line fix for a finding code. With no code, returns every fix. " +
          "Example: tools.swarm.fix({code:'fit-missing'})",
        {
          code: { type: "string", description: "One finding code." },
          codes: { type: "array", items: { type: "string" }, description: "Several finding codes." },
        },
        "fix",
      )

      // ---- record lint and decisions --------------------------------------- //

      add(
        "check",
        "Lint the record a role wrote, and write its computed stop test. Returns {passed,errors,warnings,byCode,stop_test}. " +
          "view:'rows' adds the findings (cols+rows). This is the design-role edit loop: fix a finding, call it again. " +
          "Example: tools.swarm.check({role:'architect',subsystem:'clip'})",
        { role: ROLE, subsystem: SUBSYSTEM, work: { type: "string", description: "Override the work directory." }, view: VIEW, limit: LIMIT },
        "check",
      )

      add(
        "lintRecord",
        "Lint the accepted subsystem record. Returns {passed,errors,warnings,byCode}. view:'rows' adds the findings. " +
          "Example: tools.swarm.lintRecord({subsystem:'clip'})",
        {
          subsystem: SUBSYSTEM,
          record: { type: "string", description: "Override the record directory." },
          specs: { type: "string", description: "Override the specs root." },
          view: VIEW,
          limit: LIMIT,
        },
        "lint_record",
      )

      add(
        "decisions",
        "The decision ledger. Default returns only the OPEN rows (the ones the gate needs) plus {open,total}. " +
          "all:true returns every row. Example: tools.swarm.decisions({role:'interrogator',subsystem:'clip'})",
        { role: ROLE, subsystem: SUBSYSTEM, work: { type: "string", description: "Override the work directory." }, all: { type: "boolean", description: "Include answered rows." } },
        "decisions",
      )

      add(
        "initWork",
        "Write a role's empty forms to a NEW subsystem's record directory. Refuses when the record exists unless force:true. " +
          "Example: tools.swarm.initWork({role:'architect',subsystem:'clip'})",
        {
          role: ROLE,
          subsystem: SUBSYSTEM,
          work: { type: "string", description: "Override the work directory." },
          force: { type: "boolean", description: "Reset an existing record to empty forms (destructive)." },
        },
        "init_work",
      )

      add(
        "clean",
        "Clear a disposable root of the active lane: hot, state, artifacts, or all. Returns {target,cleared}. " +
          "Example: tools.swarm.clean({target:'hot',subsystem:'clip'})",
        {
          target: { type: "string", enum: ["hot", "state", "artifacts", "all"], description: "Which root to clear (default hot)." },
          subsystem: SUBSYSTEM,
        },
        "clean",
      )

      add(
        "checkEnvelope",
        "Lint a dispatch envelope: the duplicate-block rule and the cite hint. No size limit. " +
          "Returns {pass,repeated,env_twice,long_lines,has_cite,hint}. " +
          "Example: tools.swarm.checkEnvelope({text: envelopeText})",
        { text: { type: "string", description: "The envelope text." }, file: { type: "string", description: "Or a file that holds it." } },
        "check_envelope",
      )

      add(
        "vocabRename",
        "Bulk rename a token across files. Returns {total,files,verified}. " +
          "Example: tools.swarm.vocabRename({old:'oldname',new:'newname',files:['design/subsystems/clip'],dryRun:true})",
        {
          old: { type: "string", description: "The token to replace (required)." },
          new: { type: "string", description: "The replacement (required)." },
          files: { type: "array", items: { type: "string" }, description: "Files or directories (required)." },
          word: { type: "boolean", description: "Whole-word match only." },
          dryRun: { type: "boolean", description: "Report the hits without writing." },
          verify: { type: "boolean", description: "Fail when any occurrence remains." },
        },
        "vocab_rename",
      )

      // ---- quality --------------------------------------------------------- //

      add(
        "ruff",
        "Ruff findings, without the annotated source frames. Default: {total, byCode}. " +
          "view:'rows' gives cols+rows (capped by limit); view:'all' gives a paging handle. " +
          "Example: tools.swarm.ruff({paths:['<source_root>']})",
        { paths: { type: "array", items: { type: "string" }, description: "Files or dirs. Default: the source and persistent roots." }, subsystem: SUBSYSTEM, view: VIEW, limit: LIMIT },
        "ruff",
      )

      add(
        "dry",
        "Duplicate-code pairs (dryer). Default: {total}. view:'rows' gives pairs as ['file:start-end','file:start-end']. " +
          "Example: tools.swarm.dry({paths:['<source_root>']})",
        {
          paths: { type: "array", items: { type: "string" }, description: "Files or dirs. Default: the source roots." },
          minLines: { type: "integer", description: "Minimum candidate size in lines (default 4)." },
          minNodes: { type: "integer", description: "Minimum normalized syntax nodes (default 20)." },
          threshold: { type: "number", description: "Minimum structural similarity score (default 0.82)." },
          subsystem: SUBSYSTEM,
          view: VIEW,
          limit: LIMIT,
        },
        "dry",
      )

      add(
        "pytest",
        "Run pytest. Returns {passed,failed,errors,failures:[{test,reason}],summary,exit}, not the whole log. " +
          "Default: the full persistent suite. Pass k or paths to scope it. " +
          "Example: tools.swarm.pytest({k:'privacy',subsystem:'clip'})",
        {
          subsystem: SUBSYSTEM,
          k: { type: "string", description: "A pytest -k expression." },
          paths: { type: "array", items: { type: "string" }, description: "Test paths relative to the persistent root." },
          scope: { type: "string", enum: ["scoped", "full"], description: "full runs the whole suite." },
        },
        "pytest",
      )

      add(
        "crap",
        "CRAP (complexity x coverage) from the vendored crapper, at the pack's CRAP 10 threshold. " +
          "Default: only the rows above it, plus {total,above}. all:true for every row. " +
          "Example: tools.swarm.crap({reuseFresh:true,subsystem:'clip'})",
        {
          subsystem: SUBSYSTEM,
          filters: { type: "array", items: { type: "string" }, description: "Only report functions whose namespace contains a fragment." },
          sourceRoot: { type: "array", items: { type: "string" }, description: "Override the source roots." },
          reuseFresh: { type: "boolean", description: "Reuse a fresh coverage report." },
          useExisting: { type: "boolean", description: "Read the coverage report without a test run." },
          all: { type: "boolean", description: "Return every row, not just those above the threshold." },
        },
        "crap",
      )

      add(
        "acceptance",
        "Run the acceptance pipeline (parse, dry-check, generate, run). Returns {features,passed,failed,failures,summary,exit}. " +
          "Example: tools.swarm.acceptance({feature:'privacy_recording'})",
        { feature: { type: "string", description: "A feature stem, or '*' for every feature." }, subsystem: SUBSYSTEM },
        "acceptance",
      )

      add(
        "gherkinParse",
        "Parse a .feature to the JSON IR. Returns {feature,ir,scenario_count,exit}. names:true adds the scenario names. " +
          "Example: tools.swarm.gherkinParse({feature:'privacy_recording'})",
        { feature: { type: "string", description: "The feature stem (required)." }, subsystem: SUBSYSTEM, names: { type: "boolean", description: "Include the scenario names." } },
        "gherkin_parse",
      )

      add(
        "gherkinDry",
        "Dry-check an IR. Default: {counts,total}. view:'rows' adds the first findings. " +
          "Example: tools.swarm.gherkinDry({ir:'privacy_recording.json'})",
        {
          ir: { type: "string", description: "The IR path, or its name under the artifacts root (required)." },
          includeExact: { type: "boolean", description: "Also report exact duplicates." },
          subsystem: SUBSYSTEM,
          view: VIEW,
          limit: LIMIT,
        },
        "gherkin_dry",
      )

      // ---- uml ------------------------------------------------------------- //

      add(
        "umlRender",
        "Render model.json to a standalone model.html. Returns {model,exit,stdout}. " +
          "Example: tools.swarm.umlRender({model:'model.json',subsystem:'clip',check:true})",
        {
          model: { type: "string", description: "The model.json path, or its name under the subsystem record (required)." },
          subsystem: SUBSYSTEM,
          out: { type: "string", description: "Output HTML path." },
          check: { type: "boolean", description: "Flag model errors." },
        },
        "uml_render",
      )

      add(
        "umlSync",
        "Overlay the real signatures and CRAP onto the model. Returns {model,exit,stdout}. " +
          "Example: tools.swarm.umlSync({model:'model.json',subsystem:'clip',crap:'dump/crap.txt'})",
        {
          model: { type: "string", description: "The model.json path, or its name under the subsystem record (required)." },
          subsystem: SUBSYSTEM,
          source: { type: "string", description: "Source root to scan. Default: the first configured source root." },
          crap: { type: "string", description: "A crapper text report to read metrics from." },
          out: { type: "string", description: "Output path." },
        },
        "uml_sync",
      )

      add(
        "umlScan",
        "Scan a Python source root into a model.json. Returns {root,exit,stdout}. " +
          "Example: tools.swarm.umlScan({root:'<source_root>'})",
        {
          root: { type: "string", description: "The source root to scan (required)." },
          prefix: { type: "string", description: "Only include classes under this prefix." },
          out: { type: "string", description: "Output path." },
          title: { type: "string", description: "Model title." },
        },
        "uml_scan",
      )

      add(
        "uml",
        "Query or mutate a uml model.json: classes, packages, levels, edges, violations, and every edit. " +
          "One op per call: pass {op, model, ...params}. Run {op:'list'} for every op with its one-line purpose; " +
          "swarm.help({tool:'uml'}) gives every op, its params, an example, and the invariants. " +
          "Any other key is an op param. A query returns {ok,changed,exit,stdout} plus rows. " +
          "A mutate op loads, validates, applies the op, validates again, then writes atomically; a rejected op " +
          "writes nothing, so the file stays byte-identical. dryRun:true prints the diff and writes nothing. " +
          "Example: tools.swarm.uml({op:'violations',model:'design/subsystems/safety-rule-engine/model.json'})",
        {
          op: {
            type: "string",
            description: "The operation. Run {op:'list'} for every op; e.g. classes, edges, violations, add-class, add-edge, set-class.",
          },
          model: { type: "string", description: "The model.json path, or its name under the subsystem record." },
          dryRun: { type: "boolean", description: "Print the diff and write nothing." },
          subsystem: SUBSYSTEM,
        },
        "uml",
        { additionalProperties: true },
      )

      // ---- aggregation and paging ----------------------------------------- //

      add(
        "gate",
        "The terminal gate in one call: dry + ruff + pytest + acceptance. Returns one compact verdict for each, plus pass. " +
          "checks defaults to all four. Example: tools.swarm.gate({subsystem:'clip',feature:'clip_recording'})",
        {
          subsystem: SUBSYSTEM,
          feature: { type: "string", description: "The acceptance feature stem, or '*' for all." },
          checks: { type: "array", items: { type: "string" }, description: "Subset of ['dry','ruff','pytest','acceptance']." },
          k: { type: "string", description: "A pytest -k expression." },
          paths: { type: "array", items: { type: "string" }, description: "Pytest paths." },
          scope: { type: "string", enum: ["scoped", "full"], description: "full runs the whole pytest suite." },
          reuseFresh: { type: "boolean", description: "Reuse a fresh coverage report for dry/crap." },
        },
        "gate",
      )

      add(
        "ready",
        "The record gate in one call: check + lint-record + decisions. Returns each verdict, plus pass. " +
          "checks defaults to all three. Example: tools.swarm.ready({role:'architect',subsystem:'clip'})",
        {
          role: ROLE,
          subsystem: SUBSYSTEM,
          work: { type: "string", description: "Override the work directory (required to gate a designer's module)." },
          checks: { type: "array", items: { type: "string" }, description: "Subset of ['check','record','decisions']." },
        },
        "ready",
      )

      add(
        "triage",
        "A fast read-only snapshot: status + ruff + decisions. checks may add 'pytest' or 'check'. " +
          "Example: tools.swarm.triage({subsystem:'clip'})",
        {
          subsystem: SUBSYSTEM,
          role: { type: "string", description: "The role for the decisions check (default interrogator)." },
          checks: { type: "array", items: { type: "string" }, description: "Subset of ['status','ruff','decisions','pytest','check']." },
        },
        "triage",
      )

      add(
        "genRecord",
        "Generate design/subsystems/<subsystem>/COUNTS.md and CONTRACTS.md from model.json, and " +
          "project design/subsystems/<subsystem>/SKELETON.md from the module skeletons. " +
          "No role keeps a hand count or a hand copy. Example: tools.swarm.genRecord({subsystem:'clip'})",
        { subsystem: SUBSYSTEM },
        "genRecord",
      )

      add(
        "genDoc",
        "Sync a subsystem's requirement document to its record, IN PLACE and keyed by id. " +
          "The document is a view of the record: each row the document already carries takes " +
          "the record's own id and wording, and every other line stays where it is. An id with " +
          "no row in the document is REPORTED and never written. Run it after you edit a " +
          "requirement table. Example: tools.swarm.genDoc({subsystem:'clip'})",
        { subsystem: SUBSYSTEM },
        "genDoc",
      )

      add(
        "report",
        "Report the session cost per role from the OpenCode database: tokens, sessions, minutes. " +
          "Use it to see where the time goes. Example: tools.swarm.report()",
        {},
        "report",
      )

      add(
        "page",
        "Fetch a page of a saved handle (from a view:'all' call). Returns {total,offset,returned,next,items}. " +
          "Example: tools.swarm.page({handle:'abc123',offset:50})",
        {
          handle: { type: "string", description: "The handle id from a view:'all' result (required)." },
          offset: { type: "integer", description: "Start row (default 0)." },
          limit: { type: "integer", description: "Rows per page (default 50); 0 = the rest." },
        },
        "page",
      )

      add(
        "help",
        "One tool's full help: purpose, params (name, type, default, meaning), return shape, an example, and example output. " +
          "With no tool, the whole catalog with groups. Example: tools.swarm.help({tool:'ruff'})",
        { tool: { type: "string", description: "A tool name. With none, the whole catalog." } },
        "help",
      )

      add(
        "docs",
        "The compact catalog: every swarm tool with a group, a summary, and an example. " +
          "For one tool's params and output, call swarm.help({tool}). No arguments.",
        {},
        "docs",
      )
    })
  },
})
