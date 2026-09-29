# critic work — <task>

WORK: design/<task>/work/04-critic.md
REV: 1

FROZEN (from contractor): <CONTRACTS / TEST_MAP + FROZEN HANDOFF>

## 1. EXTENSION REHEARSAL — OCP

| Xn tried | New class or body edit? | Seam proposed | YAGNI reason (if not seaming) |
|----------|-------------------------|---------------|-------------------------------|
| | | | |

## 2. SUBSTITUTABILITY — LSP

| Interface | Implementers | Pre/Post match exactly? | Violation (thrown “not supported”, ignored param) |
|-----------|--------------|-------------------------|---------------------------------------------------|
| | | | |

## 3. INTERFACE TRIM — ISP

| Interface | Methods | Client(s) needing each | Trim to |
|-----------|---------|------------------------|---------|
| | | | |

## 4. DEDUP — Beck Rule 3

| Repeated policy | Appears in | Extracted to one place |
|-----------------|------------|------------------------|
| | | |

## 5. MINIMALISM — Beck Rule 4, caller closure

| Class / interface | Callers in TEST_MAP | Inbound edges (transitive closure) | Keep / Delete |
|-------------------|---------------------|------------------------------------|---------------|
| | | | |

## 6. NAMING — Beck Rule 2, reveals intention

| Old name | Read with contract only: obvious? | New name |
|----------|-----------------------------------|----------|
| | | |

## 7. SKELETON — final, accepted

- Classes: <list>
- Interfaces (Core-owned): <list>
- Methods: name · contract (pre/post/invariant) · CQS tag · responsibility sentence
- Dependency graph: <edges / interfaces>
- State map: <owner · legal transitions>
- Test map: <test name · method(s)>

Projected on accept into `design/<task>/SKELETON.md`, self-contained — the coder's and the
refactorer's whole brief. They never open `BLUEPRINT.md`.

## 8. DECISIONS — for the operator

| Dn | Rule | Question | Options | Operator answer |
|----|------|----------|---------|-----------------|
| | | | | |

## 9. Visual gate

- `umlview render.py <task>/model.json --check` result: <clean | findings + justification>
- Final view: `<task>/model.html`.
