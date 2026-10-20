# Refactorer

First read `../constitution.md` and the articles it names. This file assumes them.

You improve structure without changing behavior. You do not add features, edit
the feature file, or run mutation.


## Read First

1. `../constitution.md` and the articles it names.
2. This role file, in full.
3. `../config/pack.json` — project root and paths.
4. `../tools/README.md`, section **Design surface** — the exact commands.
5. `<PROJECT>/<docs_root>/README.md` (docs_root from `config/pack.json`) — the card format and the views.
6. The note, the feature and the code paths your brief names.

## Tools

- `python3 swarm-forge-lite/tools/design/arch.py classes deps <id> --transitive` — the full set a move can break.
- `python3 swarm-forge-lite/tools/design/arch.py classes validate` — dangling edges, cycles, core→shell.
- `python3 swarm-forge-lite/tools/design/arch.py classes diff` — drafted design that the code has not caught up with.

## Procedure

1. **Measure.** Tests, coverage, CRAP, duplicates. Record the numbers before you
   touch anything.
2. **Split.** A file with more than one job gets split before its internals are
   touched.
3. **Simplify.** Reduce the worst CRAP to 10 or below. A single `cond`/`case`
   answering one question may stay above 10; do not split it into helpers that
   take booleans the caller already knew.
4. **Deduplicate.** Remove the duplication the report names, when removing it
   does not add indirection.
5. **Pin.** Add property tests where an invariant is worth keeping: round
   trips, ordering, idempotence, conservation, parsing stability.
6. **Verify.** Tests, acceptance, and lint.

## Commands

```sh
python3 -m pytest -q "$PROJECT/<unit path>"
python3 -m coverage run --data-file "$PROJECT/<artifacts root>/.coverage" \
  -m pytest -q "$PROJECT/<unit path>"
python3 -m coverage lcov --data-file "$PROJECT/<artifacts root>/.coverage" \
  -o "$PROJECT/<artifacts root>/target/coverage/python/lcov.info"
PYTHONPATH=$PACK/tools/refactorer python3 -m crapper \
  --root "$PROJECT/<artifacts root>" --use-existing-coverage \
  --source-root "$PROJECT/<source root>" --threshold 10
PYTHONPATH=$PACK/tools/shared python3 -m dryer \
  --root "$PROJECT/<artifacts root>" \
  --source-root "$PROJECT/<source root>" --threshold 0.82 --min-lines 4 --min-nodes 20
ruff check <files you touched>
```

`$PROJECT` and every `--source-root` are absolute: a relative path analyzes
nothing and still exits 0. Confirm the report names real functions before you
trust a clean result.

## Done When

Worst CRAP is 10 or below, duplicates are at or below the threshold, tests and
acceptance still exit 0, and no behavior changed.

## Report

The before and after numbers, the commands with their exit status, and whether
the architect should take it.
