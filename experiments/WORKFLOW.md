# Research recording workflow

## Ownership and layout

| Information | Authoritative location |
| --- | --- |
| Tasks, priorities, blockers | Existing Plane tasks linked in `docs/project_checklist.md` |
| Broad research protocol and scope | `docs/plan_experimentov.md` and `docs/project_scope.md` |
| Current evidence and next research action | `experiments/README.md` |
| Experiment hypothesis, comparisons, findings | `experiments/<experiment>/plan.md` and `findings.md` |
| Small reproducibility package for one execution | `experiments/<experiment>/runs/<run_id>/` |
| Full outputs and traces | Ignored `output/experiments/<run_id>/`, plus a verified backup |
| Thesis evidence map | `experiments/claims.md` |

Use existing E/S IDs. A run ID includes the experiment, UTC timestamp, and variant,
for example `E01_20261015T143000Z_bge-m3_s42`. This is a naming example, not a run.
Never reuse an ID for changed inputs or reruns. Create folders only as needed.
Keep ordinary Markdown usable from a text editor; no notebook service is required.

## Before running

Copy [templates/plan.md](templates/plan.md). Specify the research question,
hypothesis, changed factor, control, constants, exact dataset/split, primary
metric and tie-breaks. Set a finite candidate list, runtime/cost budget, repeat
policy, and stopping condition before the sweep. Link the relevant broad
protocol section instead of copying its model catalog.

For development, use dev data. Freeze the chosen configuration and evaluation
protocol in a Git commit before final test use. Record all test exposure. A
post-test improvement is a new exploratory result; it needs fresh held-out
evidence to support a new confirmatory claim. Never index reference answers or
feed future dialogue turns into the current turn. Recheck chunk-to-evidence
mapping when chunking changes.

## Run records and reproducibility

The existing plan's raw artifact directory remains `output/experiments/<run_id>/`.
The proposed runner is not implemented yet: collect the following evidence
manually or with the relevant existing commands until automation exists.

Keep these small files under `experiments/<experiment>/runs/<run_id>/`:

| File | Required content |
| --- | --- |
| `record.md` | Use [the template](templates/record.md): execution outcome, exact commands, provenance links, backup status, anomalies, review. |
| `config.json` | Effective settings, not just overridden flags: chunking, models/revisions, query/document prefixes, retrieval/top-k, filters, fusion/reranking, prompts/context, generation, seeds. Mark inapplicable fields explicitly. |
| `manifest.json` | Run/experiment IDs and UTC times; code commit; dataset/corpus/chunk fingerprints; model and tokenizer revisions; dependency versions; OS, CPU/GPU, RAM/VRAM; precision/quantization; evaluation implementation and protocol version. |
| `metrics.json` | Actual aggregate evaluator output with definitions, units, split, sample counts, missing/failed cases, and subgroup denominators. If compacted from a larger output, record its hash and the exact extraction command. |

Store file hashes as SHA-256, with relative paths and roles. For a directory,
hash a sorted manifest of relative paths and file hashes, not its name or count.
Identify the split by exact question/dialogue IDs or a hashed split file. Record
dataset release, source/license, sampling rules, and document versions. A hash
identifies data; it does not preserve it. Keep a retrievable snapshot or backup.

Prefer a clean committed code version. A dirty run must preserve a sanitized
patch and any relevant untracked source, with hashes and retrieval locations;
a `dirty=true` flag or patch hash alone is insufficient to reproduce it.
Never place credentials in the patch, commands, or manifest. Record dependency
locks or an exact environment export, not just the Python version.

Raw `retrieval.jsonl`, `predictions.jsonl`, `answers.jsonl`, per-question metrics,
logs, and large plots stay in the ignored raw directory. Copy the exact small
config/manifest/aggregate metrics into Git; treat these as frozen snapshots of
that run. Save full prompts and rendered contexts in the raw bundle, and retain
the prompt template/version in the reproducibility package.

Document a backup URI/location, archive hash, and verification date in the run
record. Until a second copy is verified, label it `local-only / at risk`; Git's
ignore rule is not a backup. Storage is not provisioned by this workflow.
Do not delete raw data cited by the thesis. Check redistribution rights and
personal data before publishing excerpts or corpus material.

Completed outputs are immutable by convention. Failed, interrupted, negative,
and OOM runs stay discoverable in findings; don't record missing scores as zero.
A corrected run or rescoring gets a new ID and links its input/source run and
what it supersedes. A typo or review annotation can be corrected through Git,
but never silently replace the measurements of a completed run.

## Findings and fair comparisons

Use [templates/findings.md](templates/findings.md) once evidence exists. Lead
with a short conclusion, scope, and confidence, then a run table, observed
failures, decision, and next action. A null result is a result. Include all
attempted variants and exclusion reasons; never report only the best seed.

Before comparing scores, verify dataset and split fingerprints, metric
implementation, evidence mapping, and experimental controls. Compare latency
only with compatible hardware, batching, warm-up, and measurement boundaries.
If any differ, disclose the confound or rerun rather than ranking them together.
Report counts, units, repeat variability, and uncertainty where justified. Keep
FIIT, public datasets, and institutional scenarios separate. On FIIT, current
evidence-hit metrics are not complete relevance recall or precision.

Each comparison table should link run IDs and state the exact metric JSON key
or JSON Pointer. Tables and plots should come from those files with a saved
generation command/script; avoid manually retyping numbers. Preserve a few
representative failure IDs and references so later analysis can fetch only them.
Keep the findings summary roughly one page; link deeper error analysis when needed.

Review means checking provenance, comparability, metric denominators, exclusion
rules, and whether the conclusion follows. Record reviewer identity/type (human
or AI), date, and remaining limits. AI review is not independent expert review.

## Thesis evidence and maintenance

For each empirical thesis claim, add a stable `C001`-style ID to
[claims.md](claims.md) with the proposed wording, exact run/metric references,
dataset/split scope, limitations, review status, and intended chapter. Candidate
claims remain explicitly tentative. A `supported` claim needs reviewed evidence
and a traceable calculation; a `superseded` claim links its replacement. A claim
can report failure or no clear difference. Literature claims use bibliographic
citations in the thesis, separate from local experiment evidence.

At the end of meaningful experiment work, update the experiment findings and
the index's current handoff. Add a short decision entry only when the choice
changes, with date, rationale, evidence, and superseded choice if applicable.
Do not append a transcript of each session. Archive older details by links when
summaries grow; preserve the underlying evidence and negative results.

When task updates are authorized, put a short conclusion and Git commit permalink
on the existing Plane task. The full analysis lives here. Before a thesis release,
verify claim links, artifact retrieval, figure generation, and known limitations;
then record the exact manuscript and evidence commits used.

These are lightweight conventions and templates, not an automatic runner,
validator, backup service, or synchronization system. Add automation when an
actual repeated operation warrants it; avoid maintaining duplicate registries.
