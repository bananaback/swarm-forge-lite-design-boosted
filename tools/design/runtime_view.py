#!/usr/bin/env python3
"""Render `architecture/runtime.json` into the runtime architecture page.

This is a view over the authored runtime model: nodes, zones and edges only.
Agents edit the JSON through `arch runtime ...`; nobody edits this renderer to
change the picture.
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

TONES = {
    "entry": ("#eef3fb", "#6b7f99"),
    "pipe": ("#ffffff", "#64748b"),
    "analysis": ("#f2f8ec", "#6f8f55"),
    "output": ("#fdf5ec", "#b07d4f"),
}


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def render(model_path: Path, out_path: Path) -> None:
    data = json.loads(model_path.read_text(encoding="utf-8"))
    width, height = data["canvas"]
    boxes = {
        n["id"]: (n["x"], n["y"], n["w"], n["h"], n["label"], n["sub"], n["note"], n["tone"])
        for n in data["nodes"]
    }
    edges = [
        (e["from"], e["side"], e["to"], e["to_side"], e["kind"], e["label"], e["dx"], e["dy"])
        for e in data["edges"]
    ]

    def anchor(box_id: str, side: str) -> tuple[float, float]:
        zone = next((z for z in data["zones"] if z.get("id") == box_id), None)
        if zone is not None:
            x, y, w, h = zone["x"], zone["y"], zone["w"], zone["h"]
            return {"top": (x + w / 2, y), "bottom": (x + w / 2, y + h)}[side]
        x, y, w, h = boxes[box_id][:4]
        return {
            "top": (x + w / 2, y),
            "bottom": (x + w / 2, y + h),
            "left": (x, y + h / 2),
            "right": (x + w, y + h / 2),
        }[side]

    parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="runtime architecture">',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#475569"/></marker>'
        '<marker id="ad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#94a3b8"/></marker></defs>',
    ]
    for zone in data["zones"]:
        parts.append(
            f'<rect x="{zone["x"]}" y="{zone["y"]}" width="{zone["w"]}" height="{zone["h"]}" rx="14" '
            f'fill="#f8fafc" stroke="#94a3b8" stroke-dasharray="7 6"/>'
            f'<text x="{zone["x"] + 16}" y="{zone["y"] + 22}" font-size="11.5" fill="#64748b" '
            f'letter-spacing=".06em">{escape(zone["label"])}</text>'
        )
    labels: list[tuple[float, float, str]] = []
    for src, sside, dst, dside, kind, label, dx, dy in edges:
        x1, y1 = anchor(src, sside)
        x2, y2 = anchor(dst, dside)
        vx, vy = x2 - x1, y2 - y1
        length = math.hypot(vx, vy) or 1
        x2s, y2s = x2 - vx / length * 7, y2 - vy / length * 7
        dash = ' stroke-dasharray="5 5"' if kind == "dash" else ""
        colour = "#94a3b8" if kind == "dash" else "#475569"
        marker = "ad" if kind == "dash" else "a"
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2s:.1f}" y2="{y2s:.1f}" stroke="{colour}" '
            f'stroke-width="1.6"{dash} marker-end="url(#{marker})"/>'
        )
        if label:
            labels.append(((x1 + x2s) / 2 + dx, (y1 + y2s) / 2 + dy, label))
    for box_id, (x, y, w, h, title, sub, note, tone) in boxes.items():
        fill, stroke = TONES[tone]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="1.5"/>'
            f'<text x="{x + 13}" y="{y + 27}" font-size="12.5" font-weight="600" fill="#1e293b">'
            f"{escape(title)}</text>"
            f'<text x="{x + 13}" y="{y + 46}" font-size="10.5" fill="#64748b">{escape(sub)}</text>'
        )
        if note:
            parts.append(
                f'<circle cx="{x + w - 25}" cy="{y + 24}" r="13" fill="#334155"/>'
                f'<text x="{x + w - 25}" y="{y + 27.5}" font-size="9" fill="#ffffff" '
                f'text-anchor="middle">{escape(note)}</text>'
            )
    for lx, ly, label in labels:
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" fill="#475569" text-anchor="middle" '
            f'paint-order="stroke" stroke="#ffffff" stroke-width="3.5">{escape(label)}</text>'
        )
    parts.append("</svg>")
    svg = "".join(parts)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>DS91 — runtime architecture</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; padding: 28px 32px 40px; font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1e293b; background: #fff; }}
  h1 {{ font-size: 21px; margin: 0 0 4px; }}
  p {{ margin: 0 0 16px; color: #475569; max-width: 1000px; }}
  svg {{ width: 100%; max-width: {width}px; height: auto; display: block; }}
  footer {{ margin-top: 14px; color: #64748b; font-size: 12.5px; max-width: 1000px; }}
  code {{ font-size: 12.5px; background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }}
</style></head><body>
<h1>DS91 — runtime architecture</h1>
<p>One box per subsystem, solid arrows for data or calls, dashed for seams. The runtime model is authored; the page is generated. Edit it through <code>arch runtime</code>, never here.</p>
{svg}
<footer>
  <p>Generated from the selected project's <code>architecture/&lt;project&gt;/runtime.json</code> — {len(boxes)} subsystems, {len(edges)} edges. Edit it through <code>arch runtime</code>; never edit this page.</p>
</footer>
</body></html>
"""
    _write(out_path, html)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import paths

    render(paths.RUNTIME, paths.DOCS / "ARCHITECTURE.html")
