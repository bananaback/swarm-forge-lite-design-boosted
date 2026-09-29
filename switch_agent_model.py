#!/usr/bin/env python3
"""Assign a model to each agent in .opencode/agents from one map.

Usage::

    python3 switch_agent_model.py                    # apply AGENT_MODELS
    python3 switch_agent_model.py --list             # show keys + current plan
    python3 switch_agent_model.py --dry-run          # show changes, write nothing
    python3 switch_agent_model.py coder=mimo-v2.6-pro refactorer=grok-4.7
                                                     # one-off overrides

How it works
------------
``MODEL_KEYS`` maps a short key to the full model reference that lands in the
agent frontmatter. ``AGENT_MODELS`` maps an agent name (its ``.md`` filename
stem) to one of those keys. Edit ``AGENT_MODELS`` to pick a model per role and
run the script; every listed agent is rewritten to ``model: <reference>`` plus
its ``request.body``.

Rule
----
DeepSeek models must carry ``temperature`` and ``top_p``. Any key that resolves
to a reference containing ``deepseek`` gets ``DEEPSEEK_BODY`` automatically, and
the script refuses to write a DeepSeek agent that is missing either field.
Non-DeepSeek models get no ``request.body``; stale sampling params are removed.
A per-key ``body`` (see ``MODEL_KEYS``) can add or override params for any model.

Frontmatter is native V2: the variant is part of the model reference and
sampling parameters live under ``request.body``. Requires PyYAML.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

AGENTS_DIR = Path(__file__).resolve().parent / ".opencode" / "agents"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# DeepSeek billing/serving requires both of these under request.body.
DEEPSEEK_BODY = {"temperature": 1, "top_p": 0.95}

# --------------------------------------------------------------------------- #
# model key registry: key -> full model reference (+ optional body override)
# --------------------------------------------------------------------------- #
# The reference is what goes into `model:`. Variants use `#<variant>`.
MODEL_KEYS = {
    "space-bunny-free": "opencode-go/space-bunny-free#max",
    "deepseek-v4.1-flash": "opencode-go/deepseek-v4.1-flash#high",
    "deepseek-v4-flash": "opencode-go/deepseek-v4-flash#high",
    "deepseek-v4-pro": "opencode-go/deepseek-v4-pro",
    "glm-5.3": "opencode-go/glm-5.3",
    "glm-5.3-flash": "opencode-go/glm-5.3-flash",
    "gpt-5.6-luna": "opencode-go/gpt-5.6-luna",
    "grok-4.7": "opencode-go/grok-4.7",
    "grok-4.6": "opencode-go/grok-4.6",
    "kimi-k3": "opencode-go/kimi-k3",
    "kimi-k2.7-code": "opencode-go/kimi-k2.7-code",
    "mimo-v2.6-flash": "opencode-go/mimo-v2.6-flash",
    "mimo-v2.6-pro": "opencode-go/mimo-v2.6-pro",
    "mimo-v2.5": "opencode-go/mimo-v2.5",
    "mimo-v2.5-pro": "opencode-go/mimo-v2.5-pro",
    "minimax-m3": "opencode-go/minimax-m3",
    "qwen3.8-max": "opencode-go/qwen3.8-max",
    "qwen3.8-flash": "opencode-go/qwen3.8-flash",
}

# Extra sampling params per key, merged on top of the DeepSeek rule. Example:
#     "grok-4.7": {"body": {"temperature": 0.7}},
MODEL_EXTRA_BODY: dict[str, dict] = {}

# --------------------------------------------------------------------------- #
# the map you edit: agent name -> model key
# --------------------------------------------------------------------------- #
AGENT_MODELS = {
    # Every role runs DeepSeek V4.1 Flash except the test reviewer, which runs
    # the free Space Bunny (a deep reading pass over the authored tests).
    "orchestrator": "deepseek-v4.1-flash",
    "specifier": "deepseek-v4.1-flash",
    "interrogator": "deepseek-v4.1-flash",
    "modeler": "deepseek-v4.1-flash",
    "contractor": "deepseek-v4.1-flash",
    "critic": "deepseek-v4.1-flash",
    "coder": "deepseek-v4.1-flash",
    "test-reviewer": "space-bunny-free",
    "refactorer": "deepseek-v4.1-flash",
    "hotfixer": "deepseek-v4.1-flash",
}


def dump_frontmatter(data):
    return yaml.dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=4096,
    )


def resolve(key: str) -> tuple[str, dict]:
    """Return (model_reference, request.body) for a model key, applying rules."""
    if key not in MODEL_KEYS:
        known = ", ".join(sorted(MODEL_KEYS))
        raise SystemExit(f"unknown model key {key!r}\navailable keys: {known}")

    reference = MODEL_KEYS[key]
    body: dict = {}
    if "deepseek" in reference:
        body.update(DEEPSEEK_BODY)
    body.update(MODEL_EXTRA_BODY.get(key, {}))

    if "deepseek" in reference:
        missing = {"temperature", "top_p"} - set(body)
        if missing:
            raise SystemExit(
                f"{key!r} resolves to {reference!r} but request.body is missing "
                f"{', '.join(sorted(missing))}"
            )
    return reference, body


def convert(text: str, reference: str, body: dict) -> str:
    """Return text with the agent's model and request.body set."""
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError("missing frontmatter")
    front = yaml.safe_load(match.group(1)) or {}
    order = list(front.keys())
    front["model"] = reference

    request = front.get("request")
    if isinstance(request, dict):
        if body:
            request["body"] = dict(body)
        else:
            request.pop("body", None)
            if not request:
                front.pop("request", None)
    elif body:
        front["request"] = {"body": dict(body)}

    # Rebuild deterministically with request.body directly after model, so a
    # round trip (params dropped for a non-DeepSeek model, then restored) is
    # byte-identical instead of letting the block drift to the end.
    ordered = {}
    for key in order:
        if key == "request":
            continue
        ordered[key] = front[key]
        if key == "model" and "request" in front:
            ordered["request"] = front["request"]
    for key in front:
        if key not in ordered:
            ordered[key] = front[key]

    return "---\n" + dump_frontmatter(ordered) + "---\n" + text[match.end():]


