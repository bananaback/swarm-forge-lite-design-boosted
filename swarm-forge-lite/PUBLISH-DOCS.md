# Publish the docs into the project repo

Point an agent at this file to refresh the repo's read-only design archive and the
tests README metrics. Do the two passes in order. Do not commit until the operator
asks.

Two directories are named below. Set them once, from `harness.json`:

- `DOCS` - the project's docs directory. It holds `specs/`, the requirements
  workplace, and `design-archive/`, the read-only archive. `specs` in
  `harness.json` is `DOCS/specs`.
- `TESTS` - the persistent test root. `persistent_tests` in `harness.json` names
  it.

## 1. The rules: workplace or archive

Read this table first. Most mistakes come from it.

| Path | Kind | Who writes |
|---|---|---|
| `DOCS/specs/` | **workplace** | requirements are written here |
| `DOCS/design-archive/` | **read-only archive** | nobody - copies only |
| `swarm-forge-lite/design/` (outside the repo) | **the design workplace** | the design team, and only it |

- Never write design into the repo. The design lives in `swarm-forge-lite/design/`.
- Only `model.html` leaves the design workplace.
- Never work in `DOCS/design-archive/`. It holds snapshots only.
- A snapshot can lag its source. Never edit it in place. The next publish replaces it whole.
- `DOCS/specs/` is the exception. That is where the requirements are written.

## 2. What is published

| From | To |
|---|---|
| `swarm-forge-lite/design/subsystems/<subsystem>/model.html` | `DOCS/design-archive/<subsystem>/model.html` |

`model.html` is the only published file. It is one HTML file that loads Tailwind
and jQuery from two pinned CDN URLs, so opening it needs the network. A reader of
`DOCS/design-archive/<subsystem>/model.html` in the project repository has the same
requirement. It has no absolute path and no role or process text. Render it with
`--public`. That flag drops the LIVE badge, the source-sync status, and every pack
path. It keeps the diagram: the signatures, the `cqs`/contracts, the
`responsibility`/`secret`, the CRAP/coverage metrics, and the method source.

## 3. What is never published

- `design/subsystems/<subsystem>/**` - role names, stop tests, decisions.
- `model.json` and every other `*.json` - machine projections.
- `design/templates/`, and everything under `dump/` or `hot_tests/`.

If a repo reader can tell who or what made the design, do not publish it.

## 4. Before you start

Run every command from the workspace root. The root holds `swarm-forge-lite/` and
the project.

The publish is serial and it is the operator's action. Two publishers overwrite
each other, because the procedure rewrites `DOCS/README.md` and
`DOCS/design-archive/README.md` whole.

Stop if another session is working. The archive is a snapshot of settled work.
The operator coordinates this; there is no registry to query.

## 5. Publish the design archive

Copy this block as-is. Set `DOCS` first.

```bash
# run from the workspace root that holds swarm-forge-lite/ and the project
PACK=swarm-forge-lite
DOCS=<the project's docs directory>    # the parent of specs/

# 0. prune. The archive holds one directory per CURRENT subsystem, and nothing
#    else. Remove any directory that is not one: a stale per-task fragment
#    (for example `safety-rule-engine-seen-window`). The publish replaces the
#    archive whole, so a stale directory must not survive it.
for dir in "$DOCS"/design-archive/*/; do
  task=$(basename "$dir")
  [ -d "$PACK/design/subsystems/$task" ] || { echo "prune: $task"; rm -rf "$dir"; }
done

# 1. each subsystem's class model. `templates/` is not a subsystem.
#    Render fresh with --public: prefer the live overlay, and strip the LIVE badge,
#    the source-sync status and any pack path, so the archive shows the diagram
#    (signatures, CRAP/coverage, method source) without how it was made.
for src in "$PACK"/design/subsystems/*/; do
  task=$(basename "$src")
  model="$src/model.live.json"
  [ -f "$model" ] || model="$src/model.json"
  if [ -f "$model" ]; then
    mkdir -p "$DOCS/design-archive/$task"
    python3 "$PACK/tools/shared/umlview/render.py" "$model" --public \
      --out "$DOCS/design-archive/$task/model.html"
  else
    echo "note: $task has no model yet"
  fi
done

# 2. the signposts. Both live inside the repo, so keep them neutral: no name,
#    nothing that points back at the design workplace.
cat > "$DOCS/README.md" <<'EOF'
# Design notes

`docs/specs/` is the **workplace**: the requirements are authored and updated
here. Only `docs/design-archive/` is read-only.

- `specs/` - the requirements. This is where they are written and updated.
- `design-archive/<subsystem>/model.html` - the archived class model for that subsystem.
  **Read-only.** These are snapshots, not sources: never edit them in place,
  never treat this directory as a workplace, and expect them to be replaced
  wholesale when the archive is next published. There is no design workplace in
  this repo.
EOF

cat > "$DOCS/design-archive/README.md" <<'EOF'
# READ-ONLY archive

Archived class models, one directory per feature. These are snapshots, not
sources: never edit them, never treat this directory as a workplace, and expect
them to be replaced wholesale when the archive is next published.
EOF
```

The loop writes a page that loads two libraries from the CDN, so the diagram
needs the network to open. Both URLs are pinned:
`https://cdn.tailwindcss.com/3.4.16` (Tailwind) and
`https://code.jquery.com/jquery-3.7.1.min.js` (jQuery).

Then run the verify block (section 7).

