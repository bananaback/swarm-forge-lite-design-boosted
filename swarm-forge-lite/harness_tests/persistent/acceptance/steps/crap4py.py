"""Step handlers for the crap4py feature."""

import os
import re

from .support import (
    CRAP4PY,
    python_command,
    row_for,
    run_tool,
    step,
    temp_project,
    write_config,
    write_text,
)

SIMPLE = "def simple():\n    return 1\n"

BRANCHED = (
    "def branched(x):\n"
    "    if x:\n"
    "        return 1\n"
    "    if x > 1:\n"
    "        return 2\n"
    "    return 0\n"
)

FOUR = (
    "def four(x):\n"
    "    if x == 1:\n"
    "        return 1\n"
    "    if x == 2:\n"
    "        return 2\n"
    "    if x == 3:\n"
    "        return 3\n"
    "    return 0\n"
)

TEN = (
    "def ten(x):\n"
    "    if x == 1:\n"
    "        return 1\n"
    "    if x == 2:\n"
    "        return 2\n"
    "    if x == 3:\n"
    "        return 3\n"
    "    if x == 4:\n"
    "        return 4\n"
    "    if x == 5:\n"
    "        return 5\n"
    "    if x == 6:\n"
    "        return 6\n"
    "    if x == 7:\n"
    "        return 7\n"
    "    if x == 8:\n"
    "        return 8\n"
    "    if x == 9:\n"
    "        return 9\n"
    "    return 0\n"
)

PAIR = "def solid():\n    return 1\n\n\ndef flaky():\n    return 2\n"

COVERAGE_TEST = (
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).resolve().parent.parent / \"src\"))\n"
    "import sample\n"
    "\n"
    "\n"
    "def test_simple():\n"
    "    assert sample.simple() == 1\n"
)

FAKE_RADON = (
    "import sys\n"
    "sys.stderr.write(\"radon exploded\\n\")\n"
    "sys.exit(9)\n"
)


def _lcov(module, hits) -> str:
    lines = [f"SF:{module}"]
    lines += [f"DA:{number},{count}" for number, count in hits.items()]
    lines.append("end_of_record")
    return "\n".join(lines) + "\n"


def _setup(world, modules, write_lcov: bool = True):
    """Build a temp project from (module name, body, hits) triples."""
    project = temp_project(world)
    source = project / "src"
    lcov_lines = []
    for name, body, hits in modules:
        module = write_text(source / name, body)
        lcov_lines.append(_lcov(module, hits))
    config = write_config(
        project,
        {
            "workspace_root": ".",
            "artifacts_root": "dump",
            "hot_tests": "hot_tests",
            "source_roots": ["src"],
        },
    )
    lcov = project / "dump" / "coverage.lcov"
    if write_lcov:
        write_text(lcov, "".join(lcov_lines))
    env = dict(world.state["env"])
    env["SWARM_CONFIG"] = str(config)
    world.state["crap"] = {
        "project": project,
        "source": source,
        "lcov": lcov,
        "lcov_text": "".join(lcov_lines),
        "config": config,
        "env": env,
    }
    return project


def _run(world, args, cwd=None):
    state = world.state["crap"]
    state["result"] = run_tool(
        CRAP4PY, args, state["env"], cwd=cwd or state["project"]
    )


def _success(world):
    result = world.state["crap"]["result"]
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    return result.stdout


def _refused(world):
    result = world.state["crap"]["result"]
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    return result.stderr


def _existing_args(state, filters=()):
    return [
        "--use-existing-coverage",
        "--lcov",
        state["lcov"],
        "--source-root",
        state["source"],
        *filters,
    ]


def _write_command(project, lcov_text, exit_code):
    script = write_text(
        project / "coverage_command.py",
        "import sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)\n"
        f"Path(sys.argv[1]).write_text({lcov_text!r})\n"
        f"sys.exit({exit_code})\n",
    )
    return python_command(script) + " {lcov}"


def _given_complexity_one(world, params, match):
    _setup(world, [("sample.py", SIMPLE, {1: 1, 2: 1})])


def _given_absent_lines(world, params, match):
    _setup(world, [("sample.py", SIMPLE, {})])


def _given_complexity_three(world, params, match):
    _setup(world, [("branched.py", BRANCHED, {1: 1, 2: 0, 3: 0})])


def _given_complexity_four(world, params, match):
    _setup(world, [("four.py", FOUR, {number: 0 for number in range(1, 9)})])


def _given_complexity_ten(world, params, match):
    _setup(world, [("ten.py", TEN, {number: 1 for number in range(1, 21)})])


def _given_pair(world, params, match):
    _setup(world, [("pair.py", PAIR, {1: 1, 2: 1, 5: 0, 6: 0})])


