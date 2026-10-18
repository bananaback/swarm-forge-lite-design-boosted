# Design procedure

1. **Interrogate.** Resolve the requirement document. Frame the world, the
   client, success, constraints, exclusions, and the measurable requirements.
   Scope gate: use cases, scale, out of scope. Answer every DECISION.
2. **Specify.** Inspect the record as a second party. Write one Gherkin scenario
   for each requirement. Parse and dry-check it.
3. **Architect.** Cut modules. Freeze the interfaces. Draw `model.json`.
   Render `model.html` for operator review. Answer the freeze checklist.
4. **Design.** One designer per module, in parallel when writes are disjoint.
   Write the contract: signature, pre, post, invariant, CQS, responsibility.
   Add the test map and the decisions.
5. **Critique.** Read the union. Check substitutability, deduplication, naming,
   OCP seams, and the caller closure. Write the short review. Generate `SKELETON.md`.
6. **Build.** Coder implements one accepted chunk with TDD. Test-reviewer accepts
   or rejects the tests. Refactorer runs the terminal gate.

Position in the pipeline: interrogator -> specifier -> architect -> designers ->
critic -> coder -> test-reviewer -> refactorer.

The operator reviews `model.html`, the spec document, the feature, and the test
result. The record is working state, not a deliverable.
