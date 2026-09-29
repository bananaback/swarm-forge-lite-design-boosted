"""Hypothesis properties for ruff4py option supply and config resolution."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from ruff4py.values import CheckArguments, CheckRequest

OPTIONS = st.sampled_from(["--cache-dir", "--config"])
OPTION_TOKENS = st.sampled_from(
    ["--cache-dir", "--cache-dir=x", "--config", "--config=x", "check", "tools"]
)
TOKENS = st.lists(
    st.one_of(OPTION_TOKENS, st.text(alphabet="abcofig-_.=", min_size=1, max_size=8)),
    max_size=8,
)


def _request(tokens, pack, artifacts, override=None):
    return CheckRequest(CheckArguments(tuple(tokens)), pack, artifacts, override)


def _workspace(directory):
    pack = Path(directory) / "pack"
    pack.mkdir()
    (pack / "ruff.toml").write_text("[tool.ruff]\n")
    artifacts = Path(directory) / "artifacts"
    artifacts.mkdir()
    return pack, artifacts


@settings(max_examples=100, deadline=None)
@given(option=OPTIONS, tokens=TOKENS)
def test_supplies_matches_token_presence(option, tokens):
    arguments = CheckArguments(tuple(tokens))
    expected = any(
        token == option or token.startswith(option + "=") for token in tokens
    )
    assert arguments.supplies(option) == expected


@settings(max_examples=100, deadline=None)
@given(tokens=TOKENS)
def test_as_list_preserves_the_argument_order(tokens):
    assert CheckArguments(tuple(tokens)).as_list() == list(tokens)


@settings(max_examples=100, deadline=None)
@given(tokens=TOKENS)
def test_invocation_injects_options_only_when_absent(tokens):
    with tempfile.TemporaryDirectory() as directory:
        pack, artifacts = _workspace(directory)
        arguments = CheckArguments(tuple(tokens))
        args = _request(tokens, pack, artifacts).invocation(Path("/bin/ruff")).as_list()
        assert args[0] == "/bin/ruff"
        assert args[1] == "check"
        if tokens:
            assert args[-len(tokens):] == list(tokens)
        cache = str(artifacts / "ruff-cache")
        config = str(pack / "ruff.toml")
        assert (cache in args) == (not arguments.supplies("--cache-dir"))
        assert (config in args) == (not arguments.supplies("--config"))


@settings(max_examples=50, deadline=None)
@given(name=st.text(alphabet="abc_", min_size=1, max_size=8))
def test_config_override_replaces_the_pack_config(name):
    with tempfile.TemporaryDirectory() as directory:
        pack, artifacts = _workspace(directory)
        override = Path(directory) / f"{name}.toml"
        override.write_text("[tool.ruff]\n")
        request = _request(("tools",), pack, artifacts, override=str(override))
        assert request.config().path == override
        assert str(override) in request.invocation(Path("/bin/ruff")).as_list()


@settings(max_examples=50, deadline=None)
@given(name=st.text(alphabet="abc_", min_size=1, max_size=8))
def test_config_defaults_to_the_pack_ruff_toml(name):
    with tempfile.TemporaryDirectory() as directory:
        pack = Path(directory) / name
        pack.mkdir()
        config = pack / "ruff.toml"
        config.write_text("[tool.ruff]\n")
        artifacts = Path(directory) / "artifacts"
        artifacts.mkdir()
        request = _request(("tools",), pack, artifacts)
        assert request.config().path == config
