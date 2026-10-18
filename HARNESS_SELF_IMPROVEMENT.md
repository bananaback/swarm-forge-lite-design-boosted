# Harness Self-Improvement — owner goal, current state, next work

**Read this file first.** It is the takeover document for any fresh agent asked
to improve the SwarmForge Lite harness. It records the owner's long-term goal, the
decisions already made, what is finished, what is still open, and how to continue
without re-auditing the whole workspace.

Last updated: **2026-10-18** · branch `v2-python` · pass 3 closes all
actionable P0, P1, and P2 items · both packs green.

## 0. Next action

Pass 3 is finished. Read sections 1–4 and run the baseline in section 4 before
touching the harness.

The only open work left is deliberate:

- **P1 measurement:** run one real, operator-nominated feature through the flat
  flow and record per-role tokens. It needs a real feature and spends real
  tokens, so only the operator starts it.
- **P2 `convo`:** fix its N+1 listing only if it becomes a real tax.
- **P3 scale:** conditional on concurrent sessions. `swarm.sync` stays excluded.

Do not start by re-auditing the workspace. The audit is done. Continue from the
open list.

If the owner explicitly asks for the shared task board or the deferred-goal queue,
work on section 5b instead. Those are features, not cleanup. Do not add them
unless the owner asks.

## 0.5 Read before you improve

Do not edit the harness from this file alone. This page is the map, not the
territory. Read the live files first, in this order. The cost is paid once; it
prevents a “small optimization” that breaks the pipeline.

### Read order

1. **This file**, sections 1–5 and 7. You need the goal, the current shape, the
   baseline, and the open list.
2. **`AGENTS.md`** and **`opencode.json`**. These control search, Code Mode,
   permissions, models, and which instruction file OpenCode loads.
3. **All ten role prompts** in `.opencode/agents/`:
   `orchestrator`, `interrogator`, `specifier`, `architect`, `designer`,
   `critic`, `coder`, `test-reviewer`, `refactorer`, `hotfixer`.
   Read the whole body, not only the frontmatter. You must know what each role
   reads, writes, and hands off.
4. **`swarm-forge-lite/constitution.md`** and its three articles:
   `engineering`, `workflow`, `communication`. These are the binding rules.
5. **`swarm-forge-lite/protocol/`**: `README`, `dispatch`,
   `design-protocol`, `design-procedure`, and every `protocol/<role>.md` answer
   template. This is the pipeline and the stop vocabulary.
6. **`swarm-forge-lite/reference/`**: `module-rules`, `design-quality`,
   `design-craft-*`, `test-quality`, `code-craft`, `model-format`. Skim all;
   read the one your change touches in full.
7. **`swarm-forge-lite/tools/README.md`** and the main tool entry points:
   `lane`, `harness.py`, `harness_cmds.py`, `swarm_json.py`, `swarm_gate.py`,
   `swarm_test.py`, `swarm_core.py`, `record_task.py`, `record_lint_*.py`,
   `questions.py`, `swarm_modules.py`, `swarm_uml.py`.
8. **`swarm-forge-lite/harness_tests/persistent/`**. The tests pin the intended
   behavior more honestly than the prose. Read the unit tests for the area you
   will change.
9. **The record shape**: one migrated subsystem under
   `swarm-forge-lite/design/subsystems/<subsystem>/`. Read
   `requirements.md`, `architecture.md`, one `modules/<m>.md`, `review.md`,
   `SKELETON.md`, and `GOAL.md`. Do not read `model.html`.
10. **The wired project**: `harness.json`, `PROJECT.md`, and the target layout
    under `ds91app-jetson-mount/`. You must know what is shipped and therefore
    untouchable.

### You are ready only when you can answer

- Which role writes `requirements.md`, `architecture.md`, `modules/<m>.md`,
  `SKELETON.md`, and `model.json`?
