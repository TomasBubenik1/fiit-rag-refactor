# Run ID

Template: fill measured facts, use `unknown` or `not applicable` with reasons.
Unknown required provenance makes the run exploratory/incomplete, not reproducible.

| Field | Value |
| --- | --- |
| Experiment and variant | |
| Outcome: completed / failed / interrupted | |
| Purpose: smoke / exploratory / confirmatory | |
| Started/finished UTC | |
| Source run or supersedes, with reason | |
| Plan and protocol/freeze commit | |

## Execution

Save the exact working directory and runnable commands, including evaluation
and any metrics extraction. Identify required local inputs and relative paths.
List exit codes, actual sample counts, missing predictions, exclusions, and
whether this execution exposed test data. Link the sanitized environment export.

## Evidence

- `config.json`: effective settings and model/prompt revisions.
- `manifest.json`: code/data/model/environment provenance and SHA-256 hashes.
- `metrics.json`: aggregate results; exact metric fields used in conclusions.
- Raw artifact path: `output/experiments/RUN_ID/` (from repository root).
- Backup location, bundle SHA-256, verification date and method:
- Availability: local-only / backed-up / unavailable; list any missing evidence.
- Dirty source patch and untracked inputs, if applicable:

## Anomalies and review

Record failures, deviations, selected question IDs, and links into raw artifacts.
Record reviewer identity/type, date, checks performed, and unresolved limits.
Execution success alone does not establish validity or thesis readiness.
