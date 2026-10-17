# Auto-generated split from swarm_json.py

from swarm_catalog_support import _LIMIT, _M, _VIEW, _tool

QUALITY_TOOLS = [
    _tool(
        "ruff",
        "quality",
        "ruff4py",
        "Ruff findings, without the annotated source frames.",
        [
            (
                "paths",
                "string[]",
                "source + persistent roots",
                "Files or dirs to lint.",
            ),
            _M,
            _VIEW,
            _LIMIT,
        ],
        "{total, byCode} + cols/rows on view:rows + handle on view:all",
        "swarm.ruff({paths:['<source_root>']})",
        {"tool": "ruff", "total": 6, "byCode": {"UP035": 2, "UP007": 2, "UP037": 2}},
        "Structured findings, without the source frames. A clean tree reports 0.",
        "coder, refactorer, hotfixer",
    ),
    _tool(
        "dry",
        "quality",
        "dryer",
        "Duplicate-code pairs (dryer).",
        [
            ("paths", "string[]", "source roots", "Files or dirs to scan."),
            ("minLines", "int", "4", "Minimum candidate size in lines."),
            ("minNodes", "int", "20", "Minimum normalized syntax nodes."),
            ("threshold", "number", "0.82", "Minimum structural similarity score."),
            _M,
            _VIEW,
            _LIMIT,
        ],
        "{total} + pairs on view:rows + handle on view:all",
        "swarm.dry({paths:['<source_root>']})",
        {"tool": "dryer", "total": 2, "pairs": [["a.py:449-457", "b.py:433-441"]]},
        "Duplicate-code pairs (dryer). Scope paths to the area you changed.",
        "coder, refactorer",
    ),
    _tool(
        "crap",
        "quality",
        "crapper",
        "CRAP (complexity x coverage), worst first. Default: only the rows above CRAP 10.",
        [
            _M,
            (
                "filters",
                "string[]",
                "-",
                "Only report functions whose namespace contains a fragment.",
            ),
            ("sourceRoot", "string[]", "-", "Override the source roots."),
            (
                "reuseFresh",
                "bool",
                "false",
                "Reuse a fresh coverage report instead of running the tests.",
            ),
            (
                "useExisting",
                "bool",
                "false",
                "Read the coverage report without a test run.",
            ),
            (
                "all",
                "bool",
                "false",
                "Return every row, not just those above the threshold.",
            ),
        ],
        "{total, above, threshold, rows:[{function,namespace,cc,coverage,crap}]}",
        "swarm.crap({reuseFresh:true,subsystem:'clip'})",
        {"total": 53, "above": 0, "threshold": 10.0, "rows": []},
        "CRAP, worst first, from the vendored crapper at the pack's CRAP 10 threshold. A coverage run is slow, so reuseFresh:true skips it when the report is newer than every source and test.",
        "coder, refactorer",
    ),
]