def parse_overrides(argv: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for arg in argv:
        if "=" not in arg:
            raise SystemExit(f"expected agent=model-key, got {arg!r}")
        agent, _, key = arg.partition("=")
        if not agent or not key:
            raise SystemExit(f"expected agent=model-key, got {arg!r}")
        overrides[agent] = key
    return overrides


def print_listing(plan: dict[str, str]) -> None:
    print("model keys:")
    for key in sorted(MODEL_KEYS):
        print(f"  {key:<22} -> {MODEL_KEYS[key]}")
    print("\nagent plan:")
    for agent, key in sorted(plan.items()):
        reference, _ = resolve(key)
        print(f"  {agent:<22} -> {key}  ({reference})")


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    unknown = flags - {"--list", "--dry-run"}
    if unknown:
        raise SystemExit(f"unknown flag(s): {', '.join(sorted(unknown))}\n\n{__doc__}")

    plan = dict(AGENT_MODELS)
    plan.update(parse_overrides(args))

    if "--list" in flags:
        print_listing(plan)
        return 0

    dry_run = "--dry-run" in flags
    # Resolve every key up front so a typo fails before any file is touched.
    resolved = {agent: resolve(key) for agent, key in plan.items()}

    files = sorted(AGENTS_DIR.glob("*.md"))
    if not files:
        print(f"no agent files under {AGENTS_DIR}", file=sys.stderr)
        return 1

    changed = 0
    for path in files:
        agent = path.stem
        if agent not in resolved:
            print(f"{path.name}: skipped (not in map)")
            continue

        reference, body = resolved[agent]
        text = path.read_text(encoding="utf-8")
        updated = convert(text, reference, body)
        action = "would set" if dry_run else "set"
        if updated != text:
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
            changed += 1
            print(f"{path.name}: {action} {reference}  body={body or '{}'}")
        else:
            print(f"{path.name}: already {reference}")

    missing = sorted(set(plan) - {p.stem for p in files})
    for agent in missing:
        print(f"{agent}: no agent file in {AGENTS_DIR}", file=sys.stderr)

    verb = "would change" if dry_run else "changed"
    print(f"{changed} file(s) {verb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
