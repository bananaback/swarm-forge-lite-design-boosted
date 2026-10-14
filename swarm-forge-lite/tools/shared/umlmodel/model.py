"""Read, serialize, and atomically write a model.json.

The writer follows the input file's own style: the escape of a non-ASCII
character, the indent, and the trailing newline. A file that escapes its non
ASCII characters stays escaped, so one small edit never rewrites the whole
file. A no-op write never touches the file at all.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections import namedtuple
from pathlib import Path

# A file with a `\uXXXX` escape uses the escaped style.
_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}")

Style = namedtuple("Style", "indent ensure_ascii trailing_newline")
DEFAULT_STYLE = Style(indent=2, ensure_ascii=False, trailing_newline=True)


def detect_style(text: str) -> Style:
    """Read the writer style from the input text."""
    indent: object = None
    for line in text.splitlines():
        if line[:1] == " ":
            indent = len(line) - len(line.lstrip(" "))
            break
        if line[:1] == "\t":
            indent = "\t"
            break
    return Style(
        indent=indent,
        ensure_ascii=bool(_ESCAPE.search(text)),
        trailing_newline=text.endswith("\n"),
    )


def read(path) -> tuple[dict, Style]:
    """Read a model.json and the style of its text."""
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text), detect_style(text)


def load(path) -> dict:
    """Read a model.json into a dict. A bad file raises the JSON error."""
    return read(path)[0]


def dumps(model: dict, style: Style | None = None) -> str:
    """Serialize a model in the given style (the default when none is given)."""
    style = style or DEFAULT_STYLE
    text = json.dumps(model, indent=style.indent, ensure_ascii=style.ensure_ascii)
    if style.trailing_newline:
        text += "\n"
    return text


def write_atomic(path, text: str) -> None:
    """Write text through a temp file in the same directory, then os.replace.

    A reader either sees the old file or the new one, never a half-written
    model. The temp file sits in the model's own directory, so the replace is
    atomic on one filesystem.
    """
    target = Path(path)
    handle, temp = tempfile.mkstemp(
        dir=str(target.parent), prefix=target.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, target)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