A fresh render can be byte-identical to the committed file. Then the archive is
already current. That is normal. Check it with
`git -C "$DOCS/.." diff --stat -- docs`.

## 6. Refresh the tests README

Do this pass in the same run. The file `TESTS/README.md` opens with the suite metrics:
the layer counts, the line coverage over the source root, and the CRAP line. Refresh all
three. Run every command below from the tests root.

### 6.1 Layer counts

```bash
cd <TESTS>

# unit and property: files and tests
python3 -m pytest --collect-only -q | python3 -c '
import sys, collections
files = collections.defaultdict(set)
tests = collections.Counter()
for line in sys.stdin:
    if line.startswith(("unit/", "property/")):
        path = line.split("::")[0]
        layer = path.split("/")[0]
        files[layer].add(path)
        tests[layer] += 1
for layer in ("unit", "property"):
    print(f"{layer}: {len(files[layer])} files, {tests[layer]} tests")
'

# features: file count, then scenario count
ls features/*.feature | wc -l
grep -hcE '^[[:space:]]*(Scenario|Scenario Outline):' features/*.feature | awk '{s+=$1} END {print s}'

# step handlers: every .py under acceptance/steps/, at any depth, except __init__.py
find acceptance/steps -name '*.py' ! -name '__init__.py' | wc -l

# acceptance: the count and the green or red result
python3 acceptance/run_acceptance.py
```

The acceptance row holds the feature-subsystem count and the `N passed` count.

### 6.2 Coverage and the CRAP line

`crapper` is the vendored pack tool. It is not on `PATH`. Run it with `python3`,
from the tests root, with the pack's `refactorer` tree on `PYTHONPATH`. First run
the suite under `coverage` and write the report under the pack's `dump`, then run
`crapper` over that report:

```bash
ROOT=<the pack>/dump
SRC=<the source root>
DATA=$ROOT/target/coverage/python/.coverage
python3 -m coverage run --data-file=$DATA -m pytest -p no:cacheprovider
python3 -m coverage lcov --data-file=$DATA -o $ROOT/target/coverage/python/lcov.info
PYTHONPATH=<the pack>/tools/refactorer python3 -m crapper \
  --root $ROOT --source-root "$SRC" --threshold 10 --use-existing-coverage
```

`crapper` reads the report under `--root`, writes `$ROOT/.metrics/crap.edn`, and
prints the function table: each function's complexity, coverage, and CRAP score.
Count the rows whose CRAP is above 10. That count is the CRAP line. The pack keeps
the CRAP 10 threshold, so the tool exits 2 when the worst score is above 10.

The report does not print per-module coverage. Read that coverage from the LCOV
file, for the source root as a whole and for each module directory under it:

```bash
python3 - <the pack>/dump/target/coverage/python/lcov.info <<'PY'
import sys

# The project's source root, as a fragment of the report's paths. It is not a
# prefix: read one SF: line and pick the segment that every source file shares.
# Run the block once, read the message, and set it. A wrong fragment stops the
# block. It never prints 0.0%.
SEGMENT = "/src/"

found, hit, cur = {}, {}, None
for line in open(sys.argv[1]):
    line = line.rstrip()
    if line.startswith("SF:"):
        cur = line[3:]
        found[cur] = 0
        hit[cur] = 0
    elif line.startswith("DA:") and cur:
        _n, h = line[3:].split(",", 1)
        found[cur] += 1
        if int(h) > 0:
            hit[cur] += 1
root = [f for f in found if SEGMENT in f]
lf = sum(found[f] for f in root)
lh = sum(hit[f] for f in root)
if not lf:
    sys.exit(f"no file in the report matches {SEGMENT!r}. Set SEGMENT to the source root.")
print(f"source root: {lh} / {lf} = {100*lh/lf:.1f}%  ({len(root)} files)")
PY
```

The pack's `swarm.crap` tool runs these steps for you. It adds
`--use-existing-coverage` with `reuseFresh:true` when the report is newer than
every source and test file.

When another task is active, wrap each command in the lane wrapper:
`swarm-forge-lite/tools/shared/lane <subsystem> <command...>`.

### 6.3 Write the numbers

Fill the README tables with the fresh numbers. Then update the header line:

```
Measured <YYYY-MM-DD> on branch `<branch>` at commit `<sha>`.
```

- `<YYYY-MM-DD>` is today.
- `<branch>` is `git rev-parse --abbrev-ref HEAD`.
- `<sha>` is `git rev-parse --short HEAD`, read before you commit.

Report any regression to the operator, for example a rise in the CRAP count.

## 7. Verify

```bash
DOCS=<the project's docs directory>
find "$DOCS" -name '*.json' -print                              # expect no output
find "$DOCS" \( -name '01-interrogator' -o -name '02-architect' -o -name '04-critic' \
  -o -name interfaces -o -name modules -o -name work \) -print   # expect no output
grep -rlE "swarm-forge-lite|dump/|\.\./" "$DOCS" \
  || echo "clean: no internal path leaked"
find "$DOCS" -type f | sort
```

## 8. Report and hand off

- The publisher does not commit and does not push. Report the changed files to the
  operator. Let the operator commit and push.
- Suggested commit message: `docs: publish the read-only design archive`. When you
  also refreshed the tests README, use
  `docs: publish the read-only design archive and refresh the tests README`.
- If a run prints `note: <subsystem> has no model yet`, that design is mid-flight.
  Leave it. Publish again after it settles.
