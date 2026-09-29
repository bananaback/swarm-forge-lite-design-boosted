# Tools

A tool used by more than one role lives in `shared/`; a single-role tool lives
in that role's folder.

```
tools/
├── shared/               # used by more than one role
│   ├── wiring/           # path resolution from harness.json (module)
│   ├── harness.py        # config / status / clean
│   ├── aps/              # vendored Acceptance-Pipeline-Specification
│   ├── gherkin-parser    # specifier + coder
│   ├── gherkin-mutator   # retained APS mutator
│   ├── umlview/          # design team: model.json -> standalone model.html
│   ├── ruff4py/          # coder + refactorer (module)
│   └── dry4py/           # refactorer (module)
├── specifier/
│   └── ir-dry-checker    # specifier
└── refactorer/
    └── crap4py/          # refactorer (module)
```
