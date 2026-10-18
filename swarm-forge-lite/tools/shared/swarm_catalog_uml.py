# Auto-generated split from swarm_json.py

from swarm_catalog_support import _tool, _with_uml_help

UML_TOOLS = [
    _with_uml_help(
        _tool(
            "uml",
            "uml",
            "umlmodel",
            "Query, mutate, render, sync, or scan a model.json. One op per call.",
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
            "render writes model.html; sync overlays real signatures and CRAP; scan builds a model from a source root. "
            "Any other key is an op param; run op:'list' to discover them.",
            "architect, critic, refactorer",
        )
    ),
]
