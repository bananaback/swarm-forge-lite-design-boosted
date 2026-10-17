# Auto-generated split from swarm_json.py

from swarm_catalog_support import _M, _tool, _with_uml_help

UML_TOOLS = [
    _tool(
        "umlRender",
        "uml",
        "render.py",
        "Render model.json to a standalone model.html.",
        [
            (
                "model",
                "string",
                "-",
                "The model.json path, or its name under the subsystem record (required).",
            ),
            _M,
            ("out", "string", "-", "Output HTML path."),
            ("check", "bool", "false", "Flag model errors."),
        ],
        "{model, exit, stdout}",
        "swarm.umlRender({model:'model.json',subsystem:'clip',check:true})",
        {"model": ".../model.json", "exit": 0, "stdout": "wrote ... (0 violations)"},
        "Render model.json to model.html. The output is one line and a file, so it is never compacted.",
        "architect, critic, refactorer",
    ),
    _tool(
        "umlSync",
        "uml",
        "sync_python.py",
        "Overlay the real signatures and CRAP metrics onto the model.",
        [
            (
                "model",
                "string",
                "-",
                "The model.json path, or its name under the subsystem record (required).",
            ),
            _M,
            ("source", "string", "first source root", "Source root to scan."),
            ("crap", "string", "-", "A crapper report to read metrics from."),
            ("out", "string", "-", "Output path."),
        ],
        "{model, exit, stdout}",
        "swarm.umlSync({model:'model.json',subsystem:'clip'})",
        {"exit": 0, "stdout": "wrote .../model.live.json (19 matched, 0 missing)"},
        "Overlay the real signatures and the CRAP metrics. It writes model.live.json, never model.json.",
        "refactorer",
    ),
    _tool(
        "umlScan",
        "uml",
        "scan_python.py",
        "Scan a Python source root into a model.json.",
        [
            ("root", "string", "-", "The source root to scan (required)."),
            ("prefix", "string", "-", "Only include classes under this prefix."),
            ("out", "string", "-", "Output path."),
            ("title", "string", "-", "Model title."),
        ],
        "{root, exit, stdout}",
        "swarm.umlScan({root:'<source_root>'})",
        {"exit": 0, "stdout": "wrote ... (2 packages, 143 subsystems)"},
        "A bootstrap: scan an existing source root into a model.json. The output lands under the artifacts root.",
        "architect",
    ),
    _with_uml_help(
        _tool(
            "uml",
            "uml",
            "umlmodel",
            "Query or mutate a uml model.json: classes, packages, levels, edges, violations, and every edit. One op per call.",
            [
                (
                    "op",
                    "string",
                    "-",
                    "The operation. Run op:'list' for every op, or swarm.help({tool:'uml'}) for the full usage.",
                ),
                (
                    "model",
                    "string",
                    "-",
                    "The model.json path, or its name under the subsystem record.",
                ),
                (
                    "dryRun",
                    "bool",
                    "false",
                    "Print the diff and write nothing.",
                ),
            ],
            "{model, op, ok, changed, exit, stdout} + the row data of a query",
            "swarm.uml({op:'violations',model:'design/subsystems/safety-rule-engine/model.json'})",
            {
                "op": "violations",
                "ok": True,
                "changed": False,
                "exit": 0,
                "count": 0,
                "rows": [],
            },
            "One op runs per call: load, validate, apply, validate, then write atomically. "
            "A rejected op returns ok:false with a message and writes nothing. "
            "Any other key is an op param; run op:'list' to discover them.",
            "architect, critic, refactorer",
        )
    ),
]
