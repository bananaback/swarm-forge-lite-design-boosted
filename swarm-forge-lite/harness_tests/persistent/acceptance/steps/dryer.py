"""Step handlers for the dryer feature.

The handlers drive the pack's own `dry` tool (`swarm_json.py dry`) against a
temporary project. The tool runs the vendored dryer over the project's source
files, so the scenarios exercise the real structural matcher.
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

# Two functions with the same normalized shape: the locals differ, so the pair
# scores 1.0.
ARITHMETIC = (
    "def alpha(items):\n"
    "    total = 0\n"
    "    for item in items:\n"
    "        total = total + item\n"
    "    return total\n"
)

MIRROR = (
    "def beta(values):\n"
    "    result = 0\n"
    "    for value in values:\n"
    "        result = result + value\n"
    "    return result\n"
)

# The same size as ARITHMETIC but a different shape, so the pair scores 0.54.
BRANCHING = (
    "def beta2(values):\n"
    "    result = 0\n"
    "    for value in values:\n"
    "        if value:\n"
    "            result = result + value\n"
    "        else:\n"
    "            result = result - value\n"
    "    return result\n"
)

DUPLICATE = [("alpha.py", ARITHMETIC), ("beta.py", MIRROR)]
NEAR = [("alpha.py", ARITHMETIC), ("second.py", BRANCHING)]


def _state(world):
    return world.state["dry"]


def _project(world, files):
    project = temp_project(world)
    source = project / "src"
    for name, body in files:
        write_text(source / name, body)
    config = write_config(
        project,
        {
            "workspace_root": ".",
            "artifacts_root": "dump",
            "hot_tests": "hot_tests",
            "source_roots": ["src"],
        },
    )
    env = dict(world.state["env"])
    env["SWARM_CONFIG"] = str(config)
    world.state["dry"] = {"project": project, "env": env}


def _given_duplicate(world, params, match):
    _project(world, DUPLICATE)


def _given_near(world, params, match):
    _project(world, NEAR)


def _run(world, args):
    state = _state(world)
    process = run_tool(
        SWARM_JSON, ["dry", json.dumps(args)], state["env"], cwd=state["project"]
    )
    state["process"] = process
    state["report"] = json.loads(process.stdout)


def _report(world):
    return _state(world)["report"]


def _pairs(world):
    return _report(world)["pairs"]


def _when_source(world, params, match):
    _run(world, {"view": "rows"})


def _when_min_lines(world, params, match):
    _run(world, {"view": "rows", "minLines": int(match.group(1))})


def _when_threshold(world, params, match):
    _run(world, {"view": "rows", "threshold": float(match.group(1))})


def _then_none(world, params, match):
    report = _report(world)
    assert report["exit"] == 0, report
    assert report["total"] == 0, report
    assert _pairs(world) == [], report


def _then_one(world, params, match):
    report = _report(world)
    assert report["exit"] == 0, report
    assert report["total"] == 1, report


def _then_names(world, params, match):
    pairs = _pairs(world)
    assert len(pairs) == 1, pairs
    joined = " ".join(pairs[0])
    assert "alpha.py:" in joined and "beta.py:" in joined, pairs


def _then_positions(world, params, match):
    pairs = _pairs(world)
    assert len(pairs) == 1, pairs
    first, second = sorted(pairs[0])
    assert first.endswith("alpha.py:1-5"), pairs
    assert second.endswith("beta.py:1-5"), pairs


def _then_snapshot(world, params, match):
    snapshot = _state(world)["project"] / "dump" / ".metrics" / "dry.edn"
    assert snapshot.is_file(), snapshot
    assert '"python"' in snapshot.read_text(encoding="utf-8")


def _then_no_source_metrics(world, params, match):
    assert not (_state(world)["project"] / "src" / ".metrics").exists()


HANDLERS = [
    step(
        r"^a project with a duplicated function in alpha\.py and beta\.py$",
        _given_duplicate,
    ),
    step(
        r"^a project whose source holds two functions below the similarity threshold$",
        _given_near,
    ),
    step(r"^the dry tool runs over the source$", _when_source),
    step(
        r"^the dry tool runs over the source with minimum lines (\d+)$",
        _when_min_lines,
    ),
    step(
        r"^the dry tool runs over the source with similarity threshold ([\d.]+)$",
        _when_threshold,
    ),
    step(r"^the dry report counts 0 pairs$", _then_none),
    step(r"^the dry report counts 1 pair$", _then_one),
    step(r"^the dry report names alpha\.py and beta\.py$", _then_names),
    step(
        r"^the dry report lists a pair from alpha\.py lines 1-5 to beta\.py lines 1-5$",
        _then_positions,
    ),
    step(
        r"^the artifacts hold a dry\.edn snapshot naming python$",
        _then_snapshot,
    ),
    step(
        r"^the source directory holds no \.metrics directory$",
        _then_no_source_metrics,
    ),
]
