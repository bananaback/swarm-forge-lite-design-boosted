"""DSL for the op catalog: Param, Op, and the p factory."""

from __future__ import annotations

from collections import namedtuple

Param = namedtuple("Param", "name type required multi purpose example")
Op = namedtuple("Op", "name kind purpose params example run")


def p(
    name,
    type="str",
    required=False,
    multi=False,
    purpose="",
    example="",
) -> Param:
    return Param(name, type, required, multi, purpose, example)


M = "--model m.json"
