# E00: establish the FIIT retrieval baseline

Status: planned; no measurement registered in this notebook.
Task: [BACHE-8](https://app.plane.so/bachelors-project/browse/BACHE-8/).
Protocol: [experiment plan](../../docs/plan_experimentov.md), sections 10-12.

## Question

How well does the current Qwen retrieval cover known evidence on the FIIT dev
split, and which failures should guide the next controlled comparisons?
This is a descriptive baseline, not a claim of improvement over another model.

## Fixed starting comparison

- One configuration: existing block-aware/token-aware pipeline,
  `Qwen/Qwen3-Embedding-0.6B`, exact dense search, top 5 unique parent chunks.
  Capture actual effective settings and revisions before running.
- Dataset: versioned FIIT QA dev, expected 30 questions, including 25 answerable.
  Verify actual counts and fingerprint the split and all evidence inputs.
- Primary measure: `complete_support@5`; also record `mrr@5`, known-evidence hit,
  evidence coverage, and the precise denominator of each reported metric.
- Record missing predictions and inspect actual retrieved text, not only parent
  IDs. More than five child hits may be needed to obtain five unique parents.
- Hardware/environment and timing method: record the actual machine; latency is
  descriptive until warm-up and repetition policy are fixed. No parameter sweep.
- Budget: validate inputs, perform a small smoke check, then one full dev export
  and scoring pass. Stop on validation failure or incomplete evidence mapping;
  record a failed run and diagnose before another execution. No paid API calls.
- Do not use the test split for this baseline development step.

## Evidence and completion

Use the [recording workflow](../WORKFLOW.md). The dataset validator and retrieval
scorer already exist; verify their CLI and prediction schema before execution.
A full prediction export and reproducibility package still need to be prepared.
Choose and verify a backup location before calling the evidence safely archived.

Complete when the dev export is scored, provenance and artifacts are recorded,
representative errors are inspected, and findings state the review limitations.
FIIT annotations are assistant-curated, with evidence from a small source set;
independent expert review is still pending. These results cannot establish the
quality of the full conversational or cross-institution system.
