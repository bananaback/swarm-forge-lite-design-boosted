# Install

Two ways to install this pack for a project. Both end at the same green
`doctor`. Part 1 is for an agent; Part 2 is for a human with no agent around.

---

## Part 1 — for an agent

You are installing the harness for one project. Do not guess a path, and do not
start work until `doctor` exits 0.

1. **Inspect.** Ask the operator for the project path, then run:

   ```sh
   python3 tools/install.py inspect --root <project-path>
   ```

   It writes `tmp/install-brief.md` and prints it. The brief lists every detected
   path with its certainty: `fact` (found), `guess` (derived), `missing` (a
   question).

2. **Ask once.** Send the operator **one** message: the detected root, the
   recommendation for each `guess`, and only the `missing` keys as questions.
   Attach the recommendation to every question. If a `missing` key cannot be
   answered, say what it would take to discover it — do not invent a value.

3. **Record the answers.** Write `install.json` with the skeleton from the brief,
   with the operator's answers filled in and the confirmed `name` and `root`.
   Keep the `design_root` only if the project repository accepts a new folder;
   otherwise use the pack-relative fallback the brief suggests.

4. **Dry run first**, then apply:

   ```sh
   python3 tools/install.py apply --answers install.json --dry-run
   python3 tools/install.py apply --answers install.json
   ```

   `apply` never prompts, never overwrites an existing design file, and adds the
   local config line to `.gitignore`.

5. **Prove it.**

   ```sh
   python3 tools/doctor.py --project <name>
   ```

   Report every `fail` row with its remedy, and the exit status. A warning is
   reported, not fixed.

6. **Hand over.** Tell the operator what was created, where the design folder is,
   and the one thing a human must still write: the project's environment record
   (`PROJECT.md`).

Never do these: guess a path; edit `config/pack.json` (the tracked legacy file);
overwrite an existing `design/` file; run `apply` without a dry run on a tree
that already has a config for another project.

---

## Part 2 — for a human

```sh
git clone <remote> swarm-forge-lite
cd swarm-forge-lite
python3 tools/install.py inspect --root ../myproject
```

Read the brief. Answer the `missing` rows by editing the skeleton, then:

```sh
python3 tools/install.py apply --answers install.json --dry-run
python3 tools/install.py apply --answers install.json
python3 tools/doctor.py --project <name>
```

What you should see: `ok` for the config, the project tree, the design folder,
every declared spec and the capabilities your gates need; `warn` for things that
do not block (an uncommitted harness, a missing optional policy); `fail` for a
path that does not exist.

Reading a failure: the row names the exact path and the key that produced it.
Fix the key in `config/pack.local.json` and run `doctor` again — it is safe to
repeat.

If you want the design folder inside the repository, keep `design_root`; if the
repository will not take new folders, set it to a pack-relative path and note
that the data then lives outside version control.