def _given_alpha_beta(world, params, match):
    _setup(
        world,
        [
            ("alpha.py", SIMPLE, {1: 1, 2: 1}),
            ("beta.py", SIMPLE, {1: 1, 2: 1}),
        ],
    )


def _given_no_coverage(world, params, match):
    _setup(world, [("sample.py", SIMPLE, {})], write_lcov=False)


def _given_noop_command(world, params, match):
    project = _setup(world, [("sample.py", SIMPLE, {})], write_lcov=False)
    script = write_text(
        project / "coverage_command.py",
        "import sys\nsys.exit(0)\n",
    )
    world.state["crap"]["command"] = python_command(script)


def _given_failing_command(world, params, match):
    state = world.state["crap"]
    state["command"] = _write_command(
        state["project"], state["lcov_text"], exit_code=3
    )


def _given_test_suite(world, params, match):
    project = _setup(world, [("sample.py", SIMPLE, {})], write_lcov=False)
    write_text(project / "tests" / "test_sample.py", COVERAGE_TEST)
    world.state["crap"]["tests"] = project / "tests"


def _given_complexity_fails(world, params, match):
    project = _setup(world, [("sample.py", SIMPLE, {1: 1, 2: 1})])
    fake = write_text(project / "fakeradon" / "radon.py", FAKE_RADON)
    env = world.state["crap"]["env"]
    env["PYTHONPATH"] = (
        str(fake.parent) + os.pathsep + env.get("PYTHONPATH", "")
    )


def _given_malformed_coverage(world, params, match):
    _setup(world, [("sample.py", SIMPLE, {1: 1, 2: 1})])
    state = world.state["crap"]
    write_text(state["lcov"], "DA:1,1\n" + _lcov(state["source"] / "sample.py", {}))


def _given_explicit_coverage(world, params, match):
    state = world.state["crap"]
    explicit = write_text(
        state["project"] / "elsewhere" / "cov.lcov", state["lcov_text"]
    )
    state["explicit_lcov"] = explicit


def _when_existing(world, params, match):
    _run(world, _existing_args(world.state["crap"]))


def _when_filter(world, params, match):
    _run(world, _existing_args(world.state["crap"], (match.group(1),)))


def _when_command(world, params, match):
    state = world.state["crap"]
    _run(world, ["--coverage-command", state["command"], "--source-root", state["source"]])


def _when_command_writes(world, params, match):
    state = world.state["crap"]
    state["command"] = _write_command(state["project"], state["lcov_text"], exit_code=0)
    state["lcov"].unlink(missing_ok=True)
    _run(world, ["--coverage-command", state["command"], "--source-root", state["source"]])


def _when_default(world, params, match):
    state = world.state["crap"]
    _run(
        world,
        [
            "--source-root",
            state["source"],
            "--test-path",
            state["tests"],
        ],
    )


def _when_explicit(world, params, match):
    state = world.state["crap"]
    _run(
        world,
        [
            "--use-existing-coverage",
            "--lcov",
            state["explicit_lcov"],
            "--source-root",
            state["source"],
        ],
    )


def _then_complexity_one(world, params, match):
    row = row_for(_success(world), "simple")
    assert re.search(r"simple\s+\S+\s+1\s+100\.0%\s+1\.0", row), row


def _then_absent(world, params, match):
    row = row_for(_success(world), "simple")
    assert re.search(r"simple\s+\S+\s+1\s+unmeasured\s+unmeasured", row), row


def _then_fraction(world, params, match):
    row = row_for(_success(world), "branched")
    assert re.search(r"branched\s+\S+\s+3\s+33\.3%\s+5\.7", row), row


def _then_above(world, params, match):
    assert "1 function(s) above CRAP 10" in _success(world)


def _then_at_threshold(world, params, match):
    output = _success(world)
    row = row_for(output, "ten")
    assert re.search(r"ten\s+\S+\s+10\s+100\.0%\s+10\.0", row), row
    assert "0 function(s) above CRAP 10" in output


def _then_ranked(world, params, match):
    output = _success(world)
    assert output.index("flaky") < output.index("solid"), output


def _then_filtered(world, params, match):
    output = _success(world)
    assert "alpha.py" in output, output
    assert "beta.py" not in output, output


def _then_missing_coverage(world, params, match):
    assert "coverage.lcov" in _refused(world)


def _then_no_data(world, params, match):
    result = world.state["crap"]["result"]
    assert result.returncode == 0, result.stderr
    assert "no coverage data" in result.stderr, result.stderr
    row = row_for(result.stdout, "simple")
    assert re.search(r"simple\s+\S+\s+1\s+unmeasured\s+unmeasured", row), row


