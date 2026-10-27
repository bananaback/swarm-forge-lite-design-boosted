# SwarmForge Lite

A role-based development pipeline you drop into a project. Instructions only: no
daemon, no dashboard, no worktrees, no wrapper CLI.

```text
operator → orchestrator → designer → specifier → coder → test-reviewer → refactorer → architect
```

## Cold Start

If you are an agent opening this workspace for the first time:

1. Read `constitution.md`, then the three articles it names.
2. Read `PROJECT.md`: the environment record for the project this pack is wired
   to — the machine, the mount, the Jetson, the app container, and the rules for
   working in it. It is gitignored, so copy `PROJECT.md.example` first if it is
   not there.
3. Read `protocol/README.md`: the pipeline, the order rule, and the role list.
4. Read `protocol/orchestrator.md` to coordinate, or `protocol/<your-role>.md` if
   you were dispatched as a role. The roles are: orchestrator, designer,
   specifier, coder, test-reviewer, refactorer, architect.
5. Read `config/pack.json`: the `projects` map, its `default_project`, and the
   thresholds. A pack serves several projects; `PACK_PROJECT` selects one and
   `arch.py env` prints what resolved.
6. Read `tools/README.md` before running any command, including its **Design
   surface** section.
7. If your role touches design, read `<PACK>/tools/design/README.md`: the spec
   shape, the `arch` commands and the two views. The specs themselves live under
   `<project>/<docs_root>`, where `docs_root` is the entry in `config/pack.json`.

Nothing outside this directory is part of the pack. Do not look for agent
definitions in `.opencode/`; roles are the `protocol/*.md` files.

## Working With It

You talk to one agent: the orchestrator. You do not pick a role, and there are no
agent tabs — roles are dispatched as subagents.

| You say | Chain |
|---|---|
| "Fix this one thing" / "the test is red" | coder → test-reviewer → architect |
| "Add behavior X" | designer writes the spec and class design → specifier writes the feature → you approve both → coder → test-reviewer → refactorer → architect |
| "Clean this up" | refactorer → architect |
| "Why is this red?" / "show the design another way" | designer |
| "Commit" / "push" | the orchestrator; git stays yours |

You approve once, after the specification. Everything else is a report with the
commands and their exit status. Roles run one at a time because they share the
same files.

## Design Rules

1. **The platform provides messaging.** Roles are delegated agents, not
   mailboxes. Roles share one codebase and coordinate by message; the operator
   owns commits.
2. **Git is the only state.** No board file, no queue, no design record to keep
   in sync.
3. **Instructions, not wrappers.** Every tool is a command in `tools/README.md`.
   Nothing imports a harness runtime, so the same pack runs on any agent host.
4. **Quality without mutation.** Ruff, unit tests, acceptance, coverage, CRAP,
   and duplicate analysis. Language and Gherkin mutation were removed: their
   cost outweighed their signal.
5. **Match the ceremony to the change.** A one-line fix never runs the designer
   or the specifier; if it touches a test, the test reviewer still sees it.

## Layout

```text
constitution.md              entry point
constitution/articles/       engineering, workflow, communication
PROJECT.md.example           the template for the environment record (local PROJECT.md is gitignored)
protocol/README.md           pipeline, order rule, gates
protocol/<role>.md           orchestrator, designer, specifier, coder, test-reviewer, refactorer, architect
config/pack.json             projects map, per-project paths, thresholds
architecture/<project>/      runtime.json and design.json, one set per project
tools/README.md              exact commands
tools/design/                the project design surface: arch, class/runtime views, tests
tools/shared/                dryer, APS (gherkin-parser)
tools/refactorer/crapper/
```

## Wire It Up

1. Edit `config/pack.json`: one entry under `projects` per project — its
   `project_root` (relative to this directory), source roots, class root, test
   paths, features directory, docs root, declared specs, acceptance command,
   artifacts root and umlview policy — then name one as `default_project`.
2. Copy `PROJECT.md.example` to `PROJECT.md` and fill it in: the environment
   record every role reads first. `PROJECT.md` is gitignored: it is per-project
   state and never ships.
3. Requirements: `ruff`, `pytest`, `coverage`, `bb` (Babashka) on `PATH`, and
   `tree-sitter` + `tree-sitter-language-pack` for dryer and crapper.

## Run

Open the orchestrator (`protocol/orchestrator.md`) in your platform of choice and
give it the task. It decides the chain, dispatches, and reports what passed.

- New or changed behavior → designer → coder → refactorer → architect
- Structure only → refactorer → architect
- Local fix, no behavior change → coder → architect

Approval is required once: after the specification, before implementation.

## Relation To Earlier Work

This replaces the wrapper era — `swarm_*` catalogs, the `lane` runner,
`harness.py`, and the Code Mode tool surface. The role boundaries come from
uncle bob's `four-pack`; the quality thresholds come from this workspace's
earlier pack; the transport is the host platform's own delegation.
