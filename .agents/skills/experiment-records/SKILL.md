---
name: experiment-records
description: Plan, record, compare, and retrieve RAG experiment evidence for this repository and turn supported findings into thesis material. Use for experiment work or questions about past results, not routine code edits.
---

# Experiment records

Work from the repository root. The maintained protocol is in
[experiments/WORKFLOW.md](../../../experiments/WORKFLOW.md); read the relevant
section when creating records, evaluating comparability, or preparing thesis claims.

## Find the minimum useful context

1. Read [experiments/README.md](../../../experiments/README.md). It contains the
   current research handoff and an experiment index, not the complete history.
2. For a result question, open the named experiment's `findings.md`; for new
   work, open its `plan.md`. For thesis writing, first select relevant claim IDs
   in [experiments/claims.md](../../../experiments/claims.md).
3. Verify a consequential conclusion against the referenced run's `record.md`,
   configuration, manifest, and metrics. A summary is navigation, not proof.
4. Open raw artifacts only to resolve a specific question. Select run IDs,
   question IDs, JSON fields, or a bounded sample with a script or targeted `rg`.
   Do not dump all JSONL, recursive Markdown, logs, chat history, or Git history.

Default initial reading budget: this skill, the index, and one experiment summary
(roughly 2,000 words combined). This is a routing target, not a hard accuracy cap:
expand when the question spans experiments or evidence disagrees. State what is
missing rather than reconstructing measurements from plans or model memory.

## Record work at the right level

- New experiment: copy only the needed [plan template](../../../experiments/templates/plan.md),
  choose a stable E/S ID consistent with the project checklist, predefine the
  comparison, split, metric, and stopping budget. Do not create a full grid of
  folders for speculative model combinations.
- Run: follow the workflow's run-record section and use its
  [run template](../../../experiments/templates/record.md). Preserve actual
  commands, effective settings, versions, and data fingerprints. The current
  evaluator does not automatically create the whole evidence package.
- Result: verify artifacts before writing
  [findings](../../../experiments/templates/findings.md). Include failures,
  uncertainty, and alternative explanations. Never substitute zero for missing
  data or describe a smoke test as a final experiment.
- Handoff: replace the short current-focus/next-step text and update the affected
  index row. Put decisions with their evidence in the experiment's findings.
  Avoid a growing session diary or duplicate project-wide memory files.
- Thesis: connect each empirical claim to exact run IDs and metric fields;
  preserve dataset/split scope and review status. Check sources before drafting.
  Literature claims need bibliographic sources, not an experiment run citation.

## Keep evidence and coordination separate

Plane holds task status; Git holds research evidence and interpretation. When
Plane updates are in scope and available, update the existing linked task with
a short conclusion and a Git commit permalink. Otherwise record a pending sync
in the handoff and finish local work. Do not create duplicate tasks or export the
whole workspace to recover experiment history.

Before publishing, check explicit staged paths and artifact sizes. Keep raw
outputs, credentials, model weights, indexes, and personal data out of Git.
Preserve completed run artifacts; corrected execution or rescoring gets a new
run ID with a supersedes/source link. Commit and push when authorized by the
user; this skill itself does not authorize remote changes or paid runs.
