# Experiment notebook

Read this page first to find evidence without loading the research archive.
Plane owns task status; this notebook owns experiment records and findings.
The [workflow](WORKFLOW.md) defines how to add evidence, and
[claims](claims.md) connects reviewed findings to the thesis.

## Current handoff

Updated: 2026-10-15. This notebook has just been established. **No measured run
has been registered here yet**; this does not assert that older local outputs
do not exist. Import any older result only after verifying its provenance.

- Focus: [E00 baseline plan](E00_baseline/plan.md).
- Next action: validate and fingerprint the FIIT corpus, chunks, and QA split;
  prepare a complete dev prediction export and record the baseline measurement.
- Limits: FIIT annotations still need independent review. The full experiment
  runner and automatic evidence export are planned, not implemented by this notebook.
- Wider scope: [assignment](../docs/project_scope.md),
  [technical experiment plan](../docs/plan_experimentov.md),
  [Plane task map](../docs/project_checklist.md).

## Evidence index

| ID | Question | Evidence maturity | Record | Current conclusion |
| --- | --- | --- | --- | --- |
| E00 | How does the current Qwen retrieval perform on FIIT dev? | planned | [Plan](E00_baseline/plan.md) | No registered measurement. |

Create another row when an experiment is actually prepared. E01-E09 and S00-S05
are specified in the task map; empty directories are unnecessary. Evidence
maturity is `planned`, `recorded`, `reviewed`, or `invalidated`, independent of
Plane task status. `Reviewed` requires a named review and date in the findings;
it does not imply independent expert review unless that happened.

Keep this page around 100 lines or fewer: one row per experiment and only the
current handoff. Put individual runs and historical decisions in that
experiment's findings. If the index grows, split it by phase and retain links
here. Old evidence remains available without being part of every AI request.
