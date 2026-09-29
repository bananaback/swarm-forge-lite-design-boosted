# INSTALL — bring this pack up on a new machine

**What "done" means:** every tool below is present and importable, `harness status`
resolves, and the pack's own tests and acceptance pipeline pass. **Wiring to a
project is not part of installing the pack** — see *Wiring*; it happens only when
the operator asks.

---

## Order of operations

1. Check what is already installed (see *Check first*). Do not reinstall what is present and correct.
2. Install what is missing (see *Install the missing tools*).
3. Verify the install (see *Verify the install*) — `harness status`, the unit/property suite, the acceptance pipeline.
4. Done. The pack **self-hosts** and works as-is. Wiring it to a project is
   optional and happens only when the operator asks (see *Wiring*).

---

## Requirements and pinned versions

Known-good set, measured on the authoring machine:

| Tool | Version | Kind | Used by |
|---|---|---|---|
| Python | **3.12.12** | runtime | everything |
| pytest | **9.1.1** | pip | every test root, the acceptance runner |
| hypothesis | **6.168.1** | pip | the property test roots |
| radon | **6.0.1** | pip | `crap4py` cyclomatic complexity |
| coverage | **7.15.4** | pip | `crap4py` line coverage (LCOV) |
| ruff | **0.16.9** | pip | `ruff4py` lint |
| jscpd | **5.0.14** | npm (global) | `dry4py` duplicate detection |
| Node.js | **24.15.0** | runtime | jscpd |
| npm | **11.14.0** | runtime | jscpd |
| babashka (`bb`) | **1.13.219** | standalone | Gherkin parser + IR dry-checker |
| git | **2.43.0** | system | operator-owned commits |

`radon`, `coverage`, `ruff` and `jscpd` are **shelled out to by the pack's wrappers** —
installing the package/CLI is what matters; never call them directly (see *Wiring*).

---

## Check first

Run this from the **workspace root** (the directory containing `swarm-forge-lite/`).
It changes nothing.

```bash
python3 --version
for t in git node npm pytest coverage ruff radon bb jscpd; do
  printf '%-10s ' "$t"
  command -v "$t" >/dev/null 2>&1 && "$t" --version 2>&1 | head -1 || echo 'MISSING'
done
python3 - <<'PY'
import importlib.util as u
for m in ("pytest", "hypothesis", "radon", "coverage"):
    print(f"{m:<12}", "importable" if u.find_spec(m) else "MISSING")
PY
```

Read the output against *Requirements and pinned versions*:

- **Present and matching** → skip it.
- **`MISSING`** → install it (see *Install the missing tools*).
- **Present but a different version** → leave it, but say so in your report. Only
  reinstall if a verification step in *Verify the install* actually fails. Do not
  downgrade a working system without the operator's consent.

---

## Install the missing tools

Python packages (pin all five together — they are one verified set):

```bash
python3 -m pip install \
  'pytest==9.1.1' \
  'hypothesis==6.168.1' \
  'radon==6.0.1' \
  'coverage==7.15.4' \
  'ruff==0.16.9'
```

Add `--break-system-packages` only if pip demands it.

jscpd (global npm):

```bash
npm install -g 'jscpd@5.0.14'
```

babashka — needed by `<pack>/tools/shared/gherkin-parser` and
`<pack>/tools/specifier/ir-dry-checker`, which `exec bb`. Without it, parsing and
IR dry-checks cannot run; the acceptance pipeline degrades. Install it either way:

```bash
# option 1: Homebrew
brew install borkdude/brew/babashka

# option 2: upstream installer
curl -sLO https://raw.githubusercontent.com/babashka/babashka/master/install
chmod +x install && ./install
```

git: install from the OS package manager if absent (`apt install git`, `brew install git`).

---

## Verify the install

Run from the workspace root, in order.

```bash
# 1. Every configured path resolves. Expect every row [ok].
#    "SPECS [-] (none)" is correct while self-hosting: there is no requirements
#    workplace until the pack is wired.
python3 swarm-forge-lite/tools/shared/harness.py status

# 2. Clean the disposable areas before a first run.
python3 swarm-forge-lite/tools/shared/harness.py clean all

# 3. The pack's own unit + property suite. Expect: 94 passed.
cd swarm-forge-lite/harness_tests/persistent && python3 -m pytest -q && cd -

# 4. The acceptance pipeline: parse -> dry -> generate -> run. Expect: 86 passed, exit 0.
python3 swarm-forge-lite/harness_tests/persistent/acceptance/run_acceptance.py

# 5. Leave the box clean again (step 4 wrote into dump/ and hot_tests/).
python3 swarm-forge-lite/tools/shared/harness.py clean all
```

Step 4 is the real proof: it exercises the Gherkin parser, the dry-checker, the
generator, and the runner end to end. If `bb` is missing, expect parse/dry failures
here — go back to *Install the missing tools*.

If a test count differs from the numbers above, the pack has changed since it was
packed: report the actual counts rather than forcing them.

---

## Wiring — only if the operator asks

**Do not wire this pack on your own.** It arrives **self-hosting**: `harness.json`
sets `workspace_root: ".."`, `source_roots: ["tools"]`, and both persistent roots
point inside the pack. That is its shipped state, and it works as-is.

Wiring — pointing the pack at a real project — is a separate job you take on only
when the operator asks for it. When they do, `swarm-forge-lite/WIRING.md` is the
runbook and `harness.json` is the single source of truth.

Two standing rules from the constitution that apply to everything above:

- **Wrappers only.** Never call `ruff`, `radon`, `jscpd`, or `coverage` directly. Use
  `<pack>/tools/shared/ruff4py`, `<pack>/tools/refactorer/crap4py`,
  `<pack>/tools/shared/dry4py`.
- **Paths come from `harness.json`.** Never hardcode one.

---

## Report back

Tell the operator, briefly:

| Item | Value |
|---|---|
| Tools installed | e.g. `pytest 9.1.1`, `jscpd 5.0.14`, `bb 1.13.219` |
| Tools already present at a different version | name + version, and whether the verification passed |
| `harness status` | all `[ok]`, or the exact non-`[ok]` row |
| Unit + property suite | pass/fail with the count |
| Acceptance pipeline | pass/fail with the count |
| Wiring | untouched (self-hosting), unless the operator asked for it |

Anything you could not install or resolve: name it exactly and stop rather than
improvise a workaround.
