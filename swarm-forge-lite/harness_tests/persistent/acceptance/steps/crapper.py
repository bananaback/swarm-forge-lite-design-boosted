"""Step handlers for the crapper feature.

The handlers drive the pack's own `crap` tool (`swarm_json.py crap`) against a
temporary project. The tool runs the vendored crapper, which reads the coverage
report the handlers write under the project's artifacts root.
"""

import json

from .support import (
    SWARM_JSON,
    run_tool,
    step,
    temp_project,
    write_config,
    write_text,
)

SIMPLE = "def simple():\n    return 1\n"

FOUR = (
    "def four(x):\n"
    "    if x == 1:\n"
    "        return 1\n"
    "    if x == 2:\n"
    "        return 2\n"
    "    if x == 3:\n"
    "        return 3\n"
    "    return 0\n"
)


def _lcov(module, hits) -> str:
    lines = [f"SF:{module}"]
    lines += [f"DA:{number},{count}" for number, count in hits.items()]
    lines.append("end_of_record")
    return "\n".join(lines) + "\n"


def _project(world, modules):
    """Build a temporary project with a harness config and a coverage report."""
    project = temp_project(world)
    source = project / "src"
    records = []
    for name, body, hits in modules:
        module = write_text(source / name, body)
        records.append(_lcov(module, hits))
    config = write_config(
        project,
        {
            "workspace_root": ".",
            "artifacts_root": "dump",
            "hot_tests": "hot_tests",
            "source_roots": ["src"],
        },
    )
    report = project / "dump" / "target" / "coverage" / "python" / "lcov.info"
    write_text(report, "".join(records))
    env = dict(world.state["env"])
    env["SWARM_CONFIG"] = str(config)
    world.state["crap"] = {"project": project, "env": env}
    return project


def _run(world, args):
    state = world.state["crap"]
    process = run_tool(
        SWARM_JSON, ["crap", json.dumps(args)], state["env"], cwd=state["project"]
    )
    state["process"] = process
    state["report"] = json.loads(process.stdout)


def _report(world):
    return world.state["crap"]["report"]


def _row(world, name):
    for row in _report(world)["rows"]:
        if row["function"] == name:
            return row
    raise AssertionError(f"no row for {name!r} in {_report(world)['rows']}")


def _given_covered(world, params, match):
    _project(world, [("sample.py", SIMPLE, {1: 1, 2: 1})])


def _given_absent(world, params, match):
    _project(world, [("four.py", FOUR, {})])


def _given_pair(world, params, match):
    _project(
        world,
        [
            ("sample.py", SIMPLE, {1: 1, 2: 1}),
            ("four.py", FOUR, {}),
        ],
    )


def _given_alpha_beta(world, params, match):
    _project(
        world,
        [
            ("alpha.py", FOUR, {}),
            ("beta.py", FOUR, {}),
        ],
    )


def _when_existing(world, params, match):
    _run(world, {"useExisting": True})


def _when_existing_all(world, params, match):
    _run(world, {"useExisting": True, "all": True})


def _when_filtered(world, params, match):
    _run(world, {"useExisting": True, "filters": [match.group(1)]})


def _then_covered(world, params, match):
    row = _row(world, "simple")
    assert (row["cc"], row["coverage"], row["crap"]) == (1, "100.0%", "1.0"), row


def _then_absent(world, params, match):
    row = _row(world, "four")
    assert (row["coverage"], row["crap"]) == ("0.0%", "20.0"), row


def _then_above(world, params, match):
    report = _report(world)
    assert report["above"] == 1, report
    assert [row["function"] for row in report["rows"]] == ["four"], report


def _then_all(world, params, match):
    functions = {row["function"] for row in _report(world)["rows"]}
    assert functions == {"simple", "four"}, functions


def _then_filtered(world, params, match):
    namespaces = [row["namespace"] for row in _report(world)["rows"]]
    assert namespaces == ["alpha"], namespaces


def _then_snapshot(world, params, match):
    snapshot = world.state["crap"]["project"] / "dump" / ".metrics" / "crap.edn"
    assert snapshot.is_file(), snapshot
    assert "simple" in snapshot.read_text(encoding="utf-8")


def _then_threshold(world, params, match):
    assert _report(world)["threshold"] == 10.0


HANDLERS = [
    step(
        r"^a project with a covered function of complexity 1$",
        _given_covered,
    ),
    step(
        r"^a project with a function of complexity 4 absent from the coverage report$",
        _given_absent,
    ),
    step(
        r"^a project with a covered function and an uncovered function of complexity 4$",
        _given_pair,
    ),
    step(
        r"^a project with an uncovered function in alpha\.py and an uncovered function in beta\.py$",
        _given_alpha_beta,
    ),
    step(r"^the crap tool runs with existing coverage$", _when_existing),
    step(
        r"^the crap tool runs with existing coverage and all rows$",
        _when_existing_all,
    ),
    step(
        r'^the crap tool runs with existing coverage and the filter "([^"]+)"$',
        _when_filtered,
    ),
    step(
        r"^the report lists the function at complexity 1, coverage 100\.0%, and CRAP 1\.0$",
        _then_covered,
    ),
    step(
        r"^the report lists the function at coverage 0\.0% and CRAP 20\.0$",
        _then_absent,
    ),
    step(
        r"^the report counts 1 row above CRAP 10 and returns only that row$",
        _then_above,
    ),
    step(r"^the report returns every function$", _then_all),
    step(r"^the report lists only the alpha function$", _then_filtered),
    step(
        r"^the artifacts hold a crap\.edn snapshot naming the function$",
        _then_snapshot,
    ),
    step(r"^the report states the CRAP threshold 10$", _then_threshold),
]
