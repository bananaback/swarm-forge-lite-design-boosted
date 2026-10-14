## 3. STRUCTURE - core/shell, the dependency graph, and the state map

### 3a. CORE / SHELL - functional core, imperative shell

| Class | Responsibility | I/O or PURE | Core or Shell |
|-------|----------------|-------------|---------------|
| | | | |

### 3b. DEPENDENCY GRAPH + INVERSION - DIP

| From | To | Core -> Shell? | Inverted? | Core-owned interface (Core vocabulary) |
|------|----|---------------|-----------|----------------------------------------|
| | | | | |

- Acyclic: <yes / cycle list + extraction>
- Remaining Shell cycle extractions: <none / ...>

### 3c. STATE MAP - ordering ownership

| Owner | Current state | Event | Next state | Legal? | Precondition recorded for the designer |
|-------|---------------|-------|------------|--------|--------------------------------------|
| | | | | | |