- Which gate ends each role, and which tool enforces it?
- Which block does a design role end with, and which does a build role use?
- What is per-lane, and what is shared?
- Which five checks does `gate` run by default, and what does `crap:true` add?
- What is generated, and what is authored?
- What does the project ship, and what is only working state?
- Which files are project-owned and must never travel?

If you cannot answer one, read the exact file that owns it before editing.

### Guardrails for a new agent

- Do not redesign the pipeline before you can explain the current one.
- Do not delete a gate because its artifact is small. Delete the artifact, keep
  the check.
- Do not edit more than one layer at a time: tool, prompt, protocol, docs.
  Change them together only when one rule moved.
- Do not touch `model.html`, generated skeletons, `dump/`, or `hot_tests/`.
- Do not touch the shipped project.
- Run the baseline before and after. Update this file with the result.

---

## 1. The owner's goal, in the owner's words

> yes as I suspect, there are still many drift, dead code and too much ceremony
> that waste my tokens. Without drop the methodologies, help me fix the
> inefficient, use your subagents wisely so you not bloat you main context
> window. thanks. This improvement is not kind of invent more, but to decide
> which part can be cut, which we can delete to make the harness lighter and
> more efficient without drop quality from software craftmanship. Do a lot paper
> work is useless while I only need model.html to review and feedback while
> designteam work, I just ship specs, model.html,... gherkin tests and other
> kinds of tests. too much paper work is too much token waste that is
> unneccesary, as owner manage lot of projects I have no time and end not read
> all the artifacts so I think it shouldnt be there, just temp like for agents
> to work on the design is enough. Just make the underlying data for model.html
> more clear that agents read well format. The html is derived and should not be
> operate on as it thousand line of codes, agents should interact though tool to
> edit the diagram it can fetch the current state from tool, not need to read
> the whole model.html, that is one aspect, others can be find out by you to
> optimize. When update things, remember to run it real to verify, and remember
> to update the agents prompts, workflow files to make them aware. Make prompts
> more concise if possible, each word should be choose wisely and have it owns
> weights, I believe we have many representation, same contained meaning, but
> different length because of wordings, we need to fine the optimal one. Also
> concise doesnt mean ambiguous, agent need specific path, expected input output,
> tool description, workflow steps detailed so it not struggling around and
> explore while it should solve the real coding problem not the harness. Check
> the tools set too, I think some of them stale, dead, or not well documented.
> Some overly splitted so the tool schemas is so much that agents not teach well
> in prompts yet to use them wisely. This is not a hard  task but long, so you
> should plan carefully, I allow you to create a markdown file in this workspace
> root to track your harness optimization progress so you are not hurry and can
> take your time to do it careful and correctly. I suffer tokens bills, so I need
> to prior token usage per task. The coding team was good, but from the date I
> adopt design team for clean design, elegant design, the bills is sky rocketed
> without significant gain I expected. But I also cant drop them too, as they are
> somehow fundamental and reduce slop in my shipped code. Again, specs,... which
> is already commited in my jetson mount is the thing I wanna ship, dont prune
> them when optimize.

### The goal in one sentence

**Keep the craft, remove the ceremony.** Every token spent before real work must
earn its place, and every artifact must either be shipped or help an agent decide.

### Non-negotiable constraints

1. **Do not drop the methodologies.** TDD, Gherkin acceptance, frozen
   interfaces, DbC/CQS, SOLID/LSP/ISP/OCP, DRY, CRAP, independent test review,
   and the terminal gate stay.
2. **Do not prune the project.** Specs, features, tests, and source in
   `ds91app-jetson-mount/` are the shipped product. Never remove them.
3. **Do not add a framework to solve a wording problem.** Prefer deletion,
   merging, and one source of truth.
4. **The design team stays.** It reduces shipped slop. Optimize its cost, do not
   remove it.
5. **Ship only what matters:** specs, features, tests, source, and `model.html`
   for review. Design paperwork is working state.
6. **`model.html` is derived.** Agents never read or edit it. They use
   `swarm.uml` on `model.json` and render.
