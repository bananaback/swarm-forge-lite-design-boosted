"""Command line entry point for the uml model tool.

Usage:
  python3 <pack>/tools/shared/umlmodel <op> --model MODEL.json [--dry-run] [--json]
  python3 <pack>/tools/shared/umlmodel list

The CLI output is readable text. `--json` prints one compact JSON object, which
the `swarm.uml` Code Mode tool reads. `--args '<json>'` supplies named params in
one shot; an explicit flag overrides it.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from . import diff
from . import model as model_file
from .errors import UmlModelError
from .ops import OPS, op_names
from .validate import errors as validation_errors

USAGE = (
    "umlmodel -- query and mutate a uml model.json\n"
    "\n"
    "usage:\n"
    "  umlmodel <op> --model MODEL.json [--dry-run] [--json] [--flag value ...]\n"
    "  umlmodel list\n"
    "\n"
    "Run `umlmodel list` for every op and its one-line purpose.\n"
    "Run `umlmodel <op> --help` for one op's params and example."
)


def _read_value(param, argv, index):
    """Read one flag value, honouring the param's declared type."""
    if param.type == "bool":
        if index < len(argv) and argv[index] in ("true", "false"):
            return argv[index] == "true", index + 1
        return True, index
    if index >= len(argv) or argv[index].startswith("--"):
        raise UmlModelError(f"--{param.name} needs a value")
    raw = argv[index]
    if param.type == "int":
        try:
            return int(raw), index + 1
        except ValueError:
            raise UmlModelError(
                f"--{param.name} needs an integer, got {raw!r}"
            ) from None
    if param.type == "json":
        try:
            return json.loads(raw), index + 1
        except json.JSONDecodeError:
            raise UmlModelError(f"--{param.name} needs JSON, got {raw!r}") from None
    return raw, index + 1


def _merge_multi(params: dict, key: str, value) -> None:
    current = params.get(key)
    if current is None:
        params[key] = [value]
    elif isinstance(current, list):
        current.append(value)
    else:
        params[key] = [current, value]


def parse(argv, op) -> tuple[dict, dict]:
    """Split argv into the op params and the universal options."""
    spec = OPS[op]
    by_name = {param.name: param for param in spec.params}
    params: dict = {}
    options = {"json": False, "dry_run": False, "model": None}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--json":
            options["json"] = True
            index += 1
        elif token == "--dry-run":
            options["dry_run"] = True
            index += 1
        elif token == "--model":
            if index + 1 >= len(argv):
                raise UmlModelError("--model needs a path")
            options["model"] = argv[index + 1]
            index += 2
        elif token == "--args":
            if index + 1 >= len(argv):
                raise UmlModelError("--args needs a JSON object")
            payload = json.loads(argv[index + 1])
            if not isinstance(payload, dict):
                raise UmlModelError("--args needs a JSON object")
            params.update(payload)
            index += 2
        elif token.startswith("--"):
            key = token[2:]
            param = by_name.get(key)
            if param is None:
                raise UmlModelError(
                    f"{op} has no param --{key}; known: {', '.join(by_name) or '(none)'}"
                )
            value, index = _read_value(param, argv, index + 1)
            if param.multi:
                _merge_multi(params, key, value)
            else:
                params[key] = value
        else:
            raise UmlModelError(f"unexpected argument {token!r}; use --name value")
    unknown = sorted(set(params) - set(by_name))
    if unknown:
        raise UmlModelError(
            f"{op} has no param {', '.join('--' + key for key in unknown)};"
            f" known: {', '.join(by_name) or '(none)'}"
        )
    return params, options


def _reject(model: dict, label: str) -> None:
    problems = validation_errors(model)
    if problems:
        first = problems[0]
        raise UmlModelError(
            f"{label} fails validation: {first['code']}: {first['message']}"
            f" ({len(problems)} problem(s))"
        )


def _result(path, op, ok, changed, code, text, data) -> dict:
    out = {
        "model": str(path) if path else None,
        "op": op,
        "ok": ok,
        "changed": changed,
        "exit": code,
        "stdout": text,
    }
    out.update(data)
    return out


def run(op: str, params: dict, options: dict) -> dict:
    """Run exactly one op and return the result object."""
    spec = OPS[op]
    if op == "list":
        data, text = spec.run({}, params)
        return _result(None, op, True, False, 0, text, data)
    raw = options.get("model")
    if not raw:
        raise UmlModelError(f"{op} needs --model PATH")
    path = Path(raw).expanduser()
    if not path.is_file():
        raise UmlModelError(f"no such model: {raw}")
    original, style = model_file.read(path)
    if op != "check":
        _reject(original, "the input model")
    working = copy.deepcopy(original)
    data, text = spec.run(working, params)
    if spec.kind == "mutate":
        _reject(working, "the result")
    changed = working != original
    code = 1 if op == "check" and data.get("errors") else 0
    if spec.kind == "mutate":
        if options.get("dry_run"):
            change_text = (
                diff.render(original, working, style) if changed else "(no change)"
            )
            text = f"{text}\n{change_text}"
        elif changed:
            model_file.write_atomic(path, model_file.dumps(working, style))
    return _result(path, op, code == 0, changed, code, text, data)


def _emit(result: dict, options: dict) -> None:
    if options.get("json"):
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result["stdout"])


def _fail(op, options, message: str) -> int:
    text = f"umlmodel: {message}"
    if options.get("json"):
        payload = {
            "model": options.get("model"),
            "op": op,
            "ok": False,
            "changed": False,
            "exit": 2,
            "stdout": text,
            "message": message,
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(text, file=sys.stderr)
    return 2


def _op_help(op: str) -> str:
    spec = OPS[op]
    lines = [f"{op} ({spec.kind}) -- {spec.purpose}", "", "params:"]
    if spec.params:
        for param in spec.params:
            required = "required" if param.required else "optional"
            lines.append(
                f"  --{param.name:<14} {param.type:<5} {required:<8} {param.purpose}"
                f"   e.g. {param.example}"
            )
    else:
        lines.append("  (none)")
    lines += ["", f"example: {spec.example}"]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    op = argv[0]
    if op not in OPS:
        print(f"umlmodel: unknown op {op!r}", file=sys.stderr)
        print(f"known ops: {', '.join(op_names())}", file=sys.stderr)
        return 2
    options = {"json": "--json" in argv}
    if "-h" in argv or "--help" in argv:
        print(_op_help(op))
        return 0
    try:
        params, options = parse(argv[1:], op)
        result = run(op, params, options)
    except UmlModelError as error:
        return _fail(op, options, str(error))
    _emit(result, options)
    return int(result.get("exit", 0))


if __name__ == "__main__":
    sys.exit(main())
