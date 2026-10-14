"""The upstream rank rule, used by the `violations` query.

This is a port of `domain/policy.clj`: collapse the foreign ids, merge each
pair by the strongest kind, rank a class by its longest dotted prefix, and mark
a `dependency` that runs from an inner rank to an outer rank.
"""

from __future__ import annotations

from .validate import class_ids, foreign_ids

KIND_RANK = {
    "implements": 4,
    "inheritance": 4,
    "composition": 3,
    "aggregation": 2,
    "association": 1,
    "dependency": 0,
}
DEFAULT_KIND = "association"


def ranks(model: dict) -> dict:
    """Map a level segment to its rank. A small rank is inner."""
    table: dict[str, int] = {}
    for rank, group in enumerate(model.get("levels") or []):
        if not isinstance(group, list):
            continue
        for segment in group:
            table.setdefault(str(segment), rank)
    return table


def rank_of(cid, table: dict):
    """The exact key, else the longest dotted prefix."""
    parts = str(cid).split(".")
    for length in range(len(parts), 0, -1):
        hit = table.get(".".join(parts[:length]))
        if hit is not None:
            return hit
    return None


def _prefixes(model: dict) -> list:
    return sorted(foreign_ids(model), key=len, reverse=True)


def _collapse(model: dict, table: dict) -> dict:
    """The merged edges: foreign remap, self-drop, strongest-kind merge."""
    ids = set(class_ids(model))
    prefixes = _prefixes(model)

    def remap(cid: str) -> str:
        for prefix in prefixes:
            if cid == prefix or cid.startswith(prefix + "."):
                return prefix
        return cid

    merged: dict[tuple, str] = {}
    for edge in model.get("edges") or []:
        left = remap(str(edge.get("from")))
        right = remap(str(edge.get("to")))
        if left == right:
            continue
        if left not in ids and left not in prefixes:
            continue
        if right not in ids and right not in prefixes:
            continue
        kind = str(edge.get("kind") or DEFAULT_KIND)
        key = (left, right)
        best = merged.get(key)
        if best is None or KIND_RANK.get(kind, 0) > KIND_RANK.get(best, 0):
            merged[key] = kind
    return _apply_overrides(model, merged)


def _apply_overrides(model: dict, merged: dict) -> dict:
    omitted = {
        (str(pair[0]), str(pair[1]))
        for pair in (model.get("omit-edges") or [])
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    }
    kinds = model.get("edge-kinds") or {}
    out: dict[tuple, str] = {}
    for (left, right), kind in merged.items():
        if (left, right) in omitted:
            continue
        override = kinds.get(f"{left}->{right}")
        out[(left, right)] = str(override) if override else kind
    return out


def violations(model: dict) -> list:
    """The dependency edges that run from an inner rank to an outer rank."""
    table = ranks(model)
    out = []
    for (left, right), kind in _collapse(model, table).items():
        if kind != "dependency":
            continue
        left_rank = rank_of(left, table)
        right_rank = rank_of(right, table)
        if left_rank is not None and right_rank is not None and left_rank < right_rank:
            out.append(
                {
                    "from": left,
                    "to": right,
                    "from_rank": left_rank,
                    "to_rank": right_rank,
                }
            )
    out.sort(key=lambda row: (row["from_rank"], row["from"], row["to"]))
    return out