7. **Verify by running.** A change is not done until the real command ran green.
8. **Update the prompts and workflow files in the same change.** A rule that
   exists only in code is invisible to agents.
9. **Concise is not ambiguous.** Keep exact paths, inputs, outputs, tool names,
   exit codes, and stop blocks. Cut repetition and prose, not precision.
10. **Token cost is a design constraint.** Prefer fewer always-loaded bytes,
    fewer tools and schemas, and fewer files an agent must read.

### Anti-goals

- Do not add more design sections, forms, or generated documents.
- Do not keep a compatibility path for a layout no record uses.
- Do not keep a tool because “it might be useful.” Keep it only if a role calls it.
- Do not duplicate a rule in the prompt, the protocol, and the code. State it
  once where it is enforced and point to it.
- Do not write a doc that restates the code. Generate it or delete it.

---

## 2. What the harness is now

SwarmForge Lite is a **process engine for AI coding agents**. A pack supplies
rules, prompts, tools, and gates. A project is wired through `harness.json`. A
**subsystem** is the unit of design, lane, state, and frozen contract.

### Two copies

| Path | Role |
|---|---|
| `swarm-forge-lite/` | **wired project copy**; current for this workspace; points at `../ds91app-jetson-mount` |
| `tdd_harness/` | **git clone**; unwired template and source of truth; push here to publish |
| `ds91app-jetson-mount/` | the application project; its specs and tests are the shipped output |

The project copy is what agents use. The clone is what travels. Sync pack-owned
files to the clone, commit, push, then update `.harness-version` with the full SHA.
`AGENTS.md`, `.opencode/agents/**`, and `opencode.json` are project-owned or
merge-by-hand.

### Roles

| Team | Roles |
|---|---|
| Control plane | `orchestrator` |
| Requirement/design | `interrogator`, `specifier`, `architect`, `designer`, `critic` |
| Build | `coder`, `test-reviewer`, `refactorer` |
| Fast path | `hotfixer` |

The orchestrator writes only `GOAL.md` and dispatches. The design team defines
requirements, freezes interfaces, and produces a skeleton. The build team
implements and verifies. The hotfixer handles one contained defect with no design
ceremony.

### Pipeline

```
interrogator -> specifier -> operator -> architect -> designers (parallel)
  -> critic -> operator -> coder -> test-reviewer -> refactorer -> operator
```

Change classes: `contained` (hotfixer), `module-internal`, `module-cut`,
`requirement-level`, `new-subsystem`. The class comes from the change, not from
record state.

### The flat record

```
design/subsystems/<subsystem>/
  GOAL.md            orchestrator scratchpad, short
  requirements.md    frame, goal, Rn/ACn, Cn, Xn, traceability, DECISIONs
  architecture.md    module map, shared files, ## Interface <module> sections
  modules/<m>.md     contract + design + decisions, one file per module
  SKELETON.md        generated union for coder and refactorer
  model.json         topology, edited only through swarm.uml
  model.html         derived review page; never read, never hand-edited
  review.md          optional critic review
```

The shipped requirement document is `<SPECS>/NN-<subsystem>.md`, a view synced by
`swarm.genDoc`. The shipped behavior is `FEATURES/*.feature`.

The record has **no** `01-interrogator/`, `02-architect/`, `04-critic/`,
`interfaces/`, per-module directories, `COUNTS.md`, `CONTRACTS.md`, or
`model.live.*`. All nine full records are migrated to the flat layout.

### Tools

30 `swarm.*` Code Mode tools:

| Group | Tools |
|---|---|
| resolve | `status`, `modules`, `interface`, `goal`, `envelope`, `doctor` |
| method | `guide` |
| record | `check`, `lintRecord`, `genDoc`, `decisions`, `initWork`, `clean`, `checkEnvelope`, `vocabRename`, `genRecord`, `report` |
| quality | `ruff`, `dry`, `crap`, `pytest`, `acceptance` |
| gherkin | `gherkinParse`, `gherkinDry` |
| UML | `uml` (`query`, `mutate`, `render`, `sync`, `scan`) |
| aggregate | `gate`, `ready`, `page` |
| meta | `docs`, `help` |

