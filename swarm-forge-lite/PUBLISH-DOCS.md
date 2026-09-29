# Publish the docs into the project repo

Point an agent at this file when you want the repo's read-only design archive
refreshed. It publishes each feature's class model into the project repo so it
ships with the code.

## Placeholders

Two paths below are placeholders. Set them from `harness.json` before running —
never hardcode them:

| Placeholder | Meaning |
|---|---|
| `<WORKSPACE_ROOT>` | The directory that contains the pack (`swarm-forge-lite/`) — the `WORKSPACE` row of `harness status`. |
| `<PROJECT_REPO>` | The wired project's repository root, relative to `<WORKSPACE_ROOT>` — the tree that holds `docs/specs/` and `docs/design-archive/`. |

## Which folder is a workplace — and which is not

This is the rule that keeps getting misread. Read it before touching anything:

| Path | Kind | Who writes there |
|---|---|---|
| `<PROJECT_REPO>/docs/specs/` | **workplace** | requirements are authored and updated **here** |
| `<PROJECT_REPO>/docs/design-archive/` | **read-only archive** | nobody — copies only, published by this file |
| `swarm-forge-lite/design/` (outside the repo) | **the design workplace** | the design team, and only it |

- **Never write design into the repo.** There is no design workplace in the repo;
  the design lives in `swarm-forge-lite/design/`, outside the repo, and only its
  `model.html` is ever published.
- **Never treat `docs/design-archive/` as a place to work.** Nothing there is
  authored in place; it holds snapshots only.
- A file under `docs/design-archive/` is a **snapshot**: it may lag its source, it
  is never edited in place, and it is replaced wholesale on the next publish.
  `docs/specs/` is the exception — that is where the requirements are written.

## What is published

| From | To |
|---|---|
| `swarm-forge-lite/design/<task>/model.html` | `<PROJECT_REPO>/docs/design-archive/<task>/model.html` |

`model.html` is the only file taken from the design workplace: a standalone
class diagram (no external references, no absolute paths, no role or revision
text). Its field labels are `responsibility`, `secret` and `cqs` — plain design
vocabulary, nothing about how it was made.

## Never published

- `design/<task>/BLUEPRINT.md` — names roles, revisions, stop tests, decisions.
- `design/<task>/work/**` — the working records.
- `model.json`, and any other `*.json` — machine projections.
- `design/templates/`, and anything under `dump/` or `hot_tests/`.

If a reader of the repo could tell who — or what — produced the design, it does
not get published.

## Procedure

Run from the workspace root. Copy this block as-is, setting the two placeholders
first.

```bash
cd <WORKSPACE_ROOT>
PACK=swarm-forge-lite
REPO=<PROJECT_REPO>

# 1. each feature's class model (templates/ is not a feature)
for src in "$PACK"/design/*/; do
  task=$(basename "$src")
  if [ "$task" = templates ]; then continue; fi
  if [ -f "$src/model.html" ]; then
    mkdir -p "$REPO/docs/design-archive/$task"
    cp "$src/model.html" "$REPO/docs/design-archive/$task/model.html"
  else
    echo "note: $task has no model.html yet"
  fi
done

# 2. the signposts. Both live inside the repo, so keep them neutral: no name,
#    nothing that points back at the design workplace.
cat > "$REPO/docs/README.md" <<'EOF'
# Design notes

`docs/specs/` is the **workplace**: the requirements are authored and updated
here. Only `docs/design-archive/` is read-only.

- `specs/` — the requirements. This is where they are written and updated.
- `design-archive/<task>/model.html` — the archived class model for that feature.
  **Read-only.** These are snapshots, not sources: never edit them in place,
  never treat this directory as a workplace, and expect them to be replaced
  wholesale when the archive is next published. There is no design workplace in
  this repo.
EOF

cat > "$REPO/docs/design-archive/README.md" <<'EOF'
# READ-ONLY archive

Archived class models, one directory per feature. These are snapshots, not
sources: never edit them, never treat this directory as a workplace, and expect
them to be replaced wholesale when the archive is next published.
EOF

# 3. verify
find "$REPO/docs" -name '*.json' -print                          # expect nothing
find "$REPO/docs" \( -name 'BLUEPRINT.md' -o -name 'work' \) -print   # expect nothing
grep -rl "swarm-forge-lite" "$REPO/docs" || echo "clean: no internal path leaked"
find "$REPO/docs" -type f | sort
```

## After a publish

- Report what changed and let the operator commit. Suggested message:
  `docs: publish the read-only design archive`.
- If it prints `note: <task> has no model.html yet`, that design is mid-flight —
  leave it and re-publish once it settles.
