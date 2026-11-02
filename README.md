# SwarmForge Lite

A role-based development pipeline you drop into a project. Instructions only: no
daemon, no dashboard, no worktrees, no wrapper CLI.

```text
operator → orchestrator → designer → specifier → coder → test-reviewer → refactorer → architect
```

## Cold Start

If you are an agent opening this pack for the first time:

1. Run `python3 tools/doctor.py`. Exit 0 means the install is sound. Exit 1 names
   the one thing to fix, and the remedy.
2. Read `constitution.md`, then the three articles it names.
3. Read `PROJECT.md`: the environment record — the machine, the mounts, the
   target host, the container, and the rules for working in it. It is
   gitignored; `tools/install.py` creates it from `PROJECT.md.example`.
4. Read `protocol/README.md`: the pipeline, the order rule, and the role list.
5. Read `protocol/orchestrator.md` to coordinate, or `protocol/<your-role>.md` if
   you were dispatched as a role.
6. Read the project entry in `config/pack.json` — or `config/pack.local.json`
   when it exists, which wins. `PACK_PROJECT` selects a project and
   `python3 tools/design/arch.py env` prints what resolved.
7. Read `tools/README.md` before running any command.
8. If your role touches design, read `tools/design/README.md`: the spec shape,
   the `arch` commands and the two views.

Nothing outside this directory is part of the pack. Roles are the
`protocol/*.md` files; the host is irrelevant to them.

## Install

Two commands, an agent driving:

```sh
python3 tools/install.py inspect --root ../myproject
python3 tools/install.py apply --answers install.json
```

`inspect` writes a brief where every key is tagged `fact`, `guess` or `missing`;
the agent asks only the `missing` ones. `INSTALL.md` has the full procedure for
an agent (Part 1) and for a human with no agent (Part 2). `doctor` proves the
result.

## Update

Never a blind pull.

```sh
python3 tools/update.py check          # what is available, grouped by risk
python3 tools/update.py trial          # upstream harness against this project, disposable
python3 tools/update.py apply --yes    # migrations, fast-forward, gates, record
```

`check` and `trial` are read-only and safe. `apply` needs `--yes` from the
operator: it runs the additive migrations, fast-forwards, then `doctor` and the
design gates for every project. A dirty worktree or a diverged branch is refused,
never merged.

## The boundary

A pack holds two kinds of state, and they never mix:

| Kind | Home | Versioned | Lost if the pack is wiped |
|---|---|---|---|
| harness: constitution, protocol, tools, guides | the pack | yes | re-clone |
| workspace wiring: `config/pack.json`, `PROJECT.md` | the pack | no (gitignored) | yes, cheap to recreate |
| project knowledge: specs, features, `design/` | the project repo | yes, by the project | no |
| generated output: IR, reports, metrics | pack scratch | no | yes, by re-running |

Authored design data is **not** reproducible, so it belongs to the project:
`design/runtime.json`, `design/overlay.json`, `design/policy.json`. Generated
views stay in the project's docs where the project puts them; the pack's
`architecture/` is a read-only legacy fallback, never written.

## Working With It

You talk to one agent: the orchestrator. You do not pick a role. Roles are
delegated runs, one at a time, by whatever mechanism the host provides.

| You say | Chain |
|---|---|
| "Fix this one thing" / "the test is red" | coder → test-reviewer → architect |
| "Add behavior X" | designer writes the spec and class design → specifier writes the feature → you approve both → coder → test-reviewer → refactorer → architect |
| "Clean this up" | refactorer → architect |
| "Why is this red?" / "show the design another way" | designer |
| "Commit" / "push" | the orchestrator; git stays yours |
| "Update the harness" | `update.py check` and `trial`; `apply` is your call |

You approve once, after the specification. Everything else is a report with the
commands and their exit status.

## Design Rules

1. **The platform provides messaging.** Roles are delegated agents, not
   mailboxes. They share one codebase and coordinate by message; the operator
   owns commits.
2. **Git is the only state.** No board file, no queue, no design record to keep
   in sync.
3. **Instructions, not wrappers.** Every tool is a command in `tools/README.md`.
4. **Quality gated by names, not tools.** The protocol asks for `lint`, `unit`,
   `acceptance`, `dry`, `crap`; the project's `gates` map says how. A project
   with another toolchain changes config and nothing else.
5. **Match the ceremony to the change.** A one-line fix never runs the designer
   or the specifier; if it touches a test, the test reviewer still sees it.

## Layout

```text
constitution.md              entry point
constitution/articles/       engineering, workflow, communication
PROJECT.md.example           template for the environment record (local copy is gitignored)
protocol/README.md           pipeline, order rule, gates
protocol/<role>.md           orchestrator, designer, specifier, coder, test-reviewer, refactorer, architect
config/pack.example.json     the config shape; the live file is local and gitignored
config/pack.schema.json      what a valid config is
INSTALL.md                   agent and human install paths
CONTRIBUTING.md              how to change the harness without breaking it
examples/design/             skeletons for a project's design folder
tools/README.md              exact commands
tools/design/                the design surface: arch, class/runtime views, tests
tools/shared/                config, schema, duplication analyzer, acceptance pipeline
```

## Hosts

There are no per-host adapters, and there will not be. The pack is Markdown plus
tools that ship inside it: any host that can read a file and run a command can
use it. `protocol/orchestrator.md` is the single entry point. If a host cannot
run the protocol, that is a defect in the protocol, not a missing adapter.

## Troubleshooting

- `doctor` fails: the row names the path and the config key. Fix the key in the
  local config and run it again; it is safe to repeat.
- `arch.py` says "no pack config": run `tools/install.py`, or point
  `SWARM_CONFIG` at a config file.
- Paths resolve to the wrong place: `arch.py env` prints the config file, the
  project root and the design folder it actually used.
- A design change is invisible: check `design:` in `arch.py env` — a `warning:`
  line means the legacy pack location is being read instead of the project's.
- `update.py` refuses: a dirty harness or a diverged branch. `check` lists the
  files; upstream the change or resolve the branch first.

## Relation To Earlier Work

This replaces the wrapper era — `swarm_*` catalogs, the `lane` runner,
`harness.py`, and the Code Mode tool surface. The role boundaries come from
uncle bob's four-pack; the quality thresholds come from this workspace's earlier
pack; the transport is the host platform's own delegation.