`gate({subsystem,feature,crap:true})` is the terminal gate. It returns an
explicit `ok` per check. `ready` fails closed on a check error. `pytest` and
`acceptance` run every configured persistent root.

### Gates that matter

- Requirement: `swarm.ready({role:'interrogator',subsystem})`.
- Specifier: parse + dry-check clean; operator approval.
- Architect: freeze checklist; zero model violations; operator gate.
- Designer: contract complete, one CQS tag, red test per acceptance check.
- Critic: union review, generated skeleton.
- Coder: red for the right reason, then green; ruff clean.
- Test-reviewer: independent accept or reject.
- Refactorer: `swarm.gate({subsystem,feature,crap:true})`.

---

## 3. What was already cut (pass 2)

| Metric | Before | Now | Change |
|---|---:|---:|---:|
| Agent prompts (10) | 121,101 B | 25,410 B | **−79%** |
| Constitution | 31,754 B | 9,125 B | **−71%** |
| Protocol | 55,047 B | 14,173 B | **−74%** |
| Code Mode tools | 36 | **29** | **−7** |
| Record files per subsystem | ~20 | **4 + model** | **−75%** |
| Design-record files | 533 | 101 | mostly generated HTML remains |

Pass 3 did not cut structure. It closed correctness gaps and made one gate
stricter. The one new tool is `doctor`, a startup check:

| Metric | Pass 2 | Pass 3 | Change |
|---|---:|---:|---:|
| Agent prompts (10) | 25,410 B | 25,865 B | +455 B (doctor, two entry points, loop cap) |
| Constitution | 9,125 B | 9,750 B | +625 B (change-class entry, permission precedence) |
| Protocol | 14,173 B | 14,581 B | +408 B (ok rule, entry points, CONFLICT cap) |
| Code Mode tools | 29 | **30** | +1 (`doctor`) |
| Pack self-tests | 279 | **285** | +6 |
| Record errors | 0 | 0 | `trace-no-test` is now an error |

Specific removals:

- Interrogator sections 0–13 as durable files; now one `requirements.md`.
- Architect grammar/CRC/structure/module-map files; now one `architecture.md`.
- Critic four-section directory; now one optional `review.md`.
- Separate interface files; now `## Interface <module>` sections.
- Per-module DESIGN/SKELETON/decisions; now one module file.
- `COUNTS.md`, `CONTRACTS.md`, `model.live.*`.
- Tools `forms`, `form`, `fix`, `triage`, `umlRender`, `umlSync`, `umlScan`.
- Old form-template directories; `design/templates/` holds only `GOAL.md`.

Fixed along the way:

- `ready` passed when a check errored. Now fails closed.
- `gate` could pass on `exit:4` because it dropped `exit`/`errors`. Now uses `ok`.
- `pytest`/`acceptance` ignored the second persistent root. Now run all.
- `clean all` had no lane guard. Now refuses outside a lane.
- `lane` could not forward `--config`. Now `--config PATH` works.
- AC table shape was unchecked. Now checked.
- `spec-number-gap` was a dead hint. Now emitted.
- Terminal gate can include CRAP with `crap:true`.
- `model.json` had four ops with `args` as JSON strings; fixed in `safety-rule-engine`.
- `message-publish` had no `GOAL.md`; added.
- The orchestrator now routes both `STATE` (design roles) and `STATUS` (build roles).

**Settled, do not reopen:** the model sampling is `temperature: 1`,
`top_p: 0.95`. This is the tested best setup for the DeepSeek model in use. Do
not lower it for “determinism”.

---

## 4. Verified current state

Run these before changing anything. They are the baseline.

