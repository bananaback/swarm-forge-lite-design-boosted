# Update The Harness - Agent Runbook

**Audience:** an opencode agent acting for the operator. Keep a project's harness and
the tracked pack in step. Read this before you copy a single file.

**One rule above all:** a project-owned file never travels. The pack is the same
everywhere; a project's facts, paths, and extra tests are its own.

---

## 1. The two directions

| Direction | When | Result |
| --- | --- | --- |
| **Publish** (project -> repo) | You changed something in a project's harness that is generic. | The change lands in the repo, on the canonical branch, for every other project. |
| **Pull** (repo -> project) | The repo has newer generic changes. | This project gets the minimum edit that makes it current. |

Where the fix was made decides which one you run:

| You changed | Flow |
| --- | --- |
| a generic file in a project's harness | **Publish**, then bump that project's marker (section 6). |
| the pack itself, in the clone - a defect you found while working on the pack | **Repo-first**: verify in the clone, commit, push, then **pull** (section 7) into every project that needs it, and bump each marker. |
| a project-owned file | Nothing. It never travels. |

**One rule:** a defect fixed anywhere in the pack is published in the same run. Never
leave a fix only in one project's copy - a new project pulls the pack, not your copy.

Never run both directions for one change. Finish, verify, then stop.

## 2. The boundary

Three buckets. Every file belongs to exactly one.

**Repo-owned - the pack is the source of truth. A pull may overwrite these.**

```
swarm-forge-lite/tools/**
swarm-forge-lite/protocol/**
swarm-forge-lite/reference/**
swarm-forge-lite/constitution/**
swarm-forge-lite/design/templates/**
swarm-forge-lite/harness_tests/**
swarm-forge-lite/project_tests/**
swarm-forge-lite/harness.selftest.json
swarm-forge-lite/WIRING.md
swarm-forge-lite/PUBLISH-DOCS.md
.opencode/plugins/**
.opencode/commands/**
INSTALL.md
UPDATE.md
.gitignore
```

**Project-owned - never overwritten, never committed. Report drift, change nothing.**

```
swarm-forge-lite/harness.json
swarm-forge-lite/PROJECT.md
swarm-forge-lite/design/subsystems/**
swarm-forge-lite/dump/  swarm-forge-lite/hot_tests/  swarm-forge-lite/.swarmforge/
.opencode/agents/**
opencode.json
AGENTS.md
```

**Merge by hand - show the upstream diff, let the operator decide.**

```
.opencode/agents/*.md          # project search notes and models inside generic text
switch_agent_model.py          # generic tool, project-owned AGENT_MODELS map
```

**Outside the boundary: a project's own test root.** A project that copied
`project_tests/persistent` into its own repository owns that copy. It sits outside the
ship root, so the boundary does not reach it and neither direction touches it.

- A new project copies the current template, so a fix made in `project_tests/` reaches
  new projects with no extra step.
- An existing project keeps the copy it made. Bring it forward by re-creating the root
  from the template, or by applying the same fix by hand in that project's own repo.
- When one defect exists in both places, publish the template fix first, then apply the
  same edit to each older copy. That second edit is a normal commit in the project's own
  repository, not a sync, and it does not move the marker.

## 3. Local exceptions

A project may own a file the pack ships. It lists them, one glob per line, in
`.harness-local` at the ship root:

```
# Paths this project owns beyond the boundary in UPDATE.md.
# A pull never overwrites or deletes them; it reports upstream changes instead.
swarm-forge-lite/harness_tests/persistent/unit/test_umlview_pages.py
swarm-forge-lite/harness_tests/persistent/unit/test_umlview_layout.py
```

Treat a match as project-owned. If the pack changed the same file, report both and stop.

## 4. The sync marker

`.harness-version` at the ship root records the commit this project was last synced to:

```
branch: v2-python
commit: 3d79d7da0f35cca3953e7e385ee49fd1509ef57b
date: 2026-10-14
skipped: 71fdb75  this project runs its own pytest wrapper
```

Both directions read it first. Without it, fall back to a whole-tree diff and say so in
your report. After a successful publish or pull, write the new commit. Write the `commit:`
value as the full 40-character sha, so the next run resolves `<synced>` without a guess.

A `skipped:` line records a change the operator decided this project does not take
(section 7). Keep the line, so the next pull does not offer that commit again, and name
the reason - a bare sha tells the next agent nothing.

## 5. The staging clone

