# DESIGN — <subsystem> · <module>

WORK: design/subsystems/<subsystem>/modules/<module>/

The design reasoning of this module. The contracts are in `SKELETON.md`. The decision
table is in `decisions.md`. Edit in place: no version, no status, no change log.

## 1. CONTRACTS - one home

The contracts live once in `SKELETON.md` §2: every method with its signature,
precondition, postcondition, invariant, and exactly one CQS tag. Do not copy the
table here. Record here only the judgments the table cannot carry:

- Illegal-transition preconditions folded from STATE_MAP: <none / list>
- Methods split for mixing Command and Query: <none / list>

## 2. COLLABORATION WIRING - Tell, Don't Ask + Law of Demeter (1988-89)

| Method | Objects touched beyond self/param/local | Decision moved onto its owner | Forwarding method added |
|--------|-----------------------------------------|-------------------------------|--------------------------|
| | | | |

## 3. TEST MAP - Beck Rule 1, passes the tests

| test_<criterion> | Method(s) called | Acceptance check it serves | Signature exists? |
|------------------|------------------|----------------------------|-------------------|
| | | | |

## 4. OCP SEAM

- TEST_MAP expectations that contradict an approved feature: <none / contradiction + feature line>
- Seams built now: <none / list>
- Seams left to YAGNI, with the reason: <none / list>

## 5. SUBSTITUTABILITY AND TRIM - LSP + ISP

| Interface | Implementers (this module) | Pre/post match exactly? | Methods removed (no real client) |
|---|---|---|---|
| | | | |

## 6. DUPLICATION AND MINIMALISM - Beck Rules 3 & 4

| Repeated policy | Where it repeats | Extracted to |
|---|---|---|
| | | |

| Class removed | Zero callers in TEST_MAP | Zero inbound edges | Kept because |
|---|---|---|---|
| | | | |

- Classes outside the caller closure of this module: <none / removed>

## 7. NAMING - Beck Rule 2, reveals intention

| Name | Read with its contract alone - what and why | Renamed from |
|---|---|---|
| | | |

## 8. FROZEN INTERFACES HONORED

- `interfaces/<module>.md`: <honored / CONFLICT: <interface path> - <the change needed> - <why>>
- `interfaces/<neighbor>.md` (when this module touches it): <honored / CONFLICT>
