# Project Facts

Durable, operator-owned project facts: the environment and the conventions the
feature/IR will not state. The orchestrator reads this file and copies `ENV` and
`CONVENTIONS` into every dispatch; roles learn them from the dispatch. Fill the
three sections for the wired project. Delete nothing.

Claims, not facts. On a workspace contradiction: stop and ask. Update only when a field
is missing, the operator asks, or the operator resolves a reported conflict. Never infer
a field from a role's message.

## ENV
- Language / runtime: <fill - the language, its version, and the command that runs the app>
- OS / arch: <fill - the target OS, arch, and container/host split if any>
- Versions (toolchain, deps): <fill - the pinned toolchain and dependency versions>
- Stack: <fill - the processes, services, and stores the system runs>
- Domain knowledge: <fill - the references and skills to read before a task in this domain, with their paths>
- Forbidden actions: <fill - what a role must never do in this project>

## CONVENTIONS

Requirements docs: the project's requirements workplace is the `specs` field in
`harness.json`, printed by `harness.py status` as the `SPECS` row. One document per
subsystem, `NN-<subsystem>.md`; a read-only archive of past designs is never worked in.
The interrogator owns the doc: it asks the operator whether a draft exists, refines the
draft when one does, and creates the doc when none does - before the specifier runs, as
part of the requirement gate's outcome.

Testing (Python), defaults - organized, not a straitjacket:
- Layout mirrors the app: the persistent test root holds `{unit,property}` with
  `test_<app_module>.py`, one subject per file. Gherkin features live in the
  `features` root; step handlers in `acceptance/steps/`.
- Run: never hand-set the test environment. Use `swarm.pytest`, `swarm.acceptance` and
  `swarm.gate`; they set it. A role that must use the shell wraps the command with the
  lane tool: `<pack>/tools/shared/lane <subsystem> pytest -q` from the persistent root.
- A test calls production code and asserts observable behavior (returned value,
  recorded effect, raised error). Arrange-Act-Assert. Never assert on the test's
  own scaffolding.
- Shared construction lives in `conftest.py` fixtures (composed, scoped:
  `session` for immutable, `function` for mutable). Reuse a fixture before a
  helper; reuse a helper before a new module.
- Doubles only at a boundary the app already exposes (a protocol, an injected
  callable, an `env`/`argv` mapping, a clock). Use the simplest double: a small
  fake behind a fixture for stateful collaborators; `monkeypatch`/`unittest.mock`
  for one-off external calls (os, time, subprocess, SDK). Never patch the
  behavior under test, never reimplement app logic in a double, and never build a
  parallel world (a "harness") for tests to assert against.
- Environment independence: pass the environment in (`env=`, `argv=`, `fs=`,
  `cwd=`); never depend on the real OS, filesystem, network or clock, and never
  hardcode container paths. Prefer the app's own observation seams over bespoke
  recorders. A subprocess is allowed only to verify a genuine process property
  (import purity, signals), bounded and rare.
- Gherkin step handlers are thin adapters: call production code, assert, and
  reuse the same fakes/fixtures as the unit tests.
- Freedom: a genuinely different pattern is allowed when the test's docstring
  justifies it; promote it into `conftest.py` once it recurs.
- File hygiene - all files, not only tests: keep files short. Prefer several sibling files in a reasonable length. No hard limit, and never over 600 lines.
  A file over 600 lines is a defect. Split it by behavior into sibling files, with the
  shared helpers in a `*_support.py`. A test file named `test_<module>_<topic>.py`
  groups one behavior. An acceptance step subsystem is a package of parts, one
  `HANDLERS` list each, joined in its `__init__.py`. Never grow a file past the
  limit: split it in the same change.

Code shape (operator-owned) - the shape the code holds today, and the one to keep:
- Length: aim near 50 lines, most files under 100, and never over 600. The 600 ceiling
  is a defect line, not a target.
- Docstrings: the norm. A module, a class and a public function carry a short docstring
  that says what and why. Do not strip them.
- Classes per file: one is the norm. A small second class is allowed when the two serve
  one subject, for example a tiny value object beside its owner.
- Comments: rare, and kept only for a why that the code cannot carry. Most files hold none.

Model routing (operator-owned). `switch_agent_model.py` sets each role's model and its
effort. Change a role there.

Vocabulary (operator-owned). A **subsystem** is a scope: one requirement
document, one feature set, one model, one operator task. It is not a division. A
**module** is the one division: one secret, one writer set, one designer. You cut
the subsystem area into modules. An **interface** is the frozen seam between two
modules. Never call the scope a division.

Craftsmanship and economy (operator-owned). Keep the clean-code craft: types,
contracts, tests, invariants. Never trade a guard for fewer lines - minimal code
with no guards is a bug farm, not economy. But every class, interface, seam, and
split must earn its keep: a guard, a boundary, or a scope answer. Split for the
guard or the secret, never for a future the scope gate excludes. Readability
counts: a split must lower the load of the reader, not add files to open. One
responsibility, one file. One secret, one module. Not one value, one file. The
**scope gate** is where the operator answers the near-term use cases and the
scale, so the design team can YAGNI and not pay for a future that does not exist.

## REFERENCES

List the reference trees and skills this project has, and say what each is for. A role
reads the relevant reference before it designs or codes a task in that domain. Do not
rely on memory.

- `<reference tree>` - <what it holds, and which part of it is authoritative>.
- `<reference tree>` - <what it holds, and which part of it is authoritative>.
- `<skill name>` - load it with the `skill` tool; <what it indexes>.

State where the reference trees sit relative to the pack, so a role can resolve them.