One working copy of the repo, on the canonical branch. `<clone>` is that directory.
The remote is `origin`, the canonical branch is `v2-python`.

```bash
git -C <clone> fetch origin v2-python
```

Do not create a second clone. Do not commit from the project: the project harness is
not a git repository, and it must not become one.

## 6. Publish (project -> repo)

1. Read `.harness-version`; let `<synced>` be its commit.
2. Put the clone at that commit, so the only difference left is your local change:

   ```bash
   git -C <clone> checkout --detach <synced>
   ```
3. Find what changed locally, over repo-owned paths only:

   ```bash
   diff -rq <clone> <ship-root> | grep -v '<project-owned path>'
   ```
4. Copy those files from the project into the clone. `git -C <clone> status` must show
   only them. If a project-owned or merge-by-hand file appears, remove it from the commit.
5. Return to the branch, then verify in the clone:

   ```bash
   git -C <clone> checkout v2-python
   cd <clone>/swarm-forge-lite/harness_tests && SWARM_PROJECT=<clone> python3 -m pytest -q
   ```
   The clone keeps the placeholder `<PROJECT_ROOT>` in `harness.json` (it is the
   unwired template), so its suite needs `SWARM_PROJECT=<clone>`; see WIRING.md,
   the placeholder contract. The clone's suite must be green. It cannot use project
   data, so a test that needs it belongs in `.harness-local`, not in the clone.
6. Commit and push:

   ```bash
   git -C <clone> commit -m "<what changed and why>"
   git -C <clone> push origin v2-python
   ```
7. Write the full commit sha into the project's `.harness-version`.

## 7. Pull (repo -> project)

A pull is not a copy of the newest tree. It is the diff between `<synced>` and the commit
you move to, applied file by file, and every decision in it is the operator's. Reconcile;
never overwrite blind.

1. Read `.harness-version`; let `<synced>` be its commit. Fetch the clone (section 5).
2. Read the change set - the commits, then the files:

   ```bash
   git -C <clone> log --oneline <synced>..origin/v2-python
   git -C <clone> checkout origin/v2-python
   git -C <clone> diff --name-status <synced>..origin/v2-python
   ```
3. Split the change set. Report, and never apply: every project-owned path (section 2),
   every path matched by `.harness-local` (section 3), and every merge-by-hand path -
   for those, print the upstream diff and stop.
4. **Check each remaining file for local drift before you copy it.** A repo-owned file
   whose project copy differs from `<synced>` was edited here:

   ```bash
   git -C <clone> show <synced>:<file> > /tmp/base
   diff /tmp/base <ship-root>/<file>
   ```
   - It differs, and the edit is a project adaptation: add the path to `.harness-local`,
     report it, and leave the file alone.
   - It differs, and the edit is an accident: reconcile the three sides - the `<synced>`
     base, the local edit, and the upstream change - with the operator, then write the
     merged file. Do not pick one side silently.
   - It is identical: copy the upstream file as-is.
5. Deletions are decisions, not instructions. List every deletion in the diff and get the
   operator's confirmation before removing anything. Never `rsync --delete`.
6. If the operator decides this project does not need a change, do not apply it, and
   record the decision so the next pull does not offer it again (section 4).
7. Verify in the project:

   ```bash
   python3 swarm-forge-lite/tools/shared/harness.py status     # every row [ok]
   cd swarm-forge-lite/harness_tests && python3 -m pytest -q
   ```
   Run the project's acceptance pipeline too when the diff touched `project_tests/`.
8. Write the full commit sha into `.harness-version`.

## 8. Rules

- One direction per run. Publish and pull never share a run.
- A defect fixed anywhere in the pack is published in the same run. A fix that stays in
  one project's copy is invisible to every other project.
- A file outside the ship root is not synced, even when the pack ships its template.
  Fix the template, then fix each older copy in its own repository.
- Keep the clone neutral. Before you push, confirm it holds no project path, name, or
  secret: `grep -rn "<the project root>" <clone>` must find nothing.
- Never commit a project-owned file, and never edit one to make a diff disappear.
- A pull reconciles file by file: the diff since the marker, a drift check before every
  copy, and the operator's decision on every deletion and every skip. Name each file you
  wrote, each file you reported, and each commit you skipped.
- If a repo-owned change collides with `.harness-local`, stop and report the file.
- Always write `.harness-version` last. A stale marker makes the next sync expensive.
- Report back: the direction, the commits, every file written, every file reported, and
  the verification result.