```bash
# project pack self-tests
cd swarm-forge-lite
tools/shared/lane harness bash -c 'cd harness_tests && python3 -m pytest -q'
# -> 285 passed

# project suite (the shipped code)
tools/shared/lane audio-output bash -c \
  'cd ../ds91app-jetson-mount/deepstream/tests && python3 -m pytest -q'
# -> 641 passed

# lint the tools and tests
python3 tools/shared/ruff4py tools harness_tests
# -> All checks passed

# check the resolved roots, toolchain, and agent model plan
python3 tools/shared/swarm_json.py doctor '{"subsystem":"audio-output"}' | tail -1
# -> "pass": true

# every full record
for s in audio-output detection-extraction message-publish model-file-registry \
         model-version-isolation privacy-recording rule-check-osd \
         safety-rule-engine speaker-alerts; do
  python3 tools/shared/harness.py lint-record --subsystem "$s" | tail -1
done
# -> 0 errors each

# clone self-tests
cd ../tdd_harness/swarm-forge-lite
SWARM_CONFIG=$PWD/harness.selftest.json \
  tools/shared/lane harness bash -c 'cd harness_tests && python3 -m pytest -q'
# -> 263 passed, 4 skipped
```

Five PLANNED subsystems contain only `GOAL.md`: `camera-source`,
`comment-docstring-cleanup`, `design-id-cleanup`, `pipeline`, `quality-baseline`.

Recent costs from `swarm.report` (all historical sessions, before/around the
optimization):

| Role | Output | Reasoning | Sessions |
|---|---:|---:|---:|
| orchestrator | 1,388,544 | 2,057,476 | 26 |
| interrogator | 776,999 | 1,204,294 | 32 |
| designer | 696,868 | 1,373,736 | 46 |
| hotfixer | 801,761 | 1,861,706 | 40 |
| architect | 448,830 | 981,578 | 21 |
| critic | 442,140 | 1,022,968 | 18 |
| coder | 382,084 | 642,203 | 15 |
| test-reviewer | 128,169 | 296,893 | 15 |
| refactorer | 130,133 | 380,238 | 12 |
| specifier | 123,709 | 452,923 | 14 |

The design family plus orchestrator dominates. Measure again after the flat flow
has run on a real feature; do not optimize from this table alone.

---

## 5. Open work, prioritized

These are the remaining real items. Do not re-open closed items above.

### P0 — correctness and trust

- [x] **`trace-no-test` is an error.** A traceability row with no test now fails
  the record gate. The message-publish record named real tests to clear it.
  Files: `tools/shared/record_lint_req.py`, interrogator prompt, stop test.
- [x] **`clean` can drop empty lane directories.** `harness.py clean --drop` and
  `swarm.clean({drop:true})` remove a root that is empty after the clear.
  Files: `harness.py`, `harness_cmds.py`, `harness_values.py`, `swarm_core.py`.
- [x] **Uniform `ok`.** `check`, `lintRecord`, `decisions`, `ruff`, `dry`,
  `format`, `pytest`, `acceptance`, and `crap` return `ok`. `gate` and `ready`
  use it and no longer infer from a count.
- [x] **`check`/`decisions` without a selector.** Both raise a clean `SwarmError`;
  a regression test runs both paths.
- [x] **Model/provider check.** `swarm.doctor` verifies roots, the toolchain,
  agent model shape, and declared variants. An external provider is reported as
  unverifiable, not failed. Files: `swarm_gate.py`, catalog, plugin.

### P1 — design-team cost and ambiguity

- [ ] **Run one real feature through the flat flow** and record per-role tokens.
  Deferred: needs an operator-nominated feature and spends real tokens. Do not
  invent one.
- [x] **Change-class entry points.** `module-internal` starts from the existing
  module file and feature. `module-cut` starts from `architecture.md` and the
  accepted `SKELETON.md`. Files: orchestrator, `protocol/README.md`,
  `communication.md`.
- [x] **Loop caps.** The CONFLICT loop has the same cap as the test-reviewer loop
  (3 rounds), then `CONFLICT: unresolved` goes to the operator. Files:
  orchestrator, `design-protocol.md`.
