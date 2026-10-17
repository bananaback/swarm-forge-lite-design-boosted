#!/usr/bin/env python3
"""umlview render -- UML model -> one standalone HTML diagram.

The model and every rule below are a faithful port of unclebob/uml-viewer's domain
(`domain/ir.clj` normalization, `domain/policy.clj` ranks + dependency rule,
`domain/config.clj` crap grades). We changed three things: the display is HTML/SVG
instead of Quil, the language analysis (`scan_python.py`) reads Python instead of
Clojure, and a module with no functions is not graded (`_crap_sample`). No new concepts.

Upstream-only findings:
  - `dep-rule`   : a :dependency from an inner to an outer rank (policy.clj)
  - `dup-id`     : duplicate class id               (ir.clj throws)
  - `bad-edge`   : edge naming an unknown class      (ir.clj throws)

Upstream-only grades (config.clj): `crap-risk` (mu + sigma), `crap-grade` (the risk on
the 1-10 scale over the stops 8/12/20), and `pool-crap` (function-weighted mu, max and
population sigma). The mutation half of the upstream model is not ported.

Usage:
  render.py MODEL.json [--out OUT.html] [--template PATH] [--dagre PATH] [--check] [--public]
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE_LAUNCHER = Path(__file__).resolve().parent
if str(_HERE_LAUNCHER) not in sys.path:
    sys.path.insert(0, str(_HERE_LAUNCHER))

import render_grade
import render_model
import render_view

for _module in (render_model, render_grade, render_view):
    for _name, _value in _module.__dict__.items():
        if not _name.startswith("__"):
            globals()[_name] = _value

if __name__ == "__main__":
    sys.exit(render_view.main())
