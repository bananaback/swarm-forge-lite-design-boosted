"""Unit tests for the ruff4py argument and request helpers."""

from pathlib import Path

import pytest
from ruff4py.errors import InvalidConfiguration, ToolUnavailable
from ruff4py.locator import PathToolLocator
from ruff4py.values import (
    CacheDirectory,
    CheckArguments,
    CheckRequest,
)


def _artifacts(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    return artifacts


def test_arguments_recognize_help_and_the_check_verb():
    assert CheckArguments(("--help",)).requests_help()
    assert CheckArguments(("-h",)).requests_help()
    assert not CheckArguments(("tools",)).requests_help()
    assert CheckArguments(("check", "src")).mentions_verb()
    assert not CheckArguments(("src",)).mentions_verb()


def test_arguments_supply_an_option_in_both_forms():
    assert CheckArguments(("--config", "x")).supplies("--config")
    assert CheckArguments(("--config=x",)).supplies("--config")
    assert not CheckArguments(("src",)).supplies("--config")


def test_invocation_injects_the_verb_and_the_cache(tmp_path):
    artifacts = _artifacts(tmp_path)
    request = CheckRequest(CheckArguments(("tools",)), artifacts)
    assert request.invocation(Path("/bin/ruff")).as_list() == [
        "/bin/ruff",
        "check",
        "--cache-dir",
        str(artifacts / "ruff-cache"),
        "tools",
    ]


def test_invocation_never_injects_a_config(tmp_path):
    artifacts = _artifacts(tmp_path)
    request = CheckRequest(CheckArguments(("tools",)), artifacts)
    assert "--config" not in request.invocation(Path("/bin/ruff")).as_list()


def test_prepare_creates_the_wrapper_cache(tmp_path):
    artifacts = _artifacts(tmp_path)
    request = CheckRequest(CheckArguments(("tools",)), artifacts)
    request.prepare()
    assert (artifacts / "ruff-cache").is_dir()


def test_a_caller_cache_option_is_not_replaced(tmp_path):
    artifacts = _artifacts(tmp_path)
    request = CheckRequest(
        CheckArguments(("--cache-dir", "caller-cache", "tools")), artifacts
    )
    args = request.invocation(Path("/bin/ruff")).as_list()
    assert args == [
        "/bin/ruff",
        "check",
        "--cache-dir",
        "caller-cache",
        "tools",
    ]
    assert str(artifacts / "ruff-cache") not in args


def test_a_caller_config_option_passes_through(tmp_path):
    artifacts = _artifacts(tmp_path)
    request = CheckRequest(
        CheckArguments(("--config", "caller.toml", "tools")), artifacts
    )
    args = request.invocation(Path("/bin/ruff")).as_list()
    assert args == [
        "/bin/ruff",
        "check",
        "--cache-dir",
        str(artifacts / "ruff-cache"),
        "--config",
        "caller.toml",
        "tools",
    ]


def test_the_caller_config_in_equals_form_passes_through(tmp_path):
    artifacts = _artifacts(tmp_path)
    request = CheckRequest(CheckArguments(("--config=caller.toml", "tools")), artifacts)
    args = request.invocation(Path("/bin/ruff")).as_list()
    assert "--config=caller.toml" in args


def test_the_cache_directory_must_be_absolute():
    with pytest.raises(InvalidConfiguration, match="absolute"):
        CacheDirectory(Path("relative-cache"))


def test_the_locator_refuses_a_missing_tool():
    with pytest.raises(ToolUnavailable, match="not installed"):
        PathToolLocator(which=lambda name: None).locate()


def test_the_locator_returns_the_found_executable():
    locator = PathToolLocator(which=lambda name: "/usr/bin/ruff")
    assert locator.locate() == Path("/usr/bin/ruff")
