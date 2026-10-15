# Conversational RAG — project checklist

The project targets bureaucratic institutions and their procedures. **FIIT → STU
is the first case study.** The [assignment and scope](project_scope.md) preserve
the formal requirements; the [experiment protocol](plan_experimentov.md) describes
controlled measurements.

Plane holds live progress. This file is the task specification and link map;
unchecked boxes here are not a synchronized status export. The plan currently
contains **18 cards and 94 checkable steps across seven phases**.

## Plane project

- [Bachelors Project](https://app.plane.so/bachelors-project/projects/c066fb45-2357-443a-b562-19d3767c2460/overview/)
- Workspace: `bachelors-project`; project ID: `c066fb45-2357-443a-b562-19d3767c2460`.
- Codex connection: `plane`; official endpoint: `https://mcp.plane.so/http/mcp`.
- Each computer needs its own OAuth connection; no credentials belong in Git.
- Research label: `bureaucratic-rag`.
- Workflow: **Backlog → Todo → In Progress → Review → Done**.
- The tutorial work items, modules, cycles, and labels have been removed. The demo
  page was replaced with **Assignment & project scope**, including the exact text.

## Start here

- [S00 · Scope & architecture](https://app.plane.so/bachelors-project/browse/BACHE-20/) — confirm the design, research questions, and MPC terminology.
- [E00 · Establish the baseline](https://app.plane.so/bachelors-project/browse/BACHE-8/) — validate the existing FIIT data and measure Qwen retrieval.

## Task map

| Phase | Task | Depends on |
| --- | --- | --- |
| 01 · Scope & architecture | [S00 · Scope & architecture](https://app.plane.so/bachelors-project/browse/BACHE-20/) | — |
| 02 · Data & evaluation | [S01 · Corpus adapters & institutional scope](https://app.plane.so/bachelors-project/browse/BACHE-21/) | S00 |
| 02 · Data & evaluation | [S02 · Public datasets & evaluation protocol](https://app.plane.so/bachelors-project/browse/BACHE-22/) | S00 |
| 02 · Data & evaluation | [E00 · Establish the baseline](https://app.plane.so/bachelors-project/browse/BACHE-8/) | — |
| 03 · Retrieval experiments | [E01 · Compare embedding models](https://app.plane.so/bachelors-project/browse/BACHE-9/) | E00 |
| 03 · Retrieval experiments | [E02 · Compare retrieval methods](https://app.plane.so/bachelors-project/browse/BACHE-10/) | E01 |
| 03 · Retrieval experiments | [E03 · Compare rerankers](https://app.plane.so/bachelors-project/browse/BACHE-11/) | E02 |
| 03 · Retrieval experiments | [E04 · Compare chunking strategies](https://app.plane.so/bachelors-project/browse/BACHE-12/) | E03 |
| 03 · Retrieval experiments | [E05 · Test metadata & query handling](https://app.plane.so/bachelors-project/browse/BACHE-13/) | E04 |
| 03 · Retrieval experiments | [E06 · Select the retrieval pipeline](https://app.plane.so/bachelors-project/browse/BACHE-14/) | E05 |
| 04 · Conversation & integration | [S05 · Storage & retrieval interfaces](https://app.plane.so/bachelors-project/browse/BACHE-23/) | S00 |
| 04 · Conversation & integration | [S03 · Multi-turn RAG application](https://app.plane.so/bachelors-project/browse/BACHE-24/) | S05, E06 |
| 04 · Conversation & integration | [S04 · Bureaucratic & cross-institution scenarios](https://app.plane.so/bachelors-project/browse/BACHE-25/) | S01, E06 |
| 04 · Conversation & integration | [E07 · Compare answer models](https://app.plane.so/bachelors-project/browse/BACHE-15/) | E06 |
| 04 · Conversation & integration | [E08 · Tune grounded conversation](https://app.plane.so/bachelors-project/browse/BACHE-16/) | E07, S02, S03, S04 |
| 05 · Final evaluation | [E09 · Run the final evaluation](https://app.plane.so/bachelors-project/browse/BACHE-17/) | E08 |
| 06 · Thesis writing | [Writing · Complete the thesis](https://app.plane.so/bachelors-project/browse/BACHE-18/) | — |
| 07 · Extensions | [Extensions · Explore optional improvements](https://app.plane.so/bachelors-project/browse/BACHE-19/) | — |

## Working agreement

- Keep architecture analysis separate from the implementation selected by it.
- Compare one factor at a time; save configurations, provenance, metrics, and decisions.
- Keep FIIT/Slovak, public-benchmark, and institutional-scenario results separate.
- S02, S03, and S04 must be ready before freezing the final system in E08.
- Write the thesis alongside implementation; select optional extensions from observed failures.
- Record dates and owners after the deadline and availability are agreed.
- Inspect existing task IDs before any future import to avoid duplicates.

## 01 · Scope & architecture

### [S00 · Scope & architecture](https://app.plane.so/bachelors-project/browse/BACHE-20/)

Turn the formal assignment into a concrete design for conversational RAG in bureaucratic institutions.

- [ ] Map every assignment requirement to an implementation or evaluation deliverable.
- [ ] Compare standard RAG and agentic RAG: control flow, tool use, evidence quality, latency, and complexity.
- [ ] Clarify “MPC versus RPC” with the supervisor; keep the original wording until its intended meaning is confirmed.
- [ ] Compare conventional databases, vector search, and hybrid storage using the project’s actual requirements.
- [ ] Record the chosen architecture, component interfaces, research questions, and a realistic minimum scope.

| Detail | Setting |
| --- | --- |
| Initial case | FIIT → STU, with adapters for other institutions |
| Required outcome | Own conversational RAG system, evaluated on public data and realistic scenarios |
| Architecture comparison | Analysis is required; implementing every alternative is not automatically required |

**Finish when:** A short architecture decision record covers the assignment, explains the selected design, and records unresolved terminology.

**Save:** Scope document, comparison matrix, architecture diagram, and decision record.

## 02 · Data & evaluation

### [S01 · Corpus adapters & institutional scope](https://app.plane.so/bachelors-project/browse/BACHE-21/)

Make the existing FIIT ingestion reusable and represent institutions and source applicability explicitly.

- [ ] Define a common document/chunk schema with source, document ID, institution, parent organization, rule scope, and validity metadata.
- [ ] Wrap the current FIIT parser/index inputs behind a corpus adapter instead of hardcoding the whole application to FIIT.
- [ ] Add a separately versioned STU source sample and map FIIT → STU relationships with explicit provenance.
- [ ] Define how local guidance, university-wide rules, exceptions, old editions, and missing metadata are handled.
- [ ] Verify a second corpus can be registered without rewriting retrieval or conversation logic.

| Detail | Setting |
| --- | --- |
| Separate concepts | Institutional membership, document applicability, and legal/rule precedence |
| Keep traceable | URLs, pages, headings, source versions, dates, and chunk ancestry |
| Authority policy | No automatic parent-over-child or child-over-parent rule |

**Finish when:** FIIT and a scoped STU sample share one schema and adapter contract, with documented applicability rules.

**Save:** Corpus adapter contract, institution/source registry, and checked example documents.

### [S02 · Public datasets & evaluation protocol](https://app.plane.so/bachelors-project/browse/BACHE-22/)

Evaluate beyond the local FIIT question set using public document-grounded conversational data.

- [ ] Review Doc2Dial and MultiDoc2Dial as candidates; verify domain fit, license, available splits, and usable annotations.
- [ ] Select public datasets for the final evaluation and document their coverage, relationship, and any overlap.
- [ ] Build a dataset adapter that keeps dialogue history, document IDs, evidence spans, and answer references separate from indexed knowledge.
- [ ] Define splits and leakage controls at dialogue/document/domain level as appropriate; freeze final evaluation inputs.
- [ ] Specify retrieval, answer support, citation, clarification, dialogue, latency, and resource metrics; report FIIT/Slovak and public-data results separately.

| Detail | Setting |
| --- | --- |
| Existing case study | FIIT QA: 120 questions; annotation review still required |
| Public candidates | Doc2Dial / MultiDoc2Dial; selection pending |
| Split caveat | MultiDoc2Dial v1 README describes a dummy test file; verify actual usable releases |

**Finish when:** A versioned public-data adapter and evaluation protocol exist with valid splits and explicit limitations.

**Save:** Dataset selection note, adapter, split manifests, and scoring rubric.

### [E00 · Establish the baseline](https://app.plane.so/bachelors-project/browse/BACHE-8/)

Measure the current FIIT retrieval implementation before changing it.

- [ ] Validate the normalized corpus, QA references, and existing QA tests.
- [ ] Record code/model revisions, data hashes, hardware, runtime, and index settings.
- [ ] Arrange independent annotation review and version any corrections.
- [ ] Create the reproducible run/configuration/manifest layout.
- [ ] Export Qwen predictions; map child chunks to unique parent IDs and check the actual evidence text.
- [ ] Save dev results, latency, and representative failures.

| Detail | Setting |
| --- | --- |
| Baseline | Existing Qwen3-Embedding-0.6B retrieval |
| Report at k | 1 / 3 / 5 / 10 |
| Scope | FIIT case study; broader evaluation is planned in S02 and S04 |

**Finish when:** The unchanged FIIT baseline is reproducible, validation passes, and annotation review status is explicit.

**Save:** Run configuration, predictions, metrics, timings, and a short error report.

## 03 · Retrieval experiments

### [E01 · Compare embedding models](https://app.plane.so/bachelors-project/browse/BACHE-9/)

Choose an embedding model through a controlled comparison.

- [ ] Smoke-test all four core embedding models on the available hardware.
- [ ] Pin revisions, formatting, pooling, precision, and normalization.
- [ ] Create shared chunks that fit every tokenizer without silent truncation.
- [ ] Measure quality, query latency, indexing time, memory, and index size on identical dev inputs.
- [ ] Compare shared-chunk Qwen against the original index as a separate chunking change.

| Detail | Setting |
| --- | --- |
| Models | Qwen3-Embedding-0.6B · BGE-M3 dense · multilingual-E5-base · multilingual-E5-large |
| Shared budget | Respect E5’s 512-token total input limit |
| Keep fixed | Text chunks, questions, metadata, retrieval method, and k |

**Finish when:** A saved comparison explains the selected dense model and any hardware exclusions.

**Save:** Model comparison table, configs, measured runs, and selection decision.

### [E02 · Compare retrieval methods](https://app.plane.so/bachelors-project/browse/BACHE-10/)

Compare lexical, dense, and hybrid retrieval on the same inputs.

- [ ] Implement BM25 with recorded tokenization that preserves codes and identifiers.
- [ ] Evaluate BM25 and the chosen dense model on identical chunks.
- [ ] Combine rankings with reciprocal rank fusion.
- [ ] Compare candidate depths and record the deduplicated union size.
- [ ] Score final rankings and inspect questions needing multiple sources.

| Detail | Setting |
| --- | --- |
| Methods | BM25 · dense · hybrid RRF |
| RRF starting point | c = 60 |
| Candidates / results | 20 / 50 / 100 per branch; report k = 1 / 3 / 5 / 10 |

**Finish when:** All three methods are reproducible and compared on dev.

**Save:** Ranking exports, quality/latency table, and retrieval decision.

### [E03 · Compare rerankers](https://app.plane.so/bachelors-project/browse/BACHE-11/)

Measure whether reranking improves already-retrieved evidence enough to justify its cost.

- [ ] Freeze candidate IDs and text for a fair comparison.
- [ ] Smoke-test BGE-reranker-v2-m3 and Qwen3-Reranker-0.6B.
- [ ] Define shared windows and aggregation for overlong query–passage pairs.
- [ ] Compare both rerankers with the unchanged candidate order.
- [ ] Measure evidence coverage, rank changes, and added latency.

| Detail | Setting |
| --- | --- |
| Models | None · BGE-reranker-v2-m3 · Qwen3-Reranker-0.6B |
| Candidate depths | 20 / 50 / 100 |
| Input limits | Count question and formatting; log splitting rather than silently truncate |

**Finish when:** The reranker choice is supported by a saved quality/cost comparison.

**Save:** Frozen candidates, reranked outputs, timing, and decision.

### [E04 · Compare chunking strategies](https://app.plane.so/bachelors-project/browse/BACHE-12/)

Find document boundaries and token budgets that preserve evidence and retrieval quality.

- [ ] Remap references through source document, page, and exact spans when chunk boundaries change.
- [ ] Compare block-aware, fixed-window, and recursive splitting with other components fixed.
- [ ] Vary chunk sizes and overlap in stages instead of testing the full parameter grid.
- [ ] Check table headers, row/value relationships, and surrounding context.
- [ ] Record quality, chunk lengths/counts, duplication, and index size.

| Detail | Setting |
| --- | --- |
| Sizes | 256 / 512 / 1,024 / 2,048 tokens where supported |
| Overlap | 0 / 10 / 20 percent |
| Fairness | Same corpus, model, retrieval, and evidence semantics |

**Finish when:** Evidence mappings are verified and chunking choices have comparable dev results.

**Save:** Chunking configs, source mappings, comparison table, and failures.

### [E05 · Test metadata & query handling](https://app.plane.so/bachelors-project/browse/BACHE-13/)

Measure metadata and query-handling changes without mixing their effects.

- [ ] Test document titles and heading paths in embedding inputs.
- [ ] Test year text separately from explicit validity filters and unknown-year fallback.
- [ ] Test result deduplication while preserving complementary evidence.
- [ ] Test normalization, verified abbreviations, and missing-diacritic handling.
- [ ] Measure changes separately and connect institution/scope metadata to S01 and S04.

| Detail | Setting |
| --- | --- |
| Change one factor | Titles · years · duplicates · abbreviations · diacritics |
| Historical editions | Retain for historical questions |
| Institution routing | Policy defined in S01; scenario evaluation in S04 |

**Finish when:** Every retained change has an individual result and an explained failure/cost tradeoff.

**Save:** Ablation-ready metadata/query settings and per-change results.

### [E06 · Select the retrieval pipeline](https://app.plane.so/bachelors-project/browse/BACHE-14/)

Assemble the best-supported retrieval configuration and check interactions.

- [ ] Combine the selected components and verify their interaction on dev.
- [ ] Prepare ablations that remove each retained improvement.
- [ ] Check multi-source support, requested period, latency, and memory when selecting a configuration.
- [ ] Retain reproducible BM25, original Qwen, best dense, hybrid, and hybrid+reranking baselines.

| Detail | Setting |
| --- | --- |
| FIIT selection | complete_support@5, then mrr@5 |
| Other datasets | Use their documented task-appropriate metrics from S02 |
| Next use | Shared retrieval component for the conversation application |

**Finish when:** The chosen retrieval pipeline and final comparison candidates have a recorded rationale.

**Save:** Selected configuration, ablations, and comparison candidates.

## 04 · Conversation & integration

### [S05 · Storage & retrieval interfaces](https://app.plane.so/bachelors-project/browse/BACHE-23/)

Implement the storage and service boundaries selected in the architecture study.

- [ ] Choose metadata/document persistence and exact or indexed vector search from the recorded requirements.
- [ ] Define stable ingestion, retrieval, citation, and session-facing request/response contracts.
- [ ] Implement the selected interfaces and wire the existing retrieval pipeline through them.
- [ ] Add provenance-aware error handling, reproducible configuration, and logging of retrieval/tool calls.
- [ ] Implement an MCP or other RPC adapter only if the clarified assignment and chosen design justify it; do not assume they are interchangeable alternatives.

| Detail | Setting |
| --- | --- |
| Comparison | Data consistency, filtering, updates, query latency, memory, and operational cost |
| Implementation scope | One justified working design; extra backends only for a defined experiment |
| Protocol terminology | Depends on the S00 clarification of MPC |

**Finish when:** The selected storage/retrieval interfaces work end to end and match the architecture decision.

**Save:** Runnable interface implementation, schemas, configuration, and integration notes.

### [S03 · Multi-turn RAG application](https://app.plane.so/bachelors-project/browse/BACHE-24/)

Deliver the conversational application required by the assignment.

- [ ] Build a minimal runnable chat interface or API with session-scoped dialogue history.
- [ ] Resolve follow-up references while retaining the user’s institution, period, and original question.
- [ ] Retrieve evidence for each turn and generate an answer with inspectable source citations.
- [ ] Ask for missing context, explain conflicting sources, and state when available evidence is insufficient.
- [ ] Exercise conversation resets, topic/institution changes, and follow-up questions in reproducible dialogue scenarios.

| Detail | Setting |
| --- | --- |
| State | Dialogue history, requested institution, and time period |
| Evidence | Preserve source links and the actual retrieved context per turn |
| Start small | A complete working conversation flow before additional UI features |

**Finish when:** A user can complete a multi-turn scenario with context retained, correct clarification, and source-backed answers.

**Save:** Runnable application, example transcripts, and conversation trace format.

### [S04 · Bureaucratic & cross-institution scenarios](https://app.plane.so/bachelors-project/browse/BACHE-25/)

Test realistic procedures and institution hierarchy using FIIT → STU as the first scenario.

- [ ] Create scenarios for deadlines, required documents, procedure steps, eligibility conditions, and dependencies between steps.
- [ ] Cover FIIT-local questions, university-wide STU questions, and questions requiring evidence from both levels.
- [ ] Implement and compare institution/scope-aware retrieval or routing against an unrestricted baseline.
- [ ] Include ambiguous institution/year, conflicting editions, local exceptions, missing evidence, and follow-up questions.
- [ ] Annotate expected evidence and behavior, then measure scope selection, procedure completeness, citations, and clarification quality.

| Detail | Setting |
| --- | --- |
| Source hierarchy | Represented explicitly; authority follows the documented applicability policy |
| Ground truth | Versioned source evidence and reviewed expected behavior |
| Scenario status | Planning and evaluation work; no new sources claimed as already ingested |

**Finish when:** A reviewed scenario suite exposes routing, applicability, procedure, and conversation failures beyond single-document QA.

**Save:** Scenario set, expected evidence/behavior, routing comparison, and error analysis.

### [E07 · Compare answer models](https://app.plane.so/bachelors-project/browse/BACHE-15/)

Compare grounded answer models independently of retrieval changes.

- [ ] Smoke-test Qwen3-4B and Gemma-3-4B-IT with supported precision or quantization.
- [ ] Implement evidence-backed answers, citations, and clarification/insufficient-evidence behavior.
- [ ] Freeze the same retrieved text and order for both generators.
- [ ] Define one rubric and separate no-retrieval, actual-retrieval, and oracle-evidence conditions.
- [ ] Review outputs without model names and save support, factuality, citation, token, and timing results.

| Detail | Setting |
| --- | --- |
| Models | Qwen3-4B · Gemma-3-4B-IT |
| Controlled context | Identical evidence text and order |
| Dialogue integration | Tracked separately in S03 |

**Finish when:** Generator quality and behavior are measured with retrieval held constant.

**Save:** Prompts, contexts, answers, manual rubric, and timing comparison.

### [E08 · Tune grounded conversation](https://app.plane.so/bachelors-project/browse/BACHE-16/)

Tune answers and conversation behavior on dev, then freeze the final system.

- [ ] Vary top-k, context budget, prompt, and deduplication one factor at a time.
- [ ] Tune clarification and insufficient-evidence behavior using dev only.
- [ ] Review dates, numbers, institution/year scope, forbidden claims, and citations.
- [ ] Test retrieved instructions, follow-up references, and institution/topic changes.
- [ ] Freeze the application, retrieval, generator, and scoring rules before final evaluation.

| Detail | Setting |
| --- | --- |
| Inputs | E07 generator results + S03 app + S04 scenarios + S02 protocol |
| Selection | Factuality and source support first; speed/resources next |
| Separation | No tuning against held-out final results |

**Finish when:** The complete conversational configuration and evaluation rules are locked.

**Save:** Final dev report, frozen configs/prompts, and answerability policy.

## 05 · Final evaluation

### [E09 · Run the final evaluation](https://app.plane.so/bachelors-project/browse/BACHE-17/)

Demonstrate the system on public data and realistic institutional conversations.

- [ ] Evaluate locked baselines and the final system on held-out data.
- [ ] Report FIIT/Slovak, public-benchmark, and FIIT → STU scenario results separately.
- [ ] Run predefined ablations and report relevant question/dialogue groups.
- [ ] Report counts, retrieval/support/citation quality, dialogue behavior, latency, and memory.
- [ ] Analyze source coverage, annotation/split limitations, conflicts, and failure types.
- [ ] Save reproducible artifacts and write the results/discussion from measured outputs.

| Detail | Setting |
| --- | --- |
| Coverage | Public datasets + realistic bureaucratic scenarios |
| Baselines | Retained retrieval variants and selected generation comparison |
| After test | Further tuning requires a fresh final evaluation |

**Finish when:** The assignment’s implementation and evaluation claims are backed by reproducible measured results.

**Save:** Final metrics, transcripts, ablations, errors, and thesis results.

## 06 · Thesis writing

### [Writing · Complete the thesis](https://app.plane.so/bachelors-project/browse/BACHE-18/)

Write the thesis around the formal assignment and the system actually built.

- [ ] Confirm the scope, research questions, and unresolved MPC terminology with the supervisor.
- [ ] Write related work covering RAG/agentic RAG, integration protocols, and conventional/vector storage.
- [ ] Describe institution hierarchy, source applicability, corpus adapters, and the FIIT → STU case study.
- [ ] Document the conversational architecture, implementation, and public/realistic evaluation protocol.
- [ ] Add measured results, limits, discussion, and conclusions after E09.
- [ ] Check references, figures, reproduction instructions, and submission requirements.

| Detail | Setting |
| --- | --- |
| Main topic | Conversational RAG for bureaucratic institutions |
| FIIT role | Initial case study |
| Write in parallel | Existing implementation and theory can be documented now |

**Finish when:** The thesis covers every assignment requirement and clearly separates implemented behavior from proposed extensions.

**Save:** Complete thesis and reproducibility appendix.

## 07 · Extensions

### [Extensions · Explore optional improvements](https://app.plane.so/bachelors-project/browse/BACHE-19/)

Investigate extensions only when a concrete failure and resources justify them.

- [ ] Test larger embedding, reranking, or answer models.
- [ ] Explore BGE sparse/multi-vector retrieval or alternative fusion.
- [ ] Try parent–child, semantic, or contextualized chunking.
- [ ] Try query rewriting, multi-query, decomposition, or HyDE.
- [ ] Investigate quantization, dimension reduction, or approximate search when scaling requires it.
- [ ] Compare a bounded agentic retrieval prototype with standard RAG using the same evidence access, budgets, and metrics.
- [ ] Run targeted extraction/OCR experiments on approved data samples.

| Detail | Setting |
| --- | --- |
| Required analysis | RAG vs agentic RAG is covered in S00 |
| Optional implementation | Agentic prototype and additional backend/model variants |
| Test discipline | Do not tune on the already-used final test set |

**Finish when:** Each chosen extension has a control, measured benefit/cost, and an explicit keep/drop decision.

**Save:** Separate extension run reports; no unmeasured superiority claims.
