"""Minimal EDN reader for the metrics files the analyzers write.

Only the forms those files use: maps, vectors, lists, strings, numbers, nil,
booleans, keywords, and symbols. No tagged literals, no sets, no metadata.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(
    r'[\s,]*(?:("(?:[^"\\]|\\.)*")|([\[\]{}()])|(:[^\s,\[\]{}()]+)|([^\s,\[\]{}()]+))',
    re.DOTALL,
)


def _tokens(text: str):
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            remainder = text[position:].strip()
            if not remainder:
                return
            raise ValueError(f"cannot read EDN near {remainder[:20]!r}")
        position = match.end()
        literal, bracket, keyword, symbol = match.groups()
        if literal is not None:
            yield ("string", _unescape(literal[1:-1]))
        elif bracket is not None:
            yield ("bracket", bracket)
        elif keyword is not None:
            yield ("keyword", keyword[1:])
        elif symbol is not None:
            yield ("symbol", symbol)


def _unescape(text: str) -> str:
    return (
        text.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _atom(kind: str, value: str):
    if kind == "keyword":
        # Keys are compared against plain names by every reader in this pack.
        return value
    if value == "nil":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return ("symbol", value)


class _Reader:
    def __init__(self, tokens):
        self._tokens = list(tokens)
        self._at = 0

    def next(self):
        token = self._tokens[self._at]
        self._at += 1
        return token

    def peek(self):
        return self._tokens[self._at] if self._at < len(self._tokens) else None

    def value(self):
        kind, raw = self.next()
        if kind == "bracket":
            return self.collection(raw)
        if kind == "string":
            return raw
        return _atom(kind, raw)

    def collection(self, opener: str):
        closing = {"[": "]", "{": "}", "(": ")"}[opener]
        if opener == "{":
            result = {}
            while True:
                kind, raw = self.peek()
                if kind == "bracket" and raw == closing:
                    self.next()
                    return result
                key = self.value()
                result[key] = self.value()
        result = []
        while True:
            token = self.peek()
            if token is None:
                raise ValueError("unterminated EDN collection")
            kind, raw = token
            if kind == "bracket" and raw == closing:
                self.next()
                return tuple(result)
            result.append(self.value())


def loads(text: str):
    """Parse one EDN document."""
    reader = _Reader(_tokens(text))
    return reader.value()
