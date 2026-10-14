"""Hypothesis properties for ruff4py option supply and the injected prefix."""

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


def _request(tokens, artifacts):
    return CheckRequest(CheckArguments(tuple(tokens)), artifacts)


def _artifacts(directory):
    artifacts = Path(directory) / "artifacts"
    artifacts.mkdir()
    return artifacts


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
def test_invocation_injects_only_the_verb_and_the_cache(tokens):
    with tempfile.TemporaryDirectory() as directory:
        artifacts = _artifacts(directory)
        arguments = CheckArguments(tuple(tokens))
        args = _request(tokens, artifacts).invocation(Path("/bin/ruff")).as_list()
        assert args[0] == "/bin/ruff"
        if tokens:
            assert args[-len(tokens) :] == list(tokens)
        cache = str(artifacts / "ruff-cache")
        injected = args[1 : len(args) - len(tokens)]
        expected = (
            ["check"]
            if arguments.supplies("--cache-dir")
            else ["check", "--cache-dir", cache]
        )
        assert injected == expected
