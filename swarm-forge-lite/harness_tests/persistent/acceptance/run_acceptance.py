#!/usr/bin/env python3
"""Run the harness acceptance pipeline: parse, dry-check, generate, and test.

The harness area owns its own features, so it owns its own runnable pipeline.
The pattern matches the wired project's pipeline; only the wiring source is
shared, and it resolves the harness features root from the pack config.
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path

_ACCEPTANCE = Path(__file__).resolve().parent
sys.path.insert(0, str(_ACCEPTANCE))


def load_wiring():
    tools_root = Path(__file__).resolve().parents[2].parent / "tools" / "shared"
    sys.path.insert(0, str(tools_root))
    import wiring

    return wiring


def main() -> int:
    generator = importlib.import_module("generator")
    wiring = load_wiring()
    resolved = wiring.load()
    if resolved.features is None:
        print("run_acceptance: no features root configured", file=sys.stderr)
        return 2
    parser = resolved.pack_root / "tools" / "shared" / "gherkin-parser"
    dry_checker = resolved.pack_root / "tools" / "specifier" / "ir-dry-checker"
    output = resolved.hot_tests / "acceptance"
    features = sorted(resolved.features.glob("*.feature"))
    if not features:
        print(f"run_acceptance: no features under {resolved.features}")
        return 0
    tests = []
    for feature in features:
        ir = resolved.artifacts_root / f"{feature.stem}.json"
        dry = resolved.artifacts_root / f"{feature.stem}.dry.json"
        print(f"=== {feature.stem}: parse ===")
        subprocess.run([str(parser), str(feature), str(ir)], check=True)
        print(f"=== {feature.stem}: dry check ===")
        subprocess.run([str(dry_checker), str(ir), str(dry)], check=True)
        print(f"=== {feature.stem}: generate ===")
        subprocess.run(
            [sys.executable, str(_ACCEPTANCE / "generator.py"), str(ir), str(output)],
            check=True,
        )
        tests.append(str(output / generator.test_file_name(json.loads(ir.read_text()))))
    print("=== run generated acceptance tests ===")
    return subprocess.call(
        [sys.executable, "-m", "pytest", *tests, "-q"],
        cwd=resolved.hot_tests,
    )


if __name__ == "__main__":
    sys.exit(main())
