"""Validate a pack config against `config/pack.schema.json`.

Small on purpose: the subset of JSON Schema this pack's config uses — `type`,
`required`, `properties`, `additionalProperties`, `items`, `minItems`,
`minProperties`, `enum`. No third-party dependency, because the validator runs
before anything is installed.
"""

from __future__ import annotations

import json
from pathlib import Path

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "number": (int, float),
    "integer": int,
}


def load(pack: Path) -> dict:
    return json.loads((pack / "config" / "pack.schema.json").read_text(encoding="utf-8"))


def _type_ok(value, expected: str) -> bool:
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, TYPES[expected])


def _check(value, schema: dict, where: str, errors: list, warnings: list) -> None:
    expected = schema.get("type")
    if expected and not _type_ok(value, expected):
        errors.append(f"{where}: expected {expected}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: expected one of {schema['enum']}")
    if expected == "object" and isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing {key!r}")
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties")
        for key, child in value.items():
            child_where = f"{where}.{key}" if where else key
            if key in properties:
                _check(child, properties[key], child_where, errors, warnings)
            elif isinstance(extra, dict):
                _check(child, extra, child_where, errors, warnings)
            elif extra is False:
                warnings.append(f"{where or 'config'}: unknown key {key!r}")
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            errors.append(f"{where}: needs at least {schema['minProperties']} entries")
    if expected == "array" and isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{where}: needs at least {schema['minItems']} items")
        if "items" in schema:
            for index, item in enumerate(value):
                _check(item, schema["items"], f"{where}[{index}]", errors, warnings)


def validate(config: dict, schema: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block; warnings are reported."""
    errors: list[str] = []
    warnings: list[str] = []
    _check(config, schema, "", errors, warnings)
    return errors, warnings
