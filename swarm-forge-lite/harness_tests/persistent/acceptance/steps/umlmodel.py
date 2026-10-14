"""Step handlers for the umlmodel feature.

The handlers drive the pack's own `umlmodel` tool against a temporary model
file. That exercises the real load / validate / apply / write pipeline.
"""

import json

from .support import PACK_ROOT, run_tool, step, temp_project, write_text

UMLMODEL = PACK_ROOT / "tools" / "shared" / "umlmodel"


def _base():
    return {
        "title": "demo",
        "direction": "tb",
        "levels": [["core"], ["shell"]],
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {"id": "core.A", "name": "A", "stereotype": "class", "ops": []}
                ],
            },
            {
                "id": "shell",
                "label": "Shell",
                "classes": [
                    {"id": "shell.B", "name": "B", "stereotype": "class", "ops": []}
                ],
            },
        ],
        "edges": [{"from": "shell.B", "to": "core.A", "kind": "dependency"}],
    }


def _state(world):
    return world.state.setdefault("uml", {})


def _write_model(world, model):
    project = temp_project(world)
    path = project / "model.json"
    write_text(path, json.dumps(model, indent=2) + "\n")
    state = _state(world)
    state["path"] = path
    state["before"] = path.read_text(encoding="utf-8")


def _model_arg(world):
    return ["--model", str(_state(world)["path"])]


def _run(world, args):
    state = _state(world)
    path = state.get("path")
    state["result"] = run_tool(
        UMLMODEL,
        args,
        dict(world.state.get("env") or {}),
        cwd=path.parent if path else None,
    )


def _read(world):
    return json.loads(_state(world)["path"].read_text(encoding="utf-8"))


def _output(world):
    result = _state(world)["result"]
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    return result.stdout


def _class_ids(world):
    return [cls["id"] for pkg in _read(world)["packages"] for cls in pkg["classes"]]


def _edges(world):
    return [(edge["from"], edge["to"]) for edge in _read(world)["edges"]]


# --------------------------------------------------------------------------- #
# given
# --------------------------------------------------------------------------- #


def _given_valid(world, params, match):
    _write_model(world, _base())


def _given_inner_to_outer(world, params, match):
    model = _base()
    model["edges"].append({"from": "core.A", "to": "shell.B", "kind": "dependency"})
    _write_model(world, model)


def _given_unassigned(world, params, match):
    model = _base()
    model["packages"].append(
        {
            "id": "tooling",
            "label": "Tooling",
            "classes": [{"id": "tooling.X", "name": "X"}],
        }
    )
    _write_model(world, model)


def _given_bad_edge(world, params, match):
    model = _base()
    model["edges"].append({"from": "core.A", "to": "core.Ghost", "kind": "dependency"})
    _write_model(world, model)


# --------------------------------------------------------------------------- #
# when
# --------------------------------------------------------------------------- #


def _when_list(world, params, match):
    _run(world, ["list"])


def _when_stats(world, params, match):
    _run(world, ["stats", *_model_arg(world)])


def _when_violations(world, params, match):
    _run(world, ["violations", *_model_arg(world)])


def _when_unassigned(world, params, match):
    _run(world, ["unassigned", *_model_arg(world)])


def _when_check(world, params, match):
    _run(world, ["check", *_model_arg(world)])


def _when_add_new_package(world, params, match):
    _run(
        world,
        [
            "add-class",
            *_model_arg(world),
            "--id",
            "brandnew.Thing",
            "--name",
            "Thing",
            "--package",
            "brandnew",
        ],
    )


def _when_remove_thing(world, params, match):
    _run(world, ["remove-class", *_model_arg(world), "--id", "brandnew.Thing"])


def _when_add_class(world, params, match):
    _run(
        world,
        ["add-class", *_model_arg(world), "--id", "core.New", "--package", "core"],
    )


def _when_add_class_dry(world, params, match):
    _run(
        world,
        [
            "add-class",
            *_model_arg(world),
            "--id",
            "core.New",
            "--package",
            "core",
            "--dry-run",
        ],
    )


def _when_add_edge(world, params, match):
    _run(
        world,
        [
            "add-edge",
            *_model_arg(world),
            "--from",
            "shell.B",
            "--to",
            "core.New",
            "--kind",
            "dependency",
        ],
    )


def _when_remove_round_trip(world, params, match):
    _run(
        world,
        ["remove-edge", *_model_arg(world), "--from", "shell.B", "--to", "core.New"],
    )
    _run(world, ["remove-class", *_model_arg(world), "--id", "core.New"])


def _when_bad_edge(world, params, match):
    _run(
        world,
        ["add-edge", *_model_arg(world), "--from", "core.A", "--to", "core.Ghost"],
    )


