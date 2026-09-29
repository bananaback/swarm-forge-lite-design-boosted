# contractor work — <task>

WORK: design/<task>/work/03-contractor.md
REV: 1

FROZEN (from modeler): <CRC_CARDS / SECRETS / CORE_SHELL_MAP / DEPENDENCY_GRAPH / STATE_MAP + FROZEN HANDOFF>

## 1. CONTRACTS — Design by Contract (Meyer, 1988) + Command-Query Separation

| Method (signature) | Precondition | Postcondition | Invariant | Command | Query |
|--------------------|--------------|---------------|-----------|---------|-------|
| | | | | | |

- Illegal-transition preconditions folded from STATE_MAP: <none / list>
- Methods split for mixing Command and Query: <none / list>

## 2. COLLABORATION WIRING — Tell, Don’t Ask + Law of Demeter (1988–89)

| Method | Objects touched beyond self/param/local | Decision moved onto its owner | Forwarding method added |
|--------|-----------------------------------------|-------------------------------|--------------------------|
| | | | |

- Any chain deeper than one dot remaining: <none / list + fix>

## 3. TEST MAP — Beck Rule 1, passes the tests

| test_<criterion> | Method(s) called | Acceptance check it serves | Signature exists? |
|------------------|------------------|----------------------------|-------------------|
| | | | |

## 4. SEAM — design ↔ business

- TEST_MAP expectations that contradict an approved feature: <none / contradiction + feature line>

## 5. DECISIONS — for the operator

| Dn | Rule | Question | Options | Operator answer |
|----|------|----------|---------|-----------------|
| | | | | |
