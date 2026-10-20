"""Self-test for the diagram port. Run: python3 tools/umlview/selftest.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edn import loads
from model import (
    Edge, Model, Node, combined_grade, crap_grade, mutation_grade,
    mutation_ratio, summarize, validate_model,
)
from policy import validate


def _model(edges: list[Edge], ids: list[str]) -> Model:
    return Model(
        title="t",
        prefix="p",
        nodes=[Node(id=value, ns=f"p.{value}", name=value.split(".")[-1]) for value in ids],
        edges=edges,
    )


def check_edn() -> None:
    value = loads('{:entries [{:name "f", :cc 3, :cov nil,}]}')
    entry = value["entries"][0]
    assert entry["name"] == "f", entry
    assert entry["cc"] == 3, entry
    assert entry["cov"] is None, entry


def check_dependency_rule() -> None:
    levels = [["inner"], ["outer"]]
    edges = [
        Edge(src="inner.a", dst="outer.b"),
        Edge(src="outer.b", dst="inner.a"),
        Edge(src="inner.a", dst="inner.c"),
        Edge(src="inner.a", dst="outer.b", kind="association"),
    ]
    model = _model(edges, ["inner.a", "inner.c", "outer.b"])
    violations = validate(model.nodes, model.edges, levels)
    assert [edge.src for edge in violations] == ["inner.a"], violations
    assert edges[1].violating is False
    assert edges[2].violating is False
    assert edges[3].violating is False


def check_unranked_is_not_compared() -> None:
    edges = [Edge(src="loose.a", dst="outer.b")]
    model = _model(edges, ["loose.a", "outer.b"])
    assert validate(model.nodes, model.edges, [["outer"]]) == []


def check_omitted_prefix() -> None:
    from policy import omitted

    assert omitted("audio.gate.alert", ["audio"]) is True
    assert omitted("audio", ["audio"]) is True
    assert omitted("audio_x", ["audio"]) is False


def check_model_errors() -> None:
    model = Model(title="t", prefix="", nodes=[
        Node(id="a", ns="a", name="a", coverage=93.0),
        Node(id="a", ns="a", name="a"),
    ], edges=[Edge(src="a", dst="missing")])
    errors = validate_model(model)
    assert any("duplicate class id" in error for error in errors), errors
    assert any("coverage out of range" in error for error in errors), errors
    assert any("unknown class missing" in error for error in errors), errors


def check_grade() -> None:
    # Cutoffs and scale copied from uml-viewer.domain.config.
    assert crap_grade(None) == 1
    assert crap_grade(8) == 10
    assert crap_grade(12) == 5.5
    assert crap_grade(20) == 1
    assert crap_grade(16) == 3.25
    summary = summarize([1, 10, 1])
    assert (summary.n, summary.mu, summary.sigma, summary.max) == (3, 4.0, 4.2, 10.0), summary


def check_ir_load() -> None:
    import json
    import tempfile
    from ir import load

    payload = {
        "title": "Lending library",
        "packages": [
            {
                "id": "domain",
                "label": "Domain",
                "classes": [{"id": "book", "name": "Book", "crap": 3}],
            }
        ],
        "edges": [{"from": "book", "to": "book", "kind": "association"}],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(payload, handle)
        path = Path(handle.name)
    try:
        model = load(path)
    finally:
        path.unlink()
    assert model.mode == "packages", model.mode
    assert model.packages[0].classes[0].id == "book"
    assert model.packages[0].classes[0].crap == 3.0


def check_packaged() -> None:
    from packaged import build
    from policy import Policy

    nodes = [
        Node(id="a.one", ns="", name="one"),
        Node(id="b.two", ns="", name="two"),
    ]
    foreign = [Node(id="cv2", ns="cv2", name="cv2", foreign=True)]
    edges = [Edge(src="a.one", dst="b.two"), Edge(src="a.one", dst="cv2")]
    model = Model(title="t", prefix="", nodes=nodes, edges=edges, foreign_classes=foreign)
    policy = Policy(
        title="P",
        packages=[
            {"id": "a", "label": "A", "nses": ["a.one"]},
            {"id": "b", "label": "B", "nses": ["b.two"]},
        ],
        diagrams=[
            {"title": "Overview", "view": "overview"},
            {"title": "A", "package": "a"},
        ],
    )
    document = build(policy, model)
    assert len(document.diagrams) == 2, document.diagrams
    overview = document.diagrams[0]
    assert [package.label for package in overview.packages] == ["A", "B"]
    assert [node.id for node in overview.foreign_classes] == ["cv2"]
    single = document.diagrams[1]
    assert [node.id for node in single.packages[0].classes] == ["a.one", "b.two"]


def check_mutation() -> None:
    node = Node(id="a", ns="a", name="a", killed=3, survived=1)
    assert abs(mutation_ratio(node) - 0.75) < 1e-9
    assert mutation_grade(0.75) == 1.0
    assert abs(mutation_grade(0.85) - 3.25) < 1e-9
    assert mutation_grade(1.0) == 10.0
    assert combined_grade(10.0, 1.0) == 5.5


def check_omit_edges() -> None:
    import json
    import tempfile
    from policy import Policy

    payload = {"title": "t", "omit_edges": [["a.b", "c.d"]]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(payload, handle)
        path = Path(handle.name)
    try:
        policy = Policy.read(path)
    finally:
        path.unlink()
    assert policy.omit_edges == [["a.b", "c.d"]], policy.omit_edges


def main() -> int:
    for check in (
        check_edn,
        check_dependency_rule,
        check_unranked_is_not_compared,
        check_omitted_prefix,
        check_model_errors,
        check_ir_load,
        check_packaged,
        check_mutation,
        check_omit_edges,
        check_grade,
    ):
        check()
        print(f"ok {check.__name__}")
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
