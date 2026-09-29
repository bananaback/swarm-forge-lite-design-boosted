import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

_ACCEPTANCE = Path(__file__).resolve().parent
_PERSIST = _ACCEPTANCE.parent
sys.path.insert(0, str(_ACCEPTANCE))
sys.path.insert(0, str(_PERSIST.parents[1] / "tools" / "shared"))

generator = importlib.import_module("generator")
wiring = importlib.import_module("wiring")


def main(argv: list[str]) -> int:
    resolved = wiring.load()
    if resolved.features is None:
        print("run_acceptance: no features root configured", file=sys.stderr)
        return 2
    if argv[1:]:
        features = [resolved.features / f"{stem}.feature" for stem in argv[1:]]
    else:
        features = sorted(resolved.features.glob("*.feature"))
    missing = [str(feature) for feature in features if not feature.is_file()]
    if missing:
        print("run_acceptance: missing " + ", ".join(missing), file=sys.stderr)
        return 2
    parser = resolved.pack_root / "tools" / "shared" / "gherkin-parser"
    dry_checker = resolved.pack_root / "tools" / "specifier" / "ir-dry-checker"
    output = resolved.hot_tests / "acceptance"
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
    env = dict(os.environ)
    paths = [str(root.parent) for root in resolved.source_roots]
    env["PYTHONPATH"] = os.pathsep.join([*paths, env.get("PYTHONPATH", "")])
    print("=== run generated acceptance tests ===")
    return subprocess.call(
        [sys.executable, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider"],
        cwd=resolved.hot_tests,
        env=env,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
