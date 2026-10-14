# Update The Harness - Agent Runbook

**Audience:** an opencode agent acting for the operator. Keep a project's harness and
the tracked pack in step. Read this before you copy a single file.

**One rule above all:** a project-owned file never travels. The pack is the same
everywhere; a project's facts, paths, and extra tests are its own.

---

## 1. The two directions

| Direction | When | Result |
| --- | --- | --- |
| **Publish** (project -> repo) | You changed something in the project harness that is generic. | The change lands in the repo, on the canonical branch, for every other project. |
| **Pull** (repo -> project) | The repo has newer generic changes. | This project gets the minimum edit that makes it current. |

Never do both in one run. Finish one direction, verify, then stop.

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
```

Both directions read it first. Without it, fall back to a whole-tree diff and say so in
your report. After a successful publish or pull, write the new commit.

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
   cd <clone>/swarm-forge-lite/harness_tests && python3 -m pytest -q
   ```
   The clone's suite must be green. It cannot use project data, so a test that needs it
   belongs in `.harness-local`, not in the clone.
6. Commit and push:

   ```bash
   git -C <clone> commit -m "<what changed and why>"
   git -C <clone> push origin v2-python
   ```
7. Write the new commit into the project's `.harness-version`.

## 7. Pull (repo -> project)

1. Read `.harness-version`; let `<synced>` be its commit.
2. List what you are missing, and the files it touches:

   ```bash
   git -C <clone> log --oneline <synced>..origin/v2-python
   git -C <clone> diff --stat <synced>..origin/v2-python
   ```
3. Apply only the repo-owned files in that diff, and skip anything matched by
   `.harness-local`:

   ```bash
   git -C <clone> checkout origin/v2-python
   git -C <clone> diff --name-status <synced>..origin/v2-python
   ```
4. Copy each file, one by one, from the clone into the project. Never `rsync --delete`:
   a deletion in the pack is a decision, not an instruction. List every deletion in the
   diff separately and get the operator's confirmation.
5. For a merge-by-hand file, print the upstream diff and stop. Do not apply it.
6. For a project-owned file that drifted, report it and change nothing.
7. Verify in the project:

   ```bash
   python3 swarm-forge-lite/tools/shared/harness.py status     # every row [ok]
   cd swarm-forge-lite/harness_tests && python3 -m pytest -q
   ```
   Run the project's acceptance pipeline too when the diff touched `project_tests/`.
8. Write the new commit into `.harness-version`.

## 8. Rules

- One direction per run. Publish and pull never share a run.
- Keep the clone neutral. Before you push, confirm it holds no project path, name, or
  secret: `grep -rn "<the project root>" <clone>` must find nothing.
- Never commit a project-owned file, and never edit one to make a diff disappear.
- A pull is a copy of named files, not a sync of trees. Name every file you touch, and
  report the ones you did not.
- If a repo-owned change collides with `.harness-local`, stop and report the file.
- Always write `.harness-version` last. A stale marker makes the next sync expensive.
- Report back: the direction, the commits, every file written, every file reported, and
  the verification result.
