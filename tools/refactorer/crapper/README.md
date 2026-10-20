# crapper (vendored)

CRAP scores for Clojure, Java, Go, TypeScript, Rust, and Python. The pack runs
the Python path: it turns each Python function into a complexity and a coverage
score, `CRAP = CC^2 * (1 - coverage)^3 + CC`.

## Provenance

Vendored unmodified from [`unclebob/crapper`](https://github.com/unclebob/crapper)
at version 0.1.0 (commit `master`), licence 0BSD. The `LICENSE` file beside this
note is upstream's. Every `*.py` file is byte-identical to upstream `src/crapper`.
The pack does not pip-install the tool and does not point at an upstream
checkout.

Upstream runtime dependencies: `tree-sitter` and `tree-sitter-language-pack`;
`requires-python >= 3.11`.

## Run

The package is importable when `<pack>/tools/refactorer` is on `PYTHONPATH`, so
the entry point is `python3 -m crapper`:

```bash
PYTHONPATH=<pack>/tools/refactorer python3 -m crapper --root <root> \
  --source-root <source> --threshold 10
```

`--root` is the project root: crapper writes the `.metrics/crap.edn` snapshot
there and reads coverage reports from `target/coverage/**` and `coverage/**`
under it. `--threshold 10` is the pack's CRAP ceiling; the tool exits 2 when the
worst score is above it. A function the coverage report does not mention scores
0%.

Run it exactly as `tools/README.md` documents. This pack has no wrapper layer.

## Scope

Only the Python path is used. The Clojure, Java, Go, TypeScript, and Rust paths
are vendored but not exercised by the pack.