def _then_command_failed(world, params, match):
    result = world.state["crap"]["result"]
    assert result.returncode == 0, result.stderr
    assert "coverage command exited" in result.stderr, result.stderr
    row = row_for(result.stdout, "simple")
    assert re.search(r"simple\s+\S+\s+1\s+100\.0%\s+1\.0", row), row


def _then_covered(world, params, match):
    row = row_for(_success(world), "simple")
    assert re.search(r"simple\s+\S+\s+1\s+100\.0%\s+1\.0", row), row


def _then_complexity_failure(world, params, match):
    assert "radon" in _refused(world)


def _then_malformed(world, params, match):
    assert "malformed" in _refused(world)


HANDLERS = [
    step(
        r"^a project with a function of complexity 1 whose lines are all covered$",
        _given_complexity_one,
    ),
    step(
        r"^a project with a function whose lines are absent from the coverage file$",
        _given_absent_lines,
    ),
    step(
        r"^a project with a function of complexity 3 with 1 of its 3 lines hit$",
        _given_complexity_three,
    ),
    step(
        r"^a project with a function of complexity 4 whose lines are recorded with zero hits$",
        _given_complexity_four,
    ),
    step(
        r"^a project with a function of complexity 10 whose lines are all covered$",
        _given_complexity_ten,
    ),
    step(
        r"^a project with a covered function and an uncovered function both present in the coverage file$",
        _given_pair,
    ),
    step(
        r"^a project with a function in alpha\.py and a function in beta\.py$",
        _given_alpha_beta,
    ),
    step(
        r"^a project with a function and no coverage file$",
        _given_no_coverage,
    ),
    step(
        r"^a project with a function and a coverage command that writes no coverage file$",
        _given_noop_command,
    ),
    step(
        r"^a coverage command that writes the coverage file and then exits non-zero$",
        _given_failing_command,
    ),
    step(
        r"^a project with a passing test suite and a function of complexity 1 whose lines the suite covers$",
        _given_test_suite,
    ),
    step(
        r"^a project with a coverage file whose complexity source fails$",
        _given_complexity_fails,
    ),
    step(
        r"^a project with a coverage file whose data line precedes any source line$",
        _given_malformed_coverage,
    ),
    step(
        r"^a coverage file outside the default location$",
        _given_explicit_coverage,
    ),
    step(r"^the crap4py command runs with existing coverage$", _when_existing),
    step(
        r'^the crap4py command runs with existing coverage and the filter "([^"]+)"$',
        _when_filter,
    ),
    step(
        r"^the crap4py command runs with that coverage command$",
        _when_command,
    ),
    step(
        r"^the crap4py command runs with a coverage command that writes the coverage file$",
        _when_command_writes,
    ),
    step(
        r"^the crap4py command runs without coverage flags$",
        _when_default,
    ),
    step(
        r"^the crap4py command runs with existing coverage from the explicit coverage file$",
        _when_explicit,
    ),
    step(
        r"^the crap4py command succeeds with a report listing the function with complexity 1, coverage 100\.0%, and CRAP 1\.0$",
        _then_complexity_one,
    ),
    step(
        r"^the crap4py command succeeds with a report listing the function with coverage unmeasured and CRAP unmeasured$",
        _then_absent,
    ),
    step(
        r"^the crap4py command succeeds with a report listing the function with coverage 33\.3% and CRAP 5\.7$",
        _then_fraction,
    ),
    step(
        r"^the crap4py command succeeds with a report counting 1 function above CRAP 10$",
        _then_above,
    ),
    step(
        r"^the crap4py command succeeds with a report listing the function at CRAP 10\.0 and counting 0 functions above CRAP 10$",
        _then_at_threshold,
    ),
    step(
        r"^the crap4py command succeeds with a report listing the uncovered function before the covered function$",
        _then_ranked,
    ),
    step(
        r"^the crap4py command succeeds with a report listing only the alpha\.py function$",
        _then_filtered,
    ),
    step(
        r"^the crap4py command is refused with exit code 1 and an error naming the missing coverage file$",
        _then_missing_coverage,
    ),
    step(
        r"^the crap4py command succeeds with a warning that no coverage data was found and a report listing the function with coverage unmeasured and CRAP unmeasured$",
        _then_no_data,
    ),
    step(
        r"^the crap4py command succeeds with a warning that the coverage command exited non-zero and a report listing the function with CRAP 1\.0$",
        _then_command_failed,
    ),
    step(
        r"^the crap4py command succeeds with a report listing the function with coverage 100\.0% and CRAP 1\.0$",
        _then_covered,
    ),
    step(
        r"^the crap4py command is refused with exit code 1 and an error naming the complexity failure$",
        _then_complexity_failure,
    ),
    step(
        r"^the crap4py command is refused with exit code 1 and an error saying the coverage file is malformed$",
        _then_malformed,
    ),
]