- [x] **Permissions precedence.** `AGENTS.md` states last-match-wins and the
  global-before-agent order. The existing rules are correct under that rule.
- [x] **`initWork` for non-design roles.** The plugin schema and catalog restrict
  the role enum to interrogator, architect, designer, and critic. The backend
  error names those roles.

### P2 — docs and observability

- [x] **`swarm.doctor`.** Resolves pack/config/roots, checks Python, pytest,
  ruff, coverage, `bb`, `node`, multi-root presence, and the agent model plan.
  Prints one `pass`, with a `{check,ok,detail}` row per item.
- [x] **Tool tables follow the catalog.** `swarm.docs({table:true})` renders the
  Markdown table from `TOOLS`. A test keeps the plugin README equal to it.
- [x] **WIRING/INSTALL/UPDATE.** Direct pytest examples now run through the lane
  wrapper. The clone `UPDATE.md` names the selftest config it actually uses.
- [x] **`PUBLISH-DOCS.md` uses no `find`.** The step-handler count and the
  publish verify block are Python snippets.
- [x] **`page` and handle output stay.** They remain documented as the
  large-result escape hatch; no role reads them in a normal run.
- [ ] **`convo` N+1 listing.** Deferred: it is not a pack tool and is not a
  measured tax yet. Fix only when a session pays for it.

### P3 — scale

- [ ] Per-lane claim metadata (`.swarmforge/<lane>/owner`) if concurrent sessions
  become common.
- [ ] `swarm.report` and `convo` duplicate DB parsing. `convo` is outside the
  pack, so this waits for a real reader change.
- [ ] One-command sync. The operator excluded `swarm.sync`; do not add it
  without explicit approval.

---

## 5b. Planned feature track — cross-session awareness and deferred goals

Two owner-requested features. They are **not implemented**. Build them only when
the owner asks. The design target is deliberately small: **two state files, a few
orchestrator rules, and no new framework** unless a real race proves one is
needed.

The problem they solve:

- The current harness is single-session. An orchestrator knows what it is doing,
  but not what another orchestrator in another session is doing. When files change
  under it, it can be surprised and waste turns re-reading or overwriting.
- The owner often works from a phone. He cannot type a long task description.
  He wants to prepare goals ahead of time and later say “pick the todo goal”.

### F1 — Shared task board

**One file:** `design/TASK_BOARD.md` at the pack root. It is shared by every
session in the workspace. It is small and human-readable.

Proposed shape:

```
# TASK BOARD

Updated: <ISO-8601>
Stale after: <minutes>

| Claim | Session | Role | Subsystem | Task | Files (allowlist) | State | Since |
|---|---|---|---|---|---|---|---|
| C1 | ses_ab12... | orchestrator | audio-output | implement clip gate | app/audio/**, tests/audio/** | active | 12:10 |
```

Rules:

1. The orchestrator reads the board before it classifies or dispatches.
2. The orchestrator writes one claim row when it starts a unit of work. `Session`
   is the full session id. `Files` is the allowlist, not a vague area.
3. Every dispatch carries `#OTHER SESSIONS`: the active claims whose files
   overlap the role's allowlist. The subagent knows a changed file may belong to
   another session.
4. A claim that touches the same subsystem or an overlapping file set is a
   **conflict**. The orchestrator does not dispatch a second writer. It queues,
   asks the operator, or picks a disjoint task.
5. On done or blocked, the orchestrator marks the claim `done` or `blocked` and
   keeps the row for one short history window. It does not delete evidence.
6. A claim older than `Stale after` without an update is `stale`. A stale claim
   is surfaced, not silently broken. The operator decides.
7. The board is **awareness, not a lock**. Correctness still comes from disjoint
   write sets and frozen interfaces.
8. Only the orchestrator writes the board. Subagents report files and results.

