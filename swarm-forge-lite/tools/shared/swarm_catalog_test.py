# Auto-generated split from swarm_json.py

from swarm_catalog_support import _LIMIT, _M, _VIEW, _tool

TEST_TOOLS = [
    _tool(
        "pytest",
        "quality",
        "pytest",
        "Run pytest and return counts and failing tests, not the whole log.",
        [
            _M,
            ("k", "string", "-", "A pytest -k expression."),
            ("paths", "string[]", "-", "Test paths relative to the persistent root."),
            (
                "scope",
                "scoped|full",
                "full when unscoped",
                "full runs the whole suite.",
            ),
        ],
        "{passed, failed, errors, skipped, failures:[{test,reason}], summary, exit, ok}",
        "swarm.pytest({k:'privacy',subsystem:'clip'})",
        {"passed": 97, "failed": 0, "summary": "97 passed in 2.5s"},
        "Counts and failing tests, not the whole log. Scope it with k or paths while you work, and run the full suite once, at the terminal gate.",
        "coder, test-reviewer, refactorer, hotfixer",
    ),
    _tool(
        "acceptance",
        "quality",
        "run_acceptance.py",
        "Run the acceptance pipeline (parse, dry-check, generate, run).",
        [("feature", "string", "*", "A feature stem, or '*' for every feature."), _M],
        "{features, passed, failed, failures, summary, exit, ok}",
        "swarm.acceptance({feature:'privacy_recording'})",
        {"features": ["privacy_recording"], "passed": 27, "failed": 0},
        "Parse, dry-check, generate and run the acceptance for a feature. Name the feature stem; '*' runs every feature.",
        "coder, refactorer, hotfixer",
    ),
    _tool(
        "gherkinParse",
        "gherkin",
        "gherkin-parser",
        "Parse a .feature file to the JSON IR and summarize it.",
        [
            ("feature", "string", "-", "The feature stem (required)."),
            _M,
            ("names", "bool", "false", "Include the scenario names."),
        ],
        "{feature, ir, scenario_count, exit}",
        "swarm.gherkinParse({feature:'privacy_recording'})",
        {"scenario_count": 23, "ir": "dump/privacy_recording.json"},
        "Pass the feature STEM: no path, no .feature. It writes the JSON IR under the artifacts root.",
        "specifier",
    ),
    _tool(
        "gherkinDry",
        "gherkin",
        "ir-dry-checker",
        "Dry-check the IR and summarize the report.",
        [
            (
                "ir",
                "string",
                "-",
                "The IR path, or its name under the artifacts root (required).",
            ),
            ("includeExact", "bool", "false", "Also report exact duplicates."),
            _M,
            _VIEW,
            _LIMIT,
        ],
        "{counts, total} + findings on view:rows",
        "swarm.gherkinDry({ir:'privacy_recording.json'})",
        {"counts": {"near-duplicate": 25, "possible-synonym": 79}, "total": 104},
        "Run it on the ir that gherkinParse returned, or on the bare name.",
        "specifier",
    ),
]
