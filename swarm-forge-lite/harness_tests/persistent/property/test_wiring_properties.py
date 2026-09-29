"""Hypothesis properties for wiring pack-root and config resolution."""

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from wiring.config import parse_config
from wiring.locator import PackConfigLocator
from wiring.pack import PACK_ROOT, Pack, resolve_pack_root
from wiring.resolver import PathResolver
from wiring.wiring import Wiring

JSON_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children, max_size=3)
    | st.dictionaries(st.text(min_size=1), children, max_size=3),
    max_leaves=6,
)

RELATIVE_NAMES = st.text(alphabet="abc_.", min_size=1, max_size=10)
PLAIN_NAMES = st.text(alphabet="abc_", min_size=1, max_size=8)


@settings(max_examples=50, deadline=None)
@given(document=st.dictionaries(st.text(min_size=1), JSON_VALUES, max_size=6))
def test_parse_config_round_trips_a_json_object(document):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "harness.json"
        path.write_text(json.dumps(document))
        assert parse_config(path) == document


@settings(max_examples=100, deadline=None)
@given(name=RELATIVE_NAMES)
def test_relative_paths_anchor_at_the_config_directory(name):
    base = Path("/base")
    assert PathResolver(base).path(name) == (base / Path(name)).resolve()


@settings(max_examples=100, deadline=None)
@given(name=PLAIN_NAMES)
def test_absolute_paths_resolve_unchanged(name):
    absolute = "/" + name
    assert PathResolver(Path("/base")).path(absolute) == Path(absolute).resolve()


@settings(max_examples=50, deadline=None)
@given(name=PLAIN_NAMES)
def test_swarm_pack_environment_wins(name):
    chosen = str(Path("/packs") / name)
    assert resolve_pack_root({"SWARM_PACK": chosen}) == Path(chosen).resolve()


def test_pack_root_defaults_to_the_installed_pack():
    assert resolve_pack_root({}) == PACK_ROOT


@settings(max_examples=50, deadline=None)
@given(name=PLAIN_NAMES)
def test_explicit_config_wins_over_the_environment(name):
    chosen = "/explicit/" + name
    locator = PackConfigLocator(
        Pack(Path("/pack")), override=chosen, environ={"SWARM_CONFIG": "/env.json"}
    )
    assert locator.locate() == Path(chosen).expanduser().resolve()


def test_environment_config_wins_over_the_pack_config():
    locator = PackConfigLocator(Pack(Path("/pack")), environ={"SWARM_CONFIG": "/env.json"})
    assert locator.locate() == Path("/env.json").resolve()


def test_pack_config_is_the_default():
    locator = PackConfigLocator(Pack(Path("/pack")), environ={})
    assert locator.locate() == Path("/pack/harness.json")


@settings(max_examples=50, deadline=None)
@given(name=PLAIN_NAMES)
def test_as_dict_renders_every_path_as_text(name):
    root = Path("/") / name
    resolved = Wiring(
        pack_root=root,
        workspace_root=root / "work",
        state_root=root / "state",
        artifacts_root=root / "artifacts",
        hot_tests=root / "hot",
        persistent_tests=({"root": root / "tests", "kind": "harness"},),
        source_roots=(root / "src",),
        features=None,
        specs=None,
        config_path=root / "harness.json",
    )
    document = resolved.as_dict()
    assert set(document) == {
        "pack_root",
        "workspace_root",
        "state_root",
        "artifacts_root",
        "hot_tests",
        "persistent_tests",
        "source_roots",
        "features",
        "specs",
        "config_path",
    }
    assert document["pack_root"] == str(root)
    assert document["features"] is None
    assert document["specs"] is None
    assert document["source_roots"] == [str(root / "src")]
    assert document["persistent_tests"] == [
        {"root": str(root / "tests"), "kind": "harness"}
    ]