What it costs: one short read per dispatch, one row write per task. No new tool
is required for the first version. If concurrent writes corrupt the table, add
one tiny atomic helper later; do not start there.

Acceptance:

- Two separate sessions see each other’s active claims.
- An overlapping dispatch is refused or queued before a subagent starts.
- A subagent receives `#OTHER SESSIONS` and does not treat a foreign change as
  corruption.
- A finished claim is marked done, and a stale claim is visible.
- The board stays under ~100 lines in normal use.

### F2 — Deferred goal queue

**One file:** `design/TODO.md`, operator-owned. It holds tasks that are not for
now. The owner adds them in advance, often from a phone.

Proposed shape:

```
# TODO

| Id | Goal | Subsystem | Ready | Done when | Notes |
|---|---|---|---|---|---|
| T1 | add cross-session board | harness | yes | two sessions see one claim | owner |
| T2 | add deferred queue | harness | no | pick T2 works | wait for T1 |
```

Rules:

1. The operator owns this file. The orchestrator never invents a goal.
2. On “pick the todo goal”, the orchestrator picks the top `Ready: yes` row.
   On “pick T2”, it picks that id.
3. Picking a goal moves it to `TASK_BOARD.md` as an active claim and dispatches
   it through the normal change-class path. It does not bypass the pipeline.
4. When done, the row records the result and the commit. Keep the row short.
5. A blocked goal stays in `TODO.md` with the blocker in `Notes`.
6. Do not auto-pick goals. Only the explicit owner phrase starts one.
7. The queue is not a second requirement record. It is a pointer to work, with
   just enough context to start.

What it costs: one short file read when the owner asks, one row update when the
task finishes. No new tool required.

Acceptance:

- `pick the todo goal` starts the top ready task.
- `pick T2` starts the named task.
- A done task records its commit; a blocked task records its blocker.
- The orchestrator never starts a queued task without the owner’s phrase.
- The file stays under ~80 lines in normal use.

### Minimal implementation plan

1. Add `design/TASK_BOARD.md` and `design/TODO.md` templates with the tables above.
2. Add ~10 lines to `orchestrator.md`: read board, add claim, pass
   `#OTHER SESSIONS`, mark done/stale, honor “pick the todo goal”.
3. Add one line to `protocol/dispatch.md` for `#OTHER SESSIONS`.
4. Add one line to `communication.md`: a foreign change is not corruption; check
   the board before assuming a bug.
5. Add one test that proves a claim is read and an overlap is surfaced. Prefer a
   pure file/parser test over a new tool.
6. Do not add a new Code Mode tool until a real concurrent-write failure appears.

### Open questions for the owner

- Board location: `design/TASK_BOARD.md` (travels with the record) or a
  workspace-level `TASK_BOARD.md` (shared by several projects)? Recommend
  `design/` for one project per workspace.
- Stale threshold: 30 or 60 minutes?
- Should the board show only active claims, or keep the last N done rows?
- Should `TODO.md` live beside the board, or inside the project's `PROJECT.md`?

---

## 6. Recurring failure patterns to avoid

These caused real waste in past sessions. They are more useful than a generic
style guide.

1. **Code Mode tool confusion.** Inside `execute` only `tools.swarm.*`,
   `tools.convo.*`, and `tools.opencode.*` exist. `read`, `shell`, `glob`,
   `grep`, and `codegraph_explore` are top-level tools.
2. **Node/Python assumptions in Code Mode.** No `require`, no `fs`, no Python.
   Use `shell` for filesystem or Python work.
3. **Package directories are not binaries.** `ruff4py` and `dryer` are packages.
   Use `python3 <pack>/tools/shared/ruff4py ...` and
   `PYTHONPATH=<pack>/tools/shared python3 -m dryer`.
4. **Truncated subagent ids.** Pass the full `ses...` id or omit it.
5. **Two-pack confusion.** The project copy is current; the clone is the publish
   source. Every `swarm.*` result carries `pack`; read it.
