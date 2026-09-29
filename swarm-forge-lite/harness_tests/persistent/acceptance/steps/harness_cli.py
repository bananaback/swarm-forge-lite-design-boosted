"""Step handlers for the Harness CLI feature."""

import json
from pathlib import Path

from .support import (
    HARNESS,
    run_tool,
    step,
    temp_project,
    write_config,
    write_text,
)

BASE_FIELDS = {
    "workspace_root": ".",
    "state_root": ".swarmforge",
    "artifacts_root": "dump",
    "hot_tests": "hot_tests",
    "persistent_tests": [{"root": "unit", "kind": "harness"}],
    "source_roots": ["src"],
    "features": "features",
}

BASE_PRESENT = [".swarmforge", "dump", "hot_tests", "src", "unit", "features"]

AREA_FIELDS = {"hot": "hot_tests", "artifacts": "dump", "state": ".swarmforge"}


def _state(world):
    return world.state["cli"]


def _build(world, fields, present):
    project = temp_project(world)
    for relative in present:
        (project / relative).mkdir(parents=True, exist_ok=True)
    config = write_config(project, fields)
    world.state["cli"] = {
        "project": project,
        "config": config,
        "env": dict(world.state["env"]),
        "areas": {name: project / value for name, value in AREA_FIELDS.items()},
    }


def _given_configured(world, params, match):
    _build(world, BASE_FIELDS, BASE_PRESENT)


def _given_absent_roots(world, params, match):
    fields = {
        **BASE_FIELDS,
        "workspace_root": "missing-workspace",
        "state_root": "missing-state",
        "artifacts_root": "missing-artifacts",
        "hot_tests": "missing-hot",
        "features": "missing-features",
    }
    _build(world, fields, ["src", "unit"])


def _given_all_roots(world, params, match):
    _build(world, BASE_FIELDS, BASE_PRESENT)


def _given_hot_absent(world, params, match):
    _build(world, {**BASE_FIELDS, "hot_tests": "missing-hot"}, BASE_PRESENT)


def _given_missing_config(world, params, match):
    project = temp_project(world)
    world.state["cli"] = {
        "project": project,
        "config": project / "missing.json",
        "env": dict(world.state["env"]),
        "areas": {name: project / value for name, value in AREA_FIELDS.items()},
    }


def _given_no_features(world, params, match):
    fields = {key: value for key, value in BASE_FIELDS.items() if key != "features"}
    _build(world, fields, BASE_PRESENT)


def _given_two_sources(world, params, match):
    _build(world, {**BASE_FIELDS, "source_roots": ["src", "lib"]}, BASE_PRESENT + ["lib"])


def _given_counted_files(world, params, match):
    _build(world, BASE_FIELDS, BASE_PRESENT)
    count = int(params["count"])
    for index in range(count):
        write_text(_state(world)["areas"]["hot"] / f"generated-{index}.txt", "x\n")


def _given_area_file(world, params, match):
    area = params.get("area") or match.group(1)
    write_text(_state(world)["areas"][area] / "generated.txt", "x\n")


def _given_each_file(world, params, match):
    for path in _state(world)["areas"].values():
        write_text(path / "generated.txt", "x\n")


def _run(world, args):
    state = _state(world)
    state["result"] = run_tool(HARNESS, args, state["env"], cwd=state["project"])


def _config_args(world, command):
    return ["--config", _state(world)["config"], command]


def _when_config(world, params, match):
    _run(world, _config_args(world, "config"))


def _when_status(world, params, match):
    _run(world, _config_args(world, "status"))


def _when_status_missing(world, params, match):
    _run(world, _config_args(world, "status"))


def _when_config_missing(world, params, match):
    _run(world, _config_args(world, "config"))


def _when_clean_area(world, params, match):
    area = params.get("area") or match.group(1)
    _run(world, _config_args(world, "clean") + [area])


def _when_clean_all(world, params, match):
    _run(world, _config_args(world, "clean") + ["all"])


def _when_clean_default(world, params, match):
    _run(world, _config_args(world, "clean"))


def _when_clean_unknown(world, params, match):
    _run(world, _config_args(world, "clean") + [match.group(1)])


def _when_clean_hot(world, params, match):
    _run(world, _config_args(world, "clean") + ["hot"])


def _when_clean_missing(world, params, match):
    _run(world, _config_args(world, "clean") + ["hot"])


def _result(world):
    return _state(world)["result"]


def _output(world):
    result = _result(world)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    return result.stdout


def _then_field(world, params, match):
    document = json.loads(_output(world))
    assert params["field"] in document, (params["field"], sorted(document))


def _then_roots_inside(world, params, match):
    document = json.loads(_output(world))
    project = _state(world)["project"]
    for key in ("workspace_root", "state_root", "artifacts_root", "hot_tests"):
        assert Path(document[key]).is_relative_to(project), (key, document[key])


