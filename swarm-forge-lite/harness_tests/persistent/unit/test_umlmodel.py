"""Unit tests for the umlmodel tool.

Covers the ops, the validation, the atomic write, the no-op identity, the
dry-run, and the `swarm.uml` wrapper (`swarm_json.cmd_uml`).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import swarm_json
import umlmodel
from umlmodel import cli, mutate, policy, validate
from umlmodel import model as model_file
from umlmodel.errors import UmlModelError


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


def _write(tmp_path, model, name="model.json"):
    path = tmp_path / name
    path.write_text(model_file.dumps(model), encoding="utf-8")
    return path


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #


def test_the_base_model_has_no_error():
    assert validate.errors(_base()) == []


def test_an_unknown_edge_endpoint_is_an_error():
    model = _base()
    model["edges"].append({"from": "core.A", "to": "core.Ghost", "kind": "dependency"})
    assert "bad-edge" in [item["code"] for item in validate.errors(model)]


def test_a_duplicate_id_is_an_error():
    model = _base()
    model["packages"][0]["classes"].append({"id": "core.A", "name": "A2"})
    assert "dup-id" in [item["code"] for item in validate.errors(model)]


def test_an_id_without_a_dot_is_an_error():
    model = _base()
    model["packages"][0]["classes"].append({"id": "Nodot", "name": "Nodot"})
    assert "bad-id" in [item["code"] for item in validate.errors(model)]


def test_a_bad_direction_stereotype_and_kind_are_errors():
    model = _base()
    model["direction"] = "diagonal"
    model["packages"][0]["classes"][0]["stereotype"] = "thing"
    model["edges"].append({"from": "core.A", "to": "shell.B", "kind": "uses"})
    codes = {item["code"] for item in validate.errors(model)}
    assert {"bad-direction", "bad-stereotype", "bad-kind"} <= codes


def test_a_package_without_a_label_is_an_error():
    model = _base()
    del model["packages"][1]["label"]
    assert "bad-package" in [item["code"] for item in validate.errors(model)]


def test_a_class_under_no_level_is_a_warning_not_an_error():
    model = _base()
    model["packages"].append(
        {
            "id": "tooling",
            "label": "Tooling",
            "classes": [{"id": "tooling.X", "name": "X"}],
        }
    )
    assert validate.errors(model) == []
    assert "unassigned" in [item["code"] for item in validate.warnings(model)]


# --------------------------------------------------------------------------- #
# ops
# --------------------------------------------------------------------------- #


def test_add_class_appends_to_the_named_package():
    model = _base()
    mutate.add_class(
        model, {"id": "core.New", "package": "core", "core": True, "field": ["x : int"]}
    )
    assert "core.New" in validate.class_ids(model)
    assert validate.errors(model) == []
    assert model["packages"][0]["classes"][-1]["annotations"]["core"] is True


def test_remove_class_drops_its_edges():
    model = _base()
    mutate.remove_class(model, {"id": "core.A"})
    assert model["edges"] == []
    assert "core.A" not in validate.class_ids(model)


def test_rename_class_rewrites_edges():
    model = _base()
    mutate.rename_class(model, {"id": "core.A", "new": "core.Renamed"})
    assert model["edges"][0]["to"] == "core.Renamed"
    assert validate.errors(model) == []


def test_add_op_records_the_contract_annotations():
    model = _base()
    mutate.add_op(
        model, {"id": "core.A", "name": "run", "cqs": "command", "post": "done"}
    )
    op = model["packages"][0]["classes"][0]["ops"][0]
    assert op["annotations"] == {"cqs": "command", "post": "done"}


def test_set_annotation_targets_an_op_by_name():
    model = _base()
    mutate.add_op(model, {"id": "core.A", "name": "run"})
    mutate.set_annotation(
        model,
        {"id": "core.A", "op-name": "run", "key": "visibility", "value": "private"},
    )
    op = model["packages"][0]["classes"][0]["ops"][0]
    assert op["annotations"]["visibility"] == "private"


def test_a_missing_class_is_refused():
    with pytest.raises(UmlModelError, match="no such class"):
        mutate.remove_class(_base(), {"id": "core.Ghost"})


def test_an_edge_to_itself_is_refused():
    with pytest.raises(UmlModelError, match="point at itself"):
        mutate.add_edge(_base(), {"from": "core.A", "to": "core.A"})


# --------------------------------------------------------------------------- #
# policy
# --------------------------------------------------------------------------- #


def test_an_inner_to_outer_dependency_is_a_violation():
    model = _base()
    model["edges"].append({"from": "core.A", "to": "shell.B", "kind": "dependency"})
    rows = policy.violations(model)
    assert [(row["from"], row["to"]) for row in rows] == [("core.A", "shell.B")]


def test_the_same_rank_is_permitted():
    model = _base()
    model["packages"][1]["classes"].append({"id": "shell.C", "name": "C"})
    model["edges"] = [{"from": "shell.B", "to": "shell.C", "kind": "dependency"}]
    assert policy.violations(model) == []


def test_an_implements_edge_is_never_a_violation():
    model = _base()
    model["edges"].append({"from": "core.A", "to": "shell.B", "kind": "implements"})
    assert policy.violations(model) == []


# --------------------------------------------------------------------------- #
# the CLI: atomic write, no-op identity, dry run
# --------------------------------------------------------------------------- #


def test_list_names_every_op(capsys):
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    for name in ("classes", "violations", "check", "add-class", "set-direction"):
        assert name in out
    assert len(umlmodel.op_names()) == 35


def test_a_no_op_write_is_byte_identical(tmp_path):
    path = _write(tmp_path, _base())
    before = _digest(path)
    assert cli.main(["set-title", "--model", str(path), "--title", "demo"]) == 0
    assert _digest(path) == before


def test_a_rejected_op_leaves_the_file_byte_identical(tmp_path, capsys):
    path = _write(tmp_path, _base())
    before = _digest(path)
    code = cli.main(
        ["add-edge", "--model", str(path), "--from", "core.A", "--to", "core.Ghost"]
    )
    assert code == 2
    assert "unknown to" in capsys.readouterr().err
    assert _digest(path) == before


def test_dry_run_prints_the_diff_and_writes_nothing(tmp_path, capsys):
    path = _write(tmp_path, _base())
    before = _digest(path)
    assert (
        cli.main(["add-class", "--model", str(path), "--id", "core.New", "--dry-run"])
        == 0
    )
    out = capsys.readouterr().out
    assert "+++ after" in out and "core.New" in out
    assert _digest(path) == before


def test_a_real_write_is_atomic_and_leaves_no_temp_file(tmp_path):
    path = _write(tmp_path, _base())
    assert cli.main(["add-class", "--model", str(path), "--id", "core.New"]) == 0
    assert "core.New" in validate.class_ids(model_file.load(path))
    assert [entry.name for entry in tmp_path.iterdir()] == ["model.json"]


def test_the_json_output_carries_the_result_fields(tmp_path, capsys):
    path = _write(tmp_path, _base())
    assert cli.main(["stats", "--model", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["changed"] is False
    assert payload["classes"] == 2 and payload["exit"] == 0


def test_an_add_then_a_remove_returns_the_bytes(tmp_path):
    path = _write(tmp_path, _base())
    before = _digest(path)
    assert cli.main(["add-class", "--model", str(path), "--id", "core.New"]) == 0
    assert (
        cli.main(
            ["add-edge", "--model", str(path), "--from", "shell.B", "--to", "core.New"]
        )
        == 0
    )
    assert _digest(path) != before
    assert (
        cli.main(
            [
                "remove-edge",
                "--model",
                str(path),
                "--from",
                "shell.B",
                "--to",
                "core.New",
            ]
        )
        == 0
    )
    assert cli.main(["remove-class", "--model", str(path), "--id", "core.New"]) == 0
    assert _digest(path) == before


# --------------------------------------------------------------------------- #
# removal prunes an emptied package
# --------------------------------------------------------------------------- #


def test_remove_class_prunes_a_package_it_emptied():
    model = _base()
    mutate.add_class(model, {"id": "brandnew.Thing", "package": "brandnew"})
    mutate.remove_class(model, {"id": "brandnew.Thing"})
    assert [pkg["id"] for pkg in model["packages"]] == ["core", "shell"]


def test_a_remove_of_a_class_in_a_new_package_is_a_byte_round_trip(tmp_path):
    path = _write(tmp_path, _base())
    before = _digest(path)
    assert (
        cli.main(
            [
                "add-class",
                "--model",
                str(path),
                "--id",
                "brandnew.Thing",
                "--package",
                "brandnew",
            ]
        )
        == 0
    )
    assert (
        cli.main(["remove-class", "--model", str(path), "--id", "brandnew.Thing"]) == 0
    )
    assert _digest(path) == before


def test_a_remove_of_a_class_in_an_existing_package_is_a_byte_round_trip(tmp_path):
    path = _write(tmp_path, _base())
    before = _digest(path)
    assert (
        cli.main(
            [
                "add-class",
                "--model",
                str(path),
                "--id",
                "core.Probe",
                "--package",
                "core",
            ]
        )
        == 0
    )
    assert cli.main(["remove-class", "--model", str(path), "--id", "core.Probe"]) == 0
    assert _digest(path) == before


def test_a_new_package_stays_when_it_still_holds_a_class(tmp_path):
    path = _write(tmp_path, _base())
    for cid in ("brandnew.One", "brandnew.Two"):
        assert (
            cli.main(
                [
                    "add-class",
                    "--model",
                    str(path),
                    "--id",
                    cid,
                    "--package",
                    "brandnew",
                ]
            )
            == 0
        )
    assert cli.main(["remove-class", "--model", str(path), "--id", "brandnew.One"]) == 0
    packages = {
        pkg.get("id"): [cls.get("id") for cls in pkg.get("classes") or []]
        for pkg in model_file.load(path)["packages"]
    }
    assert packages["brandnew"] == ["brandnew.Two"]


# --------------------------------------------------------------------------- #
# style preservation and the check op
# --------------------------------------------------------------------------- #


def _escaped_model():
    """A small model whose title and label carry an em dash, in the real style."""
    model = _base()
    model["title"] = "demo \u2014 the seam"
    model["packages"][0]["label"] = "Core \u2014 the policy"
    return model


def _write_style(tmp_path, model, name, ensure_ascii, indent=2):
    path = tmp_path / name
    text = json.dumps(model, indent=indent, ensure_ascii=ensure_ascii) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def _round_trip(path, anchor="shell.B"):
    assert cli.main(["add-class", "--model", str(path), "--id", "core.Probe"]) == 0
    assert (
        cli.main(
            ["add-edge", "--model", str(path), "--from", anchor, "--to", "core.Probe"]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "remove-edge",
                "--model",
                str(path),
                "--from",
                anchor,
                "--to",
                "core.Probe",
            ]
        )
        == 0
    )
    assert cli.main(["remove-class", "--model", str(path), "--id", "core.Probe"]) == 0


def test_a_no_op_mutate_leaves_an_escaped_file_byte_identical(tmp_path):
    model = _escaped_model()
    path = _write_style(tmp_path, model, "escaped.json", ensure_ascii=True)
    before = _digest(path)
    assert cli.main(["set-title", "--model", str(path), "--title", model["title"]]) == 0
    assert _digest(path) == before


def test_a_round_trip_keeps_the_escaped_style(tmp_path):
    path = _write_style(tmp_path, _escaped_model(), "escaped.json", ensure_ascii=True)
    before = _digest(path)
    _round_trip(path)
    assert _digest(path) == before


def test_a_round_trip_keeps_the_unescaped_style(tmp_path):
    path = _write_style(tmp_path, _escaped_model(), "plain.json", ensure_ascii=False)
    before = _digest(path)
    _round_trip(path)
    assert _digest(path) == before


def test_a_round_trip_keeps_a_one_space_indent(tmp_path):
    path = _write_style(
        tmp_path, _escaped_model(), "one.json", ensure_ascii=True, indent=1
    )
    before = _digest(path)
    _round_trip(path)
    assert _digest(path) == before


def test_a_round_trip_of_a_real_model_is_byte_identical(tmp_path):
    source = Path(swarm_json.PACK) / "design" / "subsystems" / "model-file-registry"
    real = source / "model.json"
    if not real.is_file():
        pytest.skip("no project design record in this pack")
    path = tmp_path / "model.json"
    shutil.copyfile(real, path)
    before = _digest(path)
    _round_trip(path, anchor="shell.DetectorGate")
    assert _digest(path) == before


def test_check_exits_zero_on_a_sound_model(tmp_path, capsys):
    path = _write(tmp_path, _base())
    assert cli.main(["check", "--model", str(path)]) == 0
    assert "0 error" in capsys.readouterr().out


def test_check_exits_non_zero_and_names_a_bad_edge(tmp_path, capsys):
    model = _base()
    model["edges"].append({"from": "core.A", "to": "core.Ghost", "kind": "dependency"})
    path = _write(tmp_path, model)
    assert cli.main(["check", "--model", str(path)]) == 1
    out = capsys.readouterr().out
    assert "bad-edge" in out and "core.Ghost" in out


def test_check_exits_zero_when_only_a_warning_exists(tmp_path, capsys):
    model = _base()
    model["packages"].append(
        {
            "id": "tooling",
            "label": "Tooling",
            "classes": [{"id": "tooling.X", "name": "X"}],
        }
    )
    path = _write(tmp_path, model)
    assert cli.main(["check", "--model", str(path)]) == 0
    out = capsys.readouterr().out
    assert "unassigned" in out and "tooling.X" in out


# --------------------------------------------------------------------------- #
# the swarm.uml wrapper
# --------------------------------------------------------------------------- #


def test_cmd_uml_runs_the_tool_for_a_query(tmp_path):
    path = _write(tmp_path, _base())
    result = swarm_json.cmd_uml({"op": "stats", "model": str(path)})
    assert result["ok"] is True and result["exit"] == 0 and result["classes"] == 2


def test_cmd_uml_returns_the_rejection_with_its_message(tmp_path):
    path = _write(tmp_path, _base())
    result = swarm_json.cmd_uml(
        {"op": "remove-class", "model": str(path), "id": "core.Ghost"}
    )
    assert result["ok"] is False and result["exit"] == 2
    assert "no such class" in result["message"]


def test_cmd_uml_needs_an_op():
    with pytest.raises(swarm_json.SwarmError, match="pass op"):
        swarm_json.cmd_uml({})


def test_the_uml_help_lists_every_op_and_the_invariants():
    tool = swarm_json.cmd_help({"tool": "uml"})
    assert [item["op"] for item in tool["ops"]] == umlmodel.op_names()
    assert tool["invariants"]


def test_a_subsystem_relative_model_resolves_under_the_record(tmp_path, monkeypatch):
    monkeypatch.setattr(swarm_json, "PACK", tmp_path)
    root = tmp_path / "design" / "subsystems" / "clip"
    root.mkdir(parents=True)
    (root / "model.json").write_text("{}", encoding="utf-8")
    resolved = swarm_json._uml_model_path("model.json", "clip")
    assert resolved == root / "model.json"
