"""The op catalog: every op, its parameters, and one example.

`list` prints this catalog, so an agent learns the tool without the README.
`swarm.help({tool:'uml'})` serves the same data as JSON.
"""

from __future__ import annotations

from .ops_dsl import Op, Param, p
from .ops_mutates import MUTATES
from .ops_queries import QUERIES


def _list_run(model: dict, params: dict) -> tuple[dict, str]:
    rows = [{"op": op.name, "kind": op.kind, "purpose": op.purpose} for op in ALL_OPS]
    text = "\n".join(
        f"{row['op']:<16} {row['kind']:<6} {row['purpose']}" for row in rows
    )
    return {"count": len(rows), "ops": rows}, text


LIST = Op(
    "list",
    "query",
    "Print this catalog: every op and its one-line purpose.",
    [],
    "umlmodel list",
    _list_run,
)

ALL_OPS = [LIST, *QUERIES, *MUTATES]
OPS = {op.name: op for op in ALL_OPS}


def op_names() -> list:
    return [op.name for op in ALL_OPS]


def entry() -> dict:
    """The full usage: every op, its params, an example, and the invariants."""
    return {
        "ops": [
            {
                "op": op.name,
                "kind": op.kind,
                "purpose": op.purpose,
                "example": op.example,
                "params": [
                    {
                        "name": param.name,
                        "type": param.type,
                        "required": param.required,
                        "multi": param.multi,
                        "purpose": param.purpose,
                        "example": param.example,
                    }
                    for param in op.params
                ],
            }
            for op in ALL_OPS
        ],
        "invariants": INVARIANTS,
    }


INVARIANTS = [
    "One op runs per call: load, validate, apply the op, validate again, then write.",
    "The writer follows the input file: its escape of non-ASCII text, its indent, and its trailing newline. A file that escapes its non-ASCII text stays escaped.",
    "The write is atomic: a temp file in the model's directory plus os.replace.",
    "A rejected op prints one message, exits non-zero, and leaves the file byte-identical.",
    "An op that changes nothing writes nothing, so the file stays byte-identical.",
    "--dry-run prints the diff and writes nothing.",
    "check validates without an edit, lists every error and warning, and exits non-zero only on a real error.",
    "Ids are unique and are namespaces of the form component.Name.",
    "Every edge endpoint must resolve to a class or a foreign id.",
    "kind is one of: inheritance implements association dependency aggregation composition.",
    "stereotype is one of: class interface abstract enum.",
    "direction is tb or lr. packages[] each need id and label.",
    "A class whose first id segment is absent from levels is a warning (unassigned), not an error.",
]


__all__ = [
    "ALL_OPS",
    "INVARIANTS",
    "LIST",
    "MUTATES",
    "OPS",
    "QUERIES",
    "Op",
    "Param",
    "entry",
    "op_names",
    "p",
]
