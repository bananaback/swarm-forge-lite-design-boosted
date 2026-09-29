"""Step handlers for the ruff4py feature."""

from .support import (
    PACK_ROOT,
    RUFF4PY,
    clean_env,
    install_fake_ruff,
    install_unrunnable_ruff,
    last_invocation,
    prepend_path,
    recorded_invocations,
    run_tool,
    step,
    temp_project,
    write_config,
    write_text,
)


def _state(world):
    return world.state["ruff"]


def _given_project(world, params, match):
    project = temp_project(world)
    artifacts = project / "dump"
    artifacts.mkdir(parents=True, exist_ok=True)
    config = write_config(
        project,
        {
            "workspace_root": ".",
            "artifacts_root": "dump",
            "hot_tests": "hot_tests",
            "source_roots": ["tools"],
        },
    )
    write_text(project / "custom.toml", "[tool.ruff]\n")
    bin_dir = project / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    env = clean_env()
    env["SWARM_CONFIG"] = str(config)
    prepend_path(env, bin_dir)
    pack_config = PACK_ROOT / "ruff.toml"
    world.state["ruff"] = {
        "project": project,
        "artifacts": artifacts,
        "config": config,
        "bin": bin_dir,
        "record": project / "ruff-record.jsonl",
        "env": env,
        "entry": RUFF4PY,
        "cache": artifacts / "ruff-cache",
        "pack_config": pack_config,
        "missing_config": str(pack_config),
        "missing_harness": str(project / "missing-harness.json"),
    }


def _given_recording(world, params, match):
    state = _state(world)
    install_fake_ruff(state["bin"])
    state["env"].update({"RUFF_RECORD": str(state["record"]), "RUFF_EXIT": "0"})


def _given_recording_status(world, params, match):
    _given_recording(world, params, match)
    _state(world)["env"]["RUFF_EXIT"] = params["status"]


def _given_unrunnable(world, params, match):
    install_unrunnable_ruff(_state(world)["bin"])


def _given_no_ruff(world, params, match):
    _state(world)["env"]["PATH"] = str(_state(world)["bin"])


def _given_cache_absent(world, params, match):
    cache = _state(world)["cache"]
    if cache.exists():
        for child in cache.iterdir():
            child.unlink()
        cache.rmdir()


def _given_env_config(world, params, match):
    value = match.group(1)
    _state(world)["env"]["RUFF4PY_CONFIG"] = value
    _state(world)["missing_config"] = value


def _given_no_pack_config(world, params, match):
    state = _state(world)
    empty_pack = temp_project(world, "temp-pack")
    state["env"]["SWARM_PACK"] = str(empty_pack)
    state["pack_config"] = empty_pack / "ruff.toml"
    state["missing_config"] = str(state["pack_config"])


def _given_missing_harness(world, params, match):
    state = _state(world)
    state["env"]["SWARM_CONFIG"] = state["missing_harness"]


def _run(world, args):
    state = _state(world)
    state["result"] = run_tool(
        state["entry"], args, state["env"], cwd=state["project"]
    )


def _when_flag(world, params, match):
    _run(world, [params.get("flag") or match.group(1)])


def _when_check_verb(world, params, match):
    _run(world, [match.group(1), match.group(2)])


def _when_option_value(world, params, match):
    _run(world, [params["option"], params["value"], "tools"])


def _when_option_equals(world, params, match):
    _run(world, [match.group(1), match.group(2)])


def _result(world):
    return _state(world)["result"]


def _then_help(world, params, match):
    result = _result(world)
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert "usage:" in result.stdout, result.stdout
    assert recorded_invocations(_state(world)["record"]) == [], "ruff was invoked"


