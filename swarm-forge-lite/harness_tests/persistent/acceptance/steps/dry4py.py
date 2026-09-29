"""Step handlers for the dry4py feature."""

import json

from .support import (
    DRY4PY,
    clean_env,
    install_fake_jscpd,
    last_invocation,
    prepend_path,
    run_tool,
    step,
    temp_project,
    write_text,
)


def _state(world):
    return world.state["dry"]


def _configure(world):
    state = _state(world)
    install_fake_jscpd(state["bin"])
    state["env"].update(
        {
            "JSCPD_RECORD": str(state["record"]),
            "JSCPD_REPORT": json.dumps({"duplicates": []}),
            "JSCPD_EXIT": "0",
            "JSCPD_WRITE_REPORT": "1",
        }
    )


def _set_report(world, duplicates):
    state = _state(world)
    state["duplicates"] = duplicates
    state["env"]["JSCPD_REPORT"] = json.dumps({"duplicates": duplicates})


def _region(name, start, end):
    return {"name": name, "start": int(start), "end": int(end)}


def _given_project(world, params, match):
    project = temp_project(world)
    write_text(project / "src" / "a.py", "print('a')\n")
    bin_dir = project / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    env = clean_env()
    prepend_path(env, bin_dir)
    world.state["dry"] = {
        "project": project,
        "bin": bin_dir,
        "record": project / "jscpd-record.jsonl",
        "env": env,
        "duplicates": [],
    }


def _given_clean(world, params, match):
    _configure(world)


def _given_duplicate(world, params, match):
    _configure(world)
    duplicates = list(_state(world).get("duplicates", []))
    duplicates.append(
        {
            "firstFile": _region(match.group(1), match.group(2), match.group(3)),
            "secondFile": _region(match.group(4), match.group(5), match.group(6)),
        }
    )
    _set_report(world, duplicates)


def _given_boom(world, params, match):
    _configure(world)
    _state(world)["env"].update({"JSCPD_STDERR": "boom\n", "JSCPD_EXIT": "3"})


def _given_status_one(world, params, match):
    _configure(world)
    _state(world)["env"]["JSCPD_EXIT"] = "1"


def _given_no_report(world, params, match):
    _configure(world)
    _state(world)["env"]["JSCPD_WRITE_REPORT"] = "0"


def _given_not_json(world, params, match):
    _configure(world)
    _state(world)["env"]["JSCPD_REPORT"] = "not json"


def _given_empty_object(world, params, match):
    _configure(world)
    _state(world)["env"]["JSCPD_REPORT"] = "{}"


def _given_no_jscpd(world, params, match):
    _state(world)["env"]["PATH"] = str(_state(world)["bin"])


def _run(world, args):
    state = _state(world)
    state["result"] = run_tool(DRY4PY, args, state["env"], cwd=state["project"])


def _when_no_paths(world, params, match):
    _run(world, [])


def _when_missing(world, params, match):
    _run(world, ["missing.py"])


def _when_source(world, params, match):
    _run(world, ["src"])


def _when_thresholds(world, params, match):
    _run(
        world,
        ["src", "--min-lines", params["min_lines"], "--min-tokens", params["min_tokens"]],
    )


def _when_defaults(world, params, match):
    _run(world, ["src"])


def _when_threshold_zero(world, params, match):
    _run(world, ["src", params["flag"], "0"])


def _when_min_lines_one(world, params, match):
    _run(world, ["src", "--min-lines", "1"])


def _result(world):
    return _state(world)["result"]


def _assert_pair(args, flag, value):
    for index, token in enumerate(args):
        if token == flag:
            assert args[index + 1] == value, args
            return
    raise AssertionError(f"{flag} not in {args}")


def _then_usage(world, params, match):
    result = _result(world)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert "usage" in result.stderr.lower(), result.stderr