def _when_rename(world, params, match):
    _run(
        world,
        ["rename-class", *_model_arg(world), "--id", "core.A", "--new", "core.Renamed"],
    )


# --------------------------------------------------------------------------- #
# then
# --------------------------------------------------------------------------- #


def _then_list(world, params, match):
    out = _output(world)
    assert "classes" in out and "add-class" in out


def _then_stats(world, params, match):
    out = _output(world)
    row = next(line for line in out.splitlines() if line.startswith("classes"))
    assert row.split()[-1] == match.group(1), row


def _then_class_present(world, params, match):
    _output(world)
    assert match.group(1) in _class_ids(world)


def _then_edge_present(world, params, match):
    _output(world)
    assert (match.group(1), match.group(2)) in _edges(world)


def _then_changed(world, params, match):
    _output(world)
    assert _state(world)["path"].read_text(encoding="utf-8") != _state(world)["before"]


def _then_identical(world, params, match):
    assert _state(world)["path"].read_text(encoding="utf-8") == _state(world)["before"]


def _then_refused(world, params, match):
    result = _state(world)["result"]
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert match.group(1) in result.stderr + result.stdout


def _then_violation(world, params, match):
    out = _output(world)
    assert match.group(1) in out and match.group(2) in out, out


def _then_unassigned(world, params, match):
    out = _output(world)
    assert match.group(1) in out, out


def _then_check_code(world, params, match):
    result = _state(world)["result"]
    assert result.returncode == int(match.group(1)), (
        result.returncode,
        result.stdout,
        result.stderr,
    )


def _then_check_names(world, params, match):
    result = _state(world)["result"]
    assert match.group(1) in result.stdout + result.stderr, result.stdout


def _then_package_absent(world, params, match):
    ids = [pkg["id"] for pkg in _read(world)["packages"]]
    assert match.group(1) not in ids, ids


HANDLERS = [
    step(r"^a copy of a valid model$", _given_valid),
    step(
        r"^a copy of a valid model with an extra inner-to-outer dependency$",
        _given_inner_to_outer,
    ),
    step(r"^a copy of a valid model with an unassigned class$", _given_unassigned),
    step(r"^a copy of a valid model with a bad edge$", _given_bad_edge),
    step(r"^the uml tool runs the list op$", _when_list),
    step(r"^the uml tool runs the stats op$", _when_stats),
    step(r"^the uml tool runs the violations op$", _when_violations),
    step(r"^the uml tool runs the unassigned op$", _when_unassigned),
    step(r"^the uml tool runs the check op$", _when_check),
    step(
        r"^the uml tool adds a class brandnew\.Thing in the package brandnew$",
        _when_add_new_package,
    ),
    step(r"^the uml tool removes the class brandnew\.Thing$", _when_remove_thing),
    step(r"^the uml tool adds a class core\.New to core$", _when_add_class),
    step(
        r"^the uml tool adds a class core\.New to core without writing$",
        _when_add_class_dry,
    ),
    step(r"^the uml tool adds an edge from shell\.B to core\.New$", _when_add_edge),
    step(r"^the uml tool removes that class and its edge$", _when_remove_round_trip),
    step(
        r"^the uml tool tries to add an edge from core\.A to core\.Ghost$",
        _when_bad_edge,
    ),
    step(r"^the uml tool renames core\.A to core\.Renamed$", _when_rename),
    step(r"^the op list names classes and add-class$", _then_list),
    step(r"^the stats report counts (\d+) classes$", _then_stats),
    step(r"^the model holds a class ([A-Za-z0-9_.-]+)$", _then_class_present),
    step(
        r"^the model holds the edge ([A-Za-z0-9_.-]+) to ([A-Za-z0-9_.-]+)$",
        _then_edge_present,
    ),
    step(r"^the model file differs from the copy at the start$", _then_changed),
    step(
        r"^the model file is byte-identical to the copy at the start$", _then_identical
    ),
    step(
        r"^the run is refused with exit code 2 and an error naming (.+)$",
        _then_refused,
    ),
    step(
        r"^the violations report names ([A-Za-z0-9_.-]+) to ([A-Za-z0-9_.-]+)$",
        _then_violation,
    ),
    step(r"^the unassigned report names ([A-Za-z0-9_.-]+)$", _then_unassigned),
    step(r"^the check report exits with code (\d+)$", _then_check_code),
    step(r"^the check report names ([A-Za-z0-9_.-]+)$", _then_check_names),
    step(r"^the model holds no package ([A-Za-z0-9_.-]+)$", _then_package_absent),
]
