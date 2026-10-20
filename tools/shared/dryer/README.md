# dryer (vendored)

Structural duplicate finder for Clojure, Java, Go, TypeScript, Rust, and
Python. The pack runs the Python path: it normalizes each function or method,
then scores every same-language pair by Jaccard similarity of its structural
fingerprints. A pair at or above `--threshold`, and large enough for
`--min-lines` and `--min-nodes`, is a candidate.

## Provenance

Vendored unmodified from [`unclebob/dryer`](https://github.com/unclebob/dryer)
at version 0.1.0 (commit `master`), licence 0BSD. The `LICENSE` file beside
this note is upstream's. Every `*.py` file is byte-identical to upstream
`src/dryer`. The pack does not pip-install the tool and does not point at an
upstream checkout.

Upstream runtime dependencies: `tree-sitter` and `tree-sitter-language-pack`;
`requires-python >= 3.11`.

## Run

The package is importable when `<pack>/tools/shared` is on `PYTHONPATH`, so
the entry point is `python3 -m dryer`:

```bash
PYTHONPATH=<pack>/tools/shared python3 -m dryer --root <root> \
  --threshold 0.82 --min-lines 4 --min-nodes 20 <paths>...
```

`--root` is the project root: dryer writes the `.metrics/dry.edn` snapshot
there. It prints a text report, closest match first, and exits 0 after a
report, 1 on a usage error, and 2 on an unknown `--format`.

Run it exactly as `tools/README.md` documents. This pack has no wrapper layer.

## Scope

Only the Python path is used. The Clojure, Java, Go, TypeScript, and Rust
paths are vendored but not exercised by the pack.
