# Agent instructions

Read and obey `swarm-forge-lite/constitution.md`, then your role in `.opencode/agents/`.
The constitution points at the protocol in `swarm-forge-lite/protocol/`.
To wire the harness to a project (or back to itself), follow
`swarm-forge-lite/WIRING.md`.

Do not test the text of prompts with an automated unit or acceptance test. That
includes the constitution, role prompts, and generated instruction files. Prompt
wording is not production behavior to pin with `str/includes?`, Gherkin, or any
other automated check.