def _then_verb_refused(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "already supplied" in result.stderr, result.stderr


def _then_status(world, params, match):
    assert _result(world).returncode == int(params["status"])


def _then_supplies(world, params, match):
    args = last_invocation(_state(world)["record"])
    assert "check" in args, args
    assert str(_state(world)["cache"]) in args, args
    assert str(_state(world)["pack_config"]) in args, args
    assert "tools" in args, args


def _then_cache_exists(world, params, match):
    assert _state(world)["cache"].is_dir()


def _absent_path(state, absent):
    if absent == "cache directory":
        return str(state["cache"])
    if absent == "pack ruff config":
        return str(state["pack_config"])
    raise AssertionError(f"unknown absent target: {absent}")


def _then_caller_option(world, params, match):
    args = last_invocation(_state(world)["record"])
    value = params["value"]
    assert args.count(value) == 1, args
    assert _absent_path(_state(world), params["absent"]) not in args, args


def _then_caller_equals(world, params, match):
    args = last_invocation(_state(world)["record"])
    assert args.count(match.group(1)) == 1, args
    assert str(_state(world)["pack_config"]) not in args, args


def _then_custom_config(world, params, match):
    args = last_invocation(_state(world)["record"])
    assert match.group(1) in args, args
    index = args.index("--config")
    assert args[index + 1] == match.group(1), args


def _then_not_installed(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "not installed" in result.stderr, result.stderr


def _then_missing_ruff_config(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "ruff config not found" in result.stderr, result.stderr
    assert _state(world)["missing_config"] in result.stderr, result.stderr


def _then_cannot_run(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "cannot run ruff" in result.stderr, result.stderr


def _then_missing_harness(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert _state(world)["missing_harness"] in result.stderr, result.stderr


HANDLERS = [
    step(
        r"^a temporary project with a harness config and an artifacts root$",
        _given_project,
    ),
    step(r"^a recording ruff on the project PATH that succeeds$", _given_recording),
    step(
        r"^a recording ruff on the project PATH that exits with status (?:<status>|\d+)$",
        _given_recording_status,
    ),
    step(r"^a ruff on the project PATH that cannot be executed$", _given_unrunnable),
    step(r"^no ruff on the project PATH$", _given_no_ruff),
    step(r"^the wrapper cache directory does not exist$", _given_cache_absent),
    step(
        r'^the environment sets RUFF4PY_CONFIG to "([^"]+)"$',
        _given_env_config,
    ),
    step(r"^no pack ruff config$", _given_no_pack_config),
    step(r"^the harness config is missing$", _given_missing_harness),
    step(r'^the ruff4py command runs with "([^"]+)"$', _when_flag),
    step(
        r'^the ruff4py command runs with an explicit "([^"]+)" verb and "([^"]+)"$',
        _when_check_verb,
    ),
    step(
        r'^the ruff4py command runs with the caller option (\S+) (\S+) and "([^"]+)"$',
        _when_option_value,
    ),
    step(
        r'^the ruff4py command runs with the caller option "([^"]+)" and "([^"]+)"$',
        _when_option_equals,
    ),
    step(
        r"^the ruff4py command succeeds showing the wrapper usage and the recording ruff was never invoked$",
        _then_help,
    ),
    step(
        r"^the ruff4py command is refused with exit code 2 saying that check is already supplied$",
        _then_verb_refused,
    ),
    step(r"^ruff4py exits with code (?:<status>|\d+)$", _then_status),
    step(
        r'^the recording ruff was run with "([^"]+)", the wrapper cache directory, the pack ruff config, and "([^"]+)"$',
        _then_supplies,
    ),
    step(r"^the wrapper cache directory exists$", _then_cache_exists),
    step(
        r"^the recording ruff was run with (.+) once and not run with the wrapper (.+)$",
        _then_caller_option,
    ),
    step(
        r'^the recording ruff was run with "([^"]+)" once and not run with the pack ruff config$',
        _then_caller_equals,
    ),
    step(
        r'^the recording ruff used "([^"]+)" as its config$',
        _then_custom_config,
    ),
    step(
        r"^the ruff4py command is refused with exit code 2 saying ruff is not installed$",
        _then_not_installed,
    ),
    step(
        r"^the ruff4py command is refused with exit code 2 naming the missing ruff config$",
        _then_missing_ruff_config,
    ),
    step(
        r"^the ruff4py command is refused with exit code 2 saying ruff cannot be run$",
        _then_cannot_run,
    ),
    step(
        r"^the ruff4py command is refused with exit code 2 naming the missing harness config$",
        _then_missing_harness,
    ),
]
