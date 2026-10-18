# Module Rules - the freeze, the parallel split, and the talk-back

The architect cuts a subsystem into **modules**. A module is a unit that one
designer can design alone. The **frozen interface** is the overlap between two
modules. It is the only thing two designers share.

## The module map

`architecture.md` holds one row for each module:

| Module | Owns (write set) | Provides | Requires | Secret |
|---|---|---|---|---|

- **Owns** - the paths this module writes. Two modules never share a path.
- **Provides** - the names this module exposes to other modules.
- **Requires** - the names it consumes from other modules.
- **Secret** - the one volatile decision it hides (Parnas).

## The freeze checklist

Freeze the interfaces only when all hold:

1. **Disjoint write sets.** No path is in two `Owns` columns.
2. **Acyclic.** The Provides/Requires graph has no cycle.
3. **One secret each.** Each module hides one decision.
4. **Caller closure.** Each module owns a closed set of classes.
5. **Every shared edge is frozen.** No cross-module call is left open.
6. **Two-way door.** A wrong interface is cheap to repair. When it is not, merge the two modules.

Also:

- **Walk the acceptance checks first.** Walk every accepted check across the map,
  card to card, before the freeze. A check that crosses a module with no frozen
  interface blocks the freeze.
- **Name the shared files.** When two modules must edit one file, name it in
  `ARCHITECTURE.md`. The orchestrator orders those edits. The two designers never
  write that file at the same time.

## The interface file

One **living** file for each module:
`design/subsystems/<subsystem>/interfaces/<module>.md`.

It holds the provides, the requires, the consumer list, and the shared-file note.
Edit it in place. There is no version, no status, and no change log. The latest
content is the whole truth.

```
INTERFACE <module> <-> <other module>
provides: <name> - <signature> - <meaning>
requires: <name> - <signature> - <meaning>
consumers: <module-a>, <module-b>
shared files (serialize): <path>
```

## Parallel dispatch

The orchestrator dispatches designers in parallel only when:

- the write sets are disjoint, and
- every shared edge is frozen.

Otherwise it serializes the affected modules.

## The talk-back

A designer that cannot honor a frozen interface stops. It never edits the frozen
zone. It reports a ONE-LINE REQUEST, so the answer costs one line and no design:

```
STATE: blocked
CONFLICT: <interface path>:<line> - <the new line> - <why>
```

- The request carries the EXACT proposed change: the `path:line`, the new line, and
  the why. A request with no exact line goes back to the designer.
- The architect answers ONE LINE and re-runs no design. The orchestrator sends the
  one change, not a new envelope.
- **AMEND** - edit `interfaces/<module>.md` in place. The orchestrator then
  re-dispatches every consumer named in the file.
- **REJECT** - give the reason. The designer conforms to the frozen interface.
- **REASSIGN** - move a path from one `Owns` column to another. The orchestrator
  updates `ARCHITECTURE.md`.

The consumer list bounds the re-dispatch. Only the named consumers run again.

A disagreement the CHECKER can settle never reaches a role. A count, a stale line
cite, and a mismatch between the record and a view are fixed by the tool: read the
finding, read the hint in the `check` row, and re-run the check.
