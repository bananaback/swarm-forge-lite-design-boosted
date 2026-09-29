# modeler work — <task>

WORK: design/<task>/work/02-modeler.md
REV: 1

FROZEN (from interrogator): <GOAL / CONSTRAINTS / EXCLUSIONS + FROZEN HANDOFF>

## 1. GRAMMAR — Abbott noun-verb analysis (1983)

| Noun / noun-phrase (candidate class or attribute) | Verb (verb — subject: noun) | Adjective (attribute or subtype) | Relationship (prepositional phrase) | Alias discarded |
|----------------------------------------------------|-----------------------------|----------------------------------|-------------------------------------|-----------------|
| | | | | |

Pass 2 added: <entries or "none — decomposition stable">

## 2. CROSS-CUTTING VERBS — one owning card each

| Verb (validate / persist / log / retry / notify) | Owning card | Other occurrences (delegation) |
|--------------------------------------------------|-------------|-------------------------------|
| | | |

## 3. CRC CARDS — Beck & Cunningham (1989)

| Class | Responsibility | Collaborator |
|-------|----------------|--------------|
| | | |

### 3a. WALKTHROUGH — one row per acceptance check

| Acceptance check | Path (card → card → …) | Unowned step → new card created |
|------------------|------------------------|---------------------------------|
| | | |

## 4. SECRETS — Parnas, information hiding (1972)

| Class | The one thing most likely to change | Merge / Split action |
|-------|-------------------------------------|----------------------|
| | | |

## 5. CORE / SHELL — functional core, imperative shell

| Class | Responsibility | I/O or PURE | Core or Shell |
|-------|----------------|-------------|---------------|
| | | | |

## 6. DEPENDENCY GRAPH + INVERSION — DIP

| From | To | Core → Shell? | Inverted? | Core-owned interface (Core vocabulary) |
|------|----|---------------|-----------|----------------------------------------|
| | | | | |

- Acyclic: <yes / cycle list + extraction>
- Remaining Shell cycle extractions: <none / …>

## 7. SRP — one reason to change

| Class | “This class changes only if ___ changes.” | Contains “and”? |
|-------|-------------------------------------------|-----------------|
| | | |

## 8. STATE MAP — ordering ownership

| Owner | Current state | Event | Next state | Legal? | Precondition recorded for contractor |
|-------|---------------|-------|------------|--------|--------------------------------------|
| | | | | | |

## 9. DECISIONS — for the operator

| Dn | Rule | Question | Options | Operator answer |
|----|------|----------|---------|-----------------|
| | | | | |

## 10. Visual

- Rendered model: `<task>/model.json` → `<task>/model.html` (run `umlview render.py`). The
  model is the source; the HTML is a view. Record `--check` findings here.
- Findings not fixed (with reason):
