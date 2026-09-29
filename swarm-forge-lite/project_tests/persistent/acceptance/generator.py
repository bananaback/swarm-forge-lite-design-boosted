import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

_ACCEPTANCE = Path(__file__).resolve().parent
_PERSIST = _ACCEPTANCE.parent
_PACK = _PERSIST.parents[1]
sys.path.insert(0, str(_PACK / "tools" / "shared"))

wiring = importlib.import_module("wiring")


def safe_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def metadata_name(feature_path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(feature_path).lower()).strip("-")
    return f"{slug}.json"


def test_file_name(ir: dict) -> str:
    return f"test_{safe_name(ir.get('name', 'unknown'))}_acceptance.py"


def feature_reference(ir_path: str) -> str:
    stem = Path(ir_path).stem
    fallback = f"{stem}.feature"
    try:
        resolved = wiring.load()
    except wiring.WiringError:
        return fallback
    if resolved.features is None:
        return fallback
    candidate = resolved.features / f"{stem}.feature"
    if not candidate.is_file():
        return fallback
    if candidate.is_relative_to(resolved.workspace_root):
        return str(candidate.relative_to(resolved.workspace_root))
    return str(candidate)


def entrypoint_lines(ir: dict, acceptance_root: Path) -> list[str]:
    lines = [
        "import json",
        "import os",
        "import sys",
        "",
        f"sys.path.insert(0, {str(acceptance_root)!r})",
        "",
        "from runtime import Runtime",
        "from steps import STEP_HANDLERS",
        "",
        "_BASE_IR = " + json.dumps(ir, indent=4, sort_keys=True),
        "",
        "",
        "def _load_ir() -> dict:",
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
        "    rt = Runtime()",
        "    for pattern, handler in STEP_HANDLERS:",
        "        rt.register(pattern, handler)",
        "    return rt",
        "",
        "",
    ]
    for scenario_index, scenario in enumerate(ir["scenarios"]):
        function_base = safe_name(scenario["name"])
        rows = scenario.get("examples", []) or [{}]
        for example_index, _ in enumerate(rows, start=1):
            lines.append(
                f"def test_{function_base}__example_{example_index}(tmp_path) -> None:"
            )
            lines.append("    rt = _build_runtime()")
            lines.append(f"    scenario = IR['scenarios'][{scenario_index}]")
            lines.append("    background = IR.get('background', [])")
            lines.append("    rt.run_scenario(scenario, background, tmp_path)")
            lines.append("")
    return lines


def write_metadata(ir: dict, ir_path: str, output: Path, test_file: Path) -> str:
    metadata_dir = output / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    hash_content = test_file.read_text()
    implementation_hash = "sha256:" + hashlib.sha256(hash_content.encode()).hexdigest()
    feature_path = feature_reference(ir_path)
    metadata = {
        "schema_version": 1,
        "feature_path": feature_path,
        "ir_path": ir_path,
        "implementation_hash": implementation_hash,
        "hash_scope": "generated_files",
        "generated_files": [str(test_file)],
    }
    meta_file = metadata_dir / metadata_name(feature_path)
    meta_file.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Metadata: {meta_file}")
    print(f"Implementation hash: {implementation_hash}")
    return implementation_hash


def generate_entrypoint(ir_path: str, output_dir: str) -> None:
    ir = json.loads(Path(ir_path).read_text())
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    acceptance_root = _ACCEPTANCE
    test_file = output / test_file_name(ir)
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