def _then_missing(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "missing.py" in result.stderr, result.stderr


def _then_clean(world, params, match):
    result = _result(world)
    assert result.returncode == 0, result.stderr
    assert "No duplicate candidates found." in result.stdout, result.stdout


def _then_one(world, params, match):
    result = _result(world)
    assert result.returncode == 0, result.stderr
    assert "a.py:1-4" in result.stdout, result.stdout
    assert "b.py:1-4" in result.stdout, result.stdout
    assert "1 duplicate candidate(s)." in result.stdout, result.stdout


def _then_two(world, params, match):
    result = _result(world)
    assert result.returncode == 0, result.stderr
    for position in ("a.py:1-4", "b.py:1-4", "c.py:1-4", "d.py:1-4"):
        assert position in result.stdout, result.stdout
    assert "2 duplicate candidate(s)." in result.stdout, result.stdout


def _then_thresholds(world, params, match):
    args = last_invocation(_state(world)["record"])
    _assert_pair(args, "--min-lines", params.get("min_lines", "4"))
    _assert_pair(args, "--min-tokens", params.get("min_tokens", "50"))


def _then_bad_threshold(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert params["name"] in result.stderr, result.stderr


def _then_min_lines_one(world, params, match):
    args = last_invocation(_state(world)["record"])
    _assert_pair(args, "--min-lines", "1")


def _then_not_found(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "command not found" in result.stderr, result.stderr


def _then_boom(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "boom" in result.stderr, result.stderr


def _then_no_report(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "produced no report" in result.stderr, result.stderr


def _then_not_json(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "not valid JSON" in result.stderr, result.stderr


def _then_no_duplicates_list(world, params, match):
    result = _result(world)
    assert result.returncode == 1, (result.returncode, result.stderr)
    assert "no duplicate list" in result.stderr, result.stderr


HANDLERS = [
    step(r"^a temporary project with a source directory$", _given_project),
    step(
        r"^a recording jscpd on the project PATH that reports no duplicates$",
        _given_clean,
    ),
    step(
        r"^a recording jscpd on the project PATH that reports a duplicate from (\S+) lines (\d+)-(\d+) to (\S+) lines (\d+)-(\d+)$",
        _given_duplicate,
    ),
    step(
        r"^a duplicate from (\S+) lines (\d+)-(\d+) to (\S+) lines (\d+)-(\d+)$",
        _given_duplicate,
    ),
    step(
        r'^a recording jscpd on the project PATH that prints "([^"]+)" and exits with status (\d+)$',
        _given_boom,
    ),
    step(
        r"^a recording jscpd on the project PATH that reports no duplicates and exits with status (\d+)$",
        _given_status_one,
    ),
    step(
        r"^a recording jscpd on the project PATH that writes no report$",
        _given_no_report,
    ),
    step(
        r'^a recording jscpd on the project PATH that writes "(?!\{\})([^"]+)" as its report$',
        _given_not_json,
    ),
    step(
        r'^a recording jscpd on the project PATH that writes "{}" as its report$',
        _given_empty_object,
    ),
    step(r"^no jscpd on the project PATH$", _given_no_jscpd),
    step(r"^the dry4py command runs with no paths$", _when_no_paths),
    step(r'^the dry4py command runs with "([^"]+)"$', _when_missing),
    step(r"^the dry4py command runs with the source directory$", _when_source),
    step(
        r'^the dry4py command runs with threshold flags "--min-lines" (\S+) and "--min-tokens" (\S+) over the source directory$',
        _when_thresholds,
    ),
    step(
        r"^the dry4py command runs with the source directory and no threshold flags$",
        _when_defaults,
    ),
    step(
        r'^the dry4py command runs with the threshold (\S+) 0 over the source directory$',
        _when_threshold_zero,
    ),
    step(
        r'^the dry4py command runs with the threshold "--min-lines" 1 over the source directory$',
        _when_min_lines_one,
    ),
    step(
        r"^the dry4py command rejects the usage with exit code 2 and shows the usage$",
        _then_usage,
    ),
    step(
        r'^the dry4py command is refused with an error naming "([^"]+)"$',
        _then_missing,
    ),
    step(
        r"^the dry4py command succeeds reporting no duplicate candidates$",
        _then_clean,
    ),
    step(
        r'^the dry4py command succeeds listing "([^"]+)" and "([^"]+)" and reporting 1 duplicate candidate$',
        _then_one,
    ),
    step(
        r"^the dry4py command succeeds listing all four positions and reporting 2 duplicate candidates$",
        _then_two,
    ),
    step(
        r'^the dry4py command succeeds with the recording jscpd run with "--min-lines" (\S+) and "--min-tokens" (\S+)$',
        _then_thresholds,
    ),
    step(
        r"^the dry4py command is refused with an error naming ([^\s\"]+)$",
        _then_bad_threshold,
    ),
    step(
        r'^the dry4py command succeeds with the recording jscpd run with "--min-lines" 1$',
        _then_min_lines_one,
    ),
    step(
        r"^the dry4py command is refused with an error saying the detector command was not found$",
        _then_not_found,
    ),
    step(
        r'^the dry4py command is refused with an error reporting "([^"]+)"$',
        _then_boom,
    ),
    step(
        r"^the dry4py command is refused with an error saying the detector produced no report$",
        _then_no_report,
    ),
    step(
        r"^the dry4py command is refused with an error saying the report is not valid JSON$",
        _then_not_json,
    ),
    step(
        r"^the dry4py command is refused with an error saying the report has no duplicate list$",
        _then_no_duplicates_list,
    ),
]
