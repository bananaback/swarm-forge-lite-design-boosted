"""Unit tests for the ruff4py argument and request helpers."""

from pathlib import Path

import pytest
from ruff4py.errors import InvalidConfiguration, ToolUnavailable
from ruff4py.locator import PathToolLocator
from ruff4py.values import (
    CacheDirectory,
    CheckArguments,
    CheckRequest,
    RuffConfig,
)


def _setup(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    config = pack / "ruff.toml"
    config.write_text("[tool.ruff]\n")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    return pack, artifacts, config


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


def test_invocation_injects_verb_cache_and_config(tmp_path):
    pack, artifacts, config = _setup(tmp_path)
    request = CheckRequest(CheckArguments(("tools",)), pack, artifacts)
    assert request.invocation(Path("/bin/ruff")).as_list() == [
        "/bin/ruff",
        "check",
        "--cache-dir",
        str(artifacts / "ruff-cache"),
        "--config",
        str(config),
        "tools",
    ]


def test_prepare_creates_the_wrapper_cache(tmp_path):
    pack, artifacts, _ = _setup(tmp_path)
    request = CheckRequest(CheckArguments(("tools",)), pack, artifacts)
    request.prepare()
    assert (artifacts / "ruff-cache").is_dir()


def test_a_caller_cache_option_is_not_replaced(tmp_path):
    pack, artifacts, config = _setup(tmp_path)
    request = CheckRequest(
        CheckArguments(("--cache-dir", "caller-cache", "tools")), pack, artifacts
    )
    args = request.invocation(Path("/bin/ruff")).as_list()
    assert args == [
        "/bin/ruff",
        "check",
        "--config",
        str(config),
        "--cache-dir",
        "caller-cache",
        "tools",
    ]
    assert str(artifacts / "ruff-cache") not in args


def test_a_caller_config_option_is_not_replaced(tmp_path):
    pack, artifacts, _ = _setup(tmp_path)
    request = CheckRequest(
        CheckArguments(("--config", "caller.toml", "tools")), pack, artifacts
    )
    args = request.invocation(Path("/bin/ruff")).as_list()
    assert "--config" in args
    assert args[args.index("--config") + 1] == "caller.toml"


def test_the_equals_form_is_not_replaced(tmp_path):
    pack, artifacts, config = _setup(tmp_path)
    request = CheckRequest(
        CheckArguments(("--config=caller.toml", "tools")), pack, artifacts
    )
    args = request.invocation(Path("/bin/ruff")).as_list()
    assert "--config=caller.toml" in args
    assert str(config) not in args


def test_a_config_override_replaces_the_pack_config(tmp_path):
    pack, artifacts, _ = _setup(tmp_path)
    override = tmp_path / "custom.toml"
    override.write_text("[tool.ruff]\n")
    request = CheckRequest(
        CheckArguments(("tools",)), pack, artifacts, config_override=str(override)
    )
    assert request.config().path == override
    assert str(override) in request.invocation(Path("/bin/ruff")).as_list()


def test_the_cache_directory_must_be_absolute():
    with pytest.raises(InvalidConfiguration, match="absolute"):
        CacheDirectory(Path("relative-cache"))


def test_a_missing_ruff_config_is_refused(tmp_path):
    with pytest.raises(InvalidConfiguration, match="ruff config not found"):
        RuffConfig(tmp_path / "missing.toml")


def test_the_locator_refuses_a_missing_tool():
    with pytest.raises(ToolUnavailable, match="not installed"):
        PathToolLocator(which=lambda name: None).locate()


def test_the_locator_returns_the_found_executable():
    locator = PathToolLocator(which=lambda name: "/usr/bin/ruff")
    assert locator.locate() == Path("/usr/bin/ruff")
