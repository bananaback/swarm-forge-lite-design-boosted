# Changelog

## 0.2.0 — 2026-11-01

### Added
- `tools/install.py inspect|apply` and `INSTALL.md`: an agent-driven install
  with a brief, one round of questions, and a human-only path.
- `tools/doctor.py`: one-line health checks, exit 1 on a blocking failure.
- `tools/gate.py` and a `gates` map: the protocol names gates, the project owns
  the commands, so a non-Python project changes config and nothing else.
- `tools/update.py check|trial|apply`: reviewed upgrades, a disposable trial
  worktree, and additive migrations.
- `tools/migrate.py`: copies authored design data from the pack into the
  project, never overwriting.
- `config/pack.schema.json`, `config/pack.example.json`, `examples/design/*`.
- `tests/` contract suite (155 tests) with a **90% coverage gate**, and a
  harness CI workflow.

### Changed
- Authored design data lives in `<project>/<design_root>/` as `runtime.json`,
  `overlay.json` and `policy.json`; the pack's `architecture/` is a read-only
  legacy fallback.
- Config resolution is `SWARM_CONFIG` → `config/pack.local.json` →
  `config/pack.json`, with the `<PACK>` token for paths.
- The protocol names gates, not tools; host-neutral wording throughout.

### Removed
- The `gherkin-mutator` task and its tests. The source and spec stay for
  provenance, but nothing in the harness runs or declares them.

### Deprecated
- `config/pack.json` and `architecture/<project>/` remain readable for one
  major release. Nothing is deleted.
