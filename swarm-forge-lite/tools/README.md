# Tools

A tool used by more than one role lives in `shared/`; a single-role tool lives
in that role's folder.

```
tools/
├── shared/               # used by more than one role
│   ├── wiring/           # path resolution from harness.json (module)
│   ├── harness.py        # config / status / clean / lint-record / check / guide /
│   │                     #   init-work / decisions / check-envelope / vocab-rename / envelope
│   ├── lane              # the lane wrapper (bash script — no python3 prefix)
│   ├── swarm_json.py     # the Code Mode backend: `swarm_json.py <command> '<json-args>'`
│   ├── record.py         # parse + lint the requirement record (module)
│   ├── questions.py      # the design forms + the method map + the stop-test lines (module)
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
