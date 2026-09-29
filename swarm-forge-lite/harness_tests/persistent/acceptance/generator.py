#!/usr/bin/env python3
"""Acceptance entrypoint generator -- turn JSON IR into pytest entry points."""

import hashlib
import json
import re
import sys
from pathlib import Path


def safe_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def metadata_name(feature_path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(feature_path).lower()).strip("-")
    return f"{slug}.json"


def feature_reference(ir: dict) -> str:
    slug = safe_name(ir.get("name", "unknown"))
    fallback = f"{slug}.feature"
    tools_root = Path(__file__).resolve().parents[3] / "tools" / "shared"
    try:
        if str(tools_root) not in sys.path:
            sys.path.insert(0, str(tools_root))
        import wiring
    except ImportError:
        return fallback
    try:
        resolved = wiring.load()
    except wiring.WiringError:
        return fallback
    if resolved.features is None:
        return fallback
    candidate = resolved.features / f"{slug}.feature"
    if not candidate.is_file():
        return fallback
    if candidate.is_relative_to(resolved.workspace_root):
        return str(candidate.relative_to(resolved.workspace_root))
    return str(candidate)


def docstring(scenario_name: str, example: dict[str, str]) -> str:
    text = f"Scenario: {scenario_name}"
    if example:
        rows = "; ".join(f"{key} = {value}" for key, value in sorted(example.items()))
        text = f"{text} ({rows})"
    return text.replace('"', '\\"')


def entrypoint_lines(ir: dict, acceptance_root: Path) -> list[str]:
    tools_root = acceptance_root.parents[2] / "tools" / "shared"
    lines = [
        f'"""Generated acceptance tests for {ir.get("name", "unknown")} feature."""',
        "",
        "import json",
        "import os",
        "import sys",
        "",
        f"sys.path.insert(0, {str(acceptance_root)!r})",
        f"sys.path.insert(0, {str(tools_root)!r})",
        "",
        "from runtime import Runtime",
        "from steps import STEP_HANDLERS",
        "",
        "_BASE_IR = " + json.dumps(ir, indent=4, sort_keys=True),
        "",
        "",
        "def _load_ir() -> dict:",
        '    """Load a mutated IR override, falling back to the generated base IR."""',
        '    override = os.environ.get("SWARM_ACCEPTANCE_IR")',
        "    if not override:",
        "        return _BASE_IR",
        '    with open(override, encoding="utf-8") as handle:',
        "        return json.load(handle)",
        "",
        "",
        "IR = _load_ir()",
        "",
        "",
        "def _build_runtime() -> Runtime:",
        '    """Create a runtime with all step handlers registered."""',
        "    rt = Runtime()",
        "    for pattern, handler in STEP_HANDLERS:",
        "        rt.register(pattern, handler)",
        "    return rt",
        "",
        "",
    ]
    for scenario_index, scenario in enumerate(ir["scenarios"]):
        scenario_name = scenario["name"]
        function_base = safe_name(scenario_name)
        rows = scenario.get("examples", []) or [{}]
        for example_index, example in enumerate(rows, start=1):
            lines.append(
                f"def test_{function_base}__example_{example_index}(tmp_path) -> None:"
            )
            lines.append(f'    """{docstring(scenario_name, example)}"""')
            lines.append("    rt = _build_runtime()")
            lines.append(f"    scenario = IR['scenarios'][{scenario_index}]")
            lines.append("    background = IR.get('background', [])")
            lines.append("    rt.run_scenario(scenario, background, tmp_path)")
            lines.append("")
    return lines


def write_metadata(ir: dict, ir_path: str, output: Path, test_file: Path) -> str:
    metadata_dir = output / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    generated = [test_file]
    hash_content = "".join(path.read_text() for path in sorted(generated))
    implementation_hash = "sha256:" + hashlib.sha256(hash_content.encode()).hexdigest()
    feature_path = feature_reference(ir)
    metadata = {
        "schema_version": 1,
        "feature_path": feature_path,
        "ir_path": ir_path,
        "implementation_hash": implementation_hash,
        "hash_scope": "generated_files",
        "generated_files": [str(path) for path in generated],
    }
    meta_file = metadata_dir / metadata_name(feature_path)
    meta_file.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Metadata: {meta_file}")
    print(f"Implementation hash: {implementation_hash}")
    return implementation_hash


def generate_entrypoint(ir_path: str, output_dir: str) -> None:
    """Generate a pytest entry point and metadata for one feature IR."""
    ir = json.loads(Path(ir_path).read_text())
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    acceptance_root = Path(__file__).resolve().parent
    test_file = output / f"test_{safe_name(ir.get('name', 'unknown'))}_acceptance.py"
    test_file.write_text("\n".join(entrypoint_lines(ir, acceptance_root)))
    print(f"Generated {test_file}")
    write_metadata(ir, ir_path, output, test_file)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <json-ir> <generated-test-output>")
        return 2
    try:
        generate_entrypoint(argv[1], argv[2])
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