6. **Stale citations.** Verify `path:line` before dispatch. Use the record's own
   words.
7. **Output truncation.** Page with `limit`/`offset` or use `view:'rows'`; do not
   `head` a large output and assume it is complete.
8. **Paperwork drift.** A generated file that no role reads is waste. Delete it
   or make a tool consume it.

---

## 7. How to continue safely

### Takeover checklist

1. Read this file fully, then complete the onboarding in section 0.5.
2. Run the baseline commands in section 4. If any fail, fix that first and update
   this file.
3. Pick one open item from section 5. Prefer P0.
4. Name the exact files and the verification command before editing.
5. Change code + prompt + protocol + docs in the same pass when the rule moves.
6. Run the real command. Capture the output in section 4 or the change log.
7. Sync the clone, commit, push, update `.harness-version`.
8. Update this file: mark the item, add the commit, adjust the metrics.
9. Stop. Do not expand scope without a new P0/P1 reason.

### Definition of done for one item

- The behavior is enforced by a tool, not only described.
- The prompt or protocol that needs it is updated.
- A test covers the new behavior, or the real command was run and recorded.
- Both packs are green.
- This file is updated.

### How to measure an optimization

- Always-loaded bytes: prompts, constitution, protocol.
- Tool schema count.
- Files an agent must read before work.
- Per-role tokens from `swarm.report` on a real feature.
- The shipped quality gates: tests, ruff, CRAP, acceptance.

Do not call an optimization successful because a file got shorter. Call it
successful when the same gates pass with fewer reads and fewer turns.

### Safe commands

```bash
# status and roots
python3 tools/shared/harness.py status

# one lane
tools/shared/lane <subsystem> <command...>

# project pack self-tests
tools/shared/lane harness bash -c 'cd harness_tests && python3 -m pytest -q'

# clone self-tests
cd tdd_harness/swarm-forge-lite
SWARM_CONFIG=$PWD/harness.selftest.json \
  tools/shared/lane harness bash -c 'cd harness_tests && python3 -m pytest -q'
```

### Do not touch

- `ds91app-jetson-mount/deepstream/docs/specs/**`
- `ds91app-jetson-mount/deepstream/tests/**`
- `ds91app-jetson-mount/deepstream/app/**`
- `design/subsystems/*/model.html` by hand
- The operator-owned commit history

---

## 8. Where things live

| Path | Purpose |
|---|---|
| `.opencode/agents/*.md` | ten role prompts |
| `.opencode/plugins/swarm-tools/` | Code Mode namespace |
| `swarm-forge-lite/constitution/articles/` | binding rules |
| `swarm-forge-lite/protocol/` | pipeline, dispatch, role answer templates |
| `swarm-forge-lite/reference/` | craft: code, tests, design, module rules, model format |
| `swarm-forge-lite/tools/shared/` | lane, harness CLI, record linters, swarm backend, UML, Gherkin |
| `swarm-forge-lite/design/subsystems/` | the living flat records |
| `swarm-forge-lite/harness_tests/` | harness self-tests |
| `tdd_harness/` | publishable clone |
| `HARNESS_SELF_IMPROVEMENT.md` | this file |

---

## 9. Change log

| Date | Commit | Change |
|---|---|---|
| 2026-10-18 | `8bd980a` | baseline before the subtraction pass |
| 2026-10-18 | `0ba4dc2` | flat record, 29 tools, −79% prompts, migrated records, clone sync |
| 2026-10-18 | `a60793d` | takeover guide added; orchestrator accepts `STATE` and `STATUS` |
| 2026-10-18 | `3e4b93f` | pass 3: strict traceability, uniform `ok`, `clean --drop`, `swarm.doctor`, entry points, loop cap, role enum, docs |
| 2026-10-18 | this commit | planned feature track: shared task board and deferred goal queue |
| 2026-10-18 | this commit | onboarding read order and pre-edit understanding gate |

Update this table after every publish. Keep it short: date, commit, one line.
