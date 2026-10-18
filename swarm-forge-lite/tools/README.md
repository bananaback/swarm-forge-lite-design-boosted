# Tools

A tool used by more than one role lives in `shared/`; a single-role tool lives
in that role's folder.

```
tools/
├── shared/               # used by more than one role
│   ├── wiring/           # path resolution from harness.json (module)
│   ├── harness.py        # facade + CLI entry point (config / status / clean / ...)
│   ├── harness_values.py # value objects, protocols, adapter, OsTree
│   ├── harness_cmds.py   # all cmd_* handlers
│   ├── lane              # the lane wrapper (bash script — no python3 prefix)
│   ├── swarm_json.py     # facade + CLI entry point (Code Mode backend)
│   ├── swarm_support.py  # shared helpers (SwarmError, _paths, _run, ...)
│   ├── swarm_catalog_*.py # tool catalog by domain (core/modules/quality/test/uml/gate)
│   ├── swarm_core.py     # status/envelope/guide/check/... commands
│   ├── swarm_modules.py  # modules/interface/goal commands
│   ├── swarm_quality.py  # ruff/format/dry/crap commands
│   ├── swarm_test.py     # pytest/acceptance/gherkin commands
│   ├── swarm_uml.py      # uml query/mutate/render/sync/scan commands
│   ├── swarm_gate.py     # gate/ready/gen_record/report commands
│   ├── swarm_help.py     # docs/help commands
│   ├── opencode_db.py    # read-only OpenCode DB reader for swarm.report
│   ├── sync_pack.py      # one-command pack -> clone sync (dry run by default)
│   ├── record.py         # facade: re-exports all record names
│   ├── record_parse.py   # Finding, Report, Table, Document, parsing, helpers
│   ├── record_lint_req.py # requirement-family linters
│   ├── record_lint_design.py # design-family linters
│   ├── record_task.py    # lint_task, render_document, resolve_record, ...
│   ├── questions.py      # facade: aggregates interrogator forms, SPECS, STOP_TESTS
│   ├── questions_engine.py # Column, Text, Field, Table, Matrix, Computed, Section, RoleSpec
│   ├── questions_interrogator_a.py # interrogator form data, sections 0-6
│   ├── questions_interrogator_b.py # interrogator form data, sections 7-13
│   ├── aps/              # vendored APS: parser, dry checker, and the mutator (`bb gherkin-mutator`)
│   ├── gherkin-parser    # specifier + coder (bash script — no python3 prefix)
│   ├── gherkin-craft.md  # the phrase and dry-check rules the specifier + coder read
│   ├── umlview/          # design team: model.json -> standalone model.html
│   ├── umlmodel/         # architect, critic, refactorer: query + mutate a uml model.json (swarm.uml)
│   ├── ruff4py/          # coder + refactorer (module; run as `python3 .../ruff4py`)
│   └── dryer/            # refactorer (vendored; run as `python3 -m dryer`)
├── specifier/
│   └── ir-dry-checker    # specifier (bash script — no python3 prefix)
└── refactorer/
    └── crapper/          # refactorer (vendored; run as `python3 -m crapper`)
```
