"""Op catalog: query ops."""

from __future__ import annotations

from . import query
from .ops_dsl import M, Op, p

QUERIES = [
    Op(
        "classes",
        "query",
        "List every class.",
        [
            p(
                "package",
                purpose="Only the classes of this package id.",
                example="--package core",
            )
        ],
        f"umlmodel classes {M}",
        query.q_classes,
    ),
    Op(
        "class",
        "query",
        "Show one class by id, in full.",
        [p("id", required=True, purpose="The class id.", example="--id core.Present")],
        f"umlmodel class {M} --id core.Present",
        query.q_class,
    ),
    Op(
        "ops",
        "query",
        "List the ops of one class, with contract annotations.",
        [p("id", required=True, purpose="The class id.", example="--id core.Present")],
        f"umlmodel ops {M} --id core.Present",
        query.q_ops,
    ),
    Op(
        "packages",
        "query",
        "List the packages.",
        [],
        f"umlmodel packages {M}",
        query.q_packages,
    ),
    Op(
        "levels",
        "query",
        "List the level groups, inner first.",
        [],
        f"umlmodel levels {M}",
        query.q_levels,
    ),
    Op("edges", "query", "List every edge.", [], f"umlmodel edges {M}", query.q_edges),
    Op(
        "edges-of",
        "query",
        "List the edges that touch one class.",
        [p("id", required=True, purpose="The class id.", example="--id core.Present")],
        f"umlmodel edges-of {M} --id core.Present",
        query.q_edges_of,
    ),
    Op(
        "violations",
        "query",
        "List the inner->outer dependency violations.",
        [],
        f"umlmodel violations {M}",
        query.q_violations,
    ),
    Op(
        "unassigned",
        "query",
        "List the classes under no level (a warning, never an error).",
        [],
        f"umlmodel unassigned {M}",
        query.q_unassigned,
    ),
    Op(
        "dups",
        "query",
        "List duplicate class ids.",
        [],
        f"umlmodel dups {M}",
        query.q_dups,
    ),
    Op(
        "bad-edges",
        "query",
        "List the edges whose endpoint does not resolve.",
        [],
        f"umlmodel bad-edges {M}",
        query.q_bad_edges,
    ),
    Op(
        "orphans",
        "query",
        "List the classes that no edge touches.",
        [],
        f"umlmodel orphans {M}",
        query.q_orphans,
    ),
    Op(
        "annotations",
        "query",
        "List the annotation keys in use, with counts.",
        [],
        f"umlmodel annotations {M}",
        query.q_annotations,
    ),
    Op(
        "stats",
        "query",
        "Summarize the model.",
        [],
        f"umlmodel stats {M}",
        query.q_stats,
    ),
    Op(
        "check",
        "query",
        "Validate the model and list every error and warning. An error exits non-zero.",
        [],
        f"umlmodel check {M}",
        query.q_check,
    ),
]