def _then_rows(world, params, match):
    lines = _output(world).splitlines()
    for label in (
        "PACK",
        "CONFIG",
        "WORKSPACE",
        "STATE",
        "ARTIFACTS",
        "HOT",
        "FEATURES",
        "SOURCE",
        "PERSIST",
    ):
        assert any(line.startswith(label) for line in lines), (label, lines)


def _then_marker(world, params, match):
    lines = _output(world).splitlines()
    row = next(line for line in lines if line.startswith(params["row"]))
    assert f"[{params['marker']}]" in row, row


def _then_area_empty(world, params, match):
    _output(world)
    area = params.get("area") or match.group(1)
    path = _state(world)["areas"][area]
    assert path.is_dir(), path
    assert list(path.iterdir()) == [], list(path.iterdir())


def _then_untouched(world, params, match):
    _output(world)
    areas = _state(world)["areas"]
    assert (areas["hot"] / "generated.txt").is_file()
    assert (areas["state"] / "generated.txt").is_file()


def _then_removed(world, params, match):
    output = _output(world)
    count = params.get("count") or match.group(1)
    assert f"({count} entr" in output, output


def _then_unknown(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert match.group(1) in result.stderr, result.stderr


def _then_missing_config(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert str(_state(world)["config"]) in result.stderr, result.stderr


def _then_features_absent(world, params, match):
    lines = _output(world).splitlines()
    row = next(line for line in lines if line.startswith("FEATURES"))
    assert "[-]" in row and "(none)" in row, row


def _then_two_sources(world, params, match):
    lines = _output(world).splitlines()
    sources = [line for line in lines if line.startswith("SOURCE")]
    assert len(sources) == 2, sources


HANDLERS = [
    step(
        r"^a temporary project with its own harness config and roots inside it$",
        _given_configured,
    ),
    step(
        r"^a temporary project whose source and persistent roots are present and whose workspace, state, artifacts, hot, and features roots are absent$",
        _given_absent_roots,
    ),
    step(
        r"^a temporary project with all harness roots inside it$",
        _given_all_roots,
    ),
    step(
        r"^a temporary project with all harness roots inside it and the hot directory absent$",
        _given_hot_absent,
    ),
    step(
        r"^a temporary project whose config path is missing$",
        _given_missing_config,
    ),
    step(
        r"^a temporary project with its roots inside it and no features root configured$",
        _given_no_features,
    ),
    step(
        r"^a temporary project with two source roots inside it$",
        _given_two_sources,
    ),
    step(
        r"^a temporary project with (.+) generated files under the hot directory$",
        _given_counted_files,
    ),
    step(
        r"^a generated file under the project (.+) directory$",
        _given_area_file,
    ),
    step(
        r"^a generated file under each of the hot, artifacts, and state directories$",
        _given_each_file,
    ),
    step(r"^the harness config command runs$", _when_config),
    step(r"^the harness status command runs$", _when_status),
    step(
        r"^the harness status command runs with that missing config$",
        _when_status_missing,
    ),
    step(
        r"^the harness config command runs with that missing config$",
        _when_config_missing,
    ),
    step(
        r"^the harness clean command runs for (<area>|hot|artifacts|state)$",
        _when_clean_area,
    ),
    step(
        r"^the harness clean command clears every managed area$",
        _when_clean_all,
    ),
    step(
        r"^the harness clean command runs without a target$",
        _when_clean_default,
    ),
    step(
        r'^the harness clean command runs for the unknown target "([^"]+)"$',
        _when_clean_unknown,
    ),
    step(
        r"^the harness clean command runs against the hot area$",
        _when_clean_hot,
    ),
    step(
        r"^the harness clean command runs with that missing config for the hot area$",
        _when_clean_missing,
    ),
    step(r"^the config output has a (.+) field$", _then_field),
    step(
        r"^the config output places the workspace, state, artifacts, and hot roots inside the project directory$",
        _then_roots_inside,
    ),
    step(
        r"^the status reports a row for each of the pack, config, workspace, state, artifacts, hot, features, source, and persistent roots$",
        _then_rows,
    ),
    step(r'^the status marks the (.+) row as "(.+)"$', _then_marker),
    step(
        r"^the harness command succeeds with the project (.+) directory empty$",
        _then_area_empty,
    ),
    step(
        r"^the hot and state directories still hold their generated files$",
        _then_untouched,
    ),
    step(
        r"^the harness command succeeds reporting the removed entry count as (.+)$",
        _then_removed,
    ),
    step(
        r'^the harness command is refused with exit code 2 and an error naming "([^"]+)"$',
        _then_unknown,
    ),
    step(
        r"^the harness command is refused with exit code 2 and an error naming the missing config$",
        _then_missing_config,
    ),
    step(
        r"^the status reports the FEATURES row as absent$",
        _then_features_absent,
    ),
    step(r"^the status reports two SOURCE rows$", _then_two_sources),
]
