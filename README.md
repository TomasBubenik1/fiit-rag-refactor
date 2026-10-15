# Conversational RAG for bureaucratic institutions

The thesis targets a reusable conversational RAG system for institutional
information and procedures. FIIT STU is the initial corpus and case study;
FIIT → STU is the first planned hierarchy scenario. The full assignment also
requires architecture analysis, public-dataset evaluation, and realistic
conversations. See the [assignment and scope](docs/project_scope.md) and
[planning checklist](docs/project_checklist.md).

Experiment work starts at the [experiment notebook](experiments/README.md).
It keeps a small evidence index, reproducible run records, findings, and a thesis
claim map. The repository skill
[`experiment-records`](.agents/skills/experiment-records/SKILL.md) follows this
workflow; invoke it with `$experiment-records` when working on experiments.

## Current implementation

Local tools for cleaning the supplied FIIT STU website/PDF corpus, preserving
source references, chunking documents and searching with Qwen3 embeddings.
Application code uses plain functions. Each chunking method has its own file.

## Project structure

- `tools/`: HTML/PDF extraction, corpus normalization, validation and CLI commands.
- `chunking/block_aware.py`: Markdown blocks, complete tables and PDF page boundaries.
- `chunking/token_aware.py`: tokenizer-budget splitting for embedding inputs.
- `embeddings/qwen3.py`: pinned model download and offline inference.
- `tests/`: regression checks for extraction, source preservation and chunking.

The supplied dataset, cleaned outputs, vector indexes, virtual environment and
model/OCR caches remain local and are excluded from Git. A fresh clone requires
the original data to be placed under `data/` before running the corpus pipeline.
No dataset or model weights are downloaded by cloning this repository.

## Setup

The checked embedding configuration targets **Windows, Python 3.13 and a GTX
1080 Ti**. Its pinned PyTorch CUDA 12.6 build retains support for this card.
For another operating system or Python version, use a compatible PyTorch wheel
as described in [the embedding guide](embeddings/README.md).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-parser.txt
.\.venv\Scripts\python.exe tools/setup_pdf_ocr.py
.\.venv\Scripts\python.exe tools/setup_embeddings.py --install-dependencies
```

The setup commands download dependencies and pinned OCR/model files. Extraction
and embedding inference then run locally; inference uses offline mode.

## Clean and validate the corpus

Place the supplied folder contents under `data/`, including `raw_html/`,
`raw_pdfs/`, `raw_xml/`, `markdown/` and their original mapping/metadata files.
The normalizer preserves these originals and writes separate derived outputs.

```powershell
.\.venv\Scripts\python.exe tools/normalize_dataset.py --stage web
.\.venv\Scripts\python.exe tools/batch_dataset_pdfs.py --workers 6
.\.venv\Scripts\python.exe tools/normalize_dataset.py --stage finalize
.\.venv\Scripts\python.exe tools/validate_normalized_dataset.py
```

`data/normalized/documents/` contains cleaned Markdown/JSON documents.
`corpus.jsonl` remains independent of the chosen chunking method. Derived chunks
are separated into ready and review files; OCR and ambiguous extraction results
are flagged for review. Records retain source file/URL, page, heading context
and available validity/academic-year metadata.

See [the parser guide](tools/README.md) for individual files, OCR options and
[the chunking guide](chunking/README.md) for alternative chunking workflows.

## Build and search a local index

```powershell
.\.venv\Scripts\python.exe tools/embed_chunks.py
.\.venv\Scripts\python.exe tools/validate_embeddings.py
.\.venv\Scripts\python.exe tools/search_embeddings.py "Kedy sa začína letný semester 2025/26?"
```

The default index includes ready knowledge chunks only. It uses normalized
1,024-dimensional FP32 vectors and a 2,048-token inference budget. Oversized
inputs are split with source provenance preserved. Completed batches are
resumable, and a completed index is reused when the build command runs again.
Cleaned documents and the original block-aware chunks remain unchanged.

The small index uses NumPy cosine search and needs no database server. Retrieval
scores are similarity scores. The corpus contains historical editions; a year
in a query does not enforce a year filter. See [the embedding guide](embeddings/README.md)
for hardware settings, output formats and observed retrieval limitations.

## FIIT question evaluation dataset

The planned models, retrieval variants and evaluation protocol are listed in
the Slovak [experiment plan](docs/plan_experimentov.md).

[`evaluation/fiit_qa/`](evaluation/fiit_qa/README.md) contains 120 Slovak questions:
100 with reference answers and exact source evidence, 10 requiring clarification
and 10 unanswerable from the saved public corpus. It includes 30 development and
90 test questions, a questions-only JSONL export and a readable answer overview.
Annotations are assistant-curated against the local snapshot and still require
independent expert review. Validate provenance and score saved retrieval results:

```powershell
.\.venv\Scripts\python.exe tools/validate_qa_dataset.py
.\.venv\Scripts\python.exe tools/evaluate_qa_retrieval.py data/qa_predictions.jsonl --split test --top-k 5
```

See the [dataset guide](evaluation/fiit_qa/README.md) for the prediction format,
metrics, split policy and limitations. Original evaluation files remain unchanged.

## Tests

Run the self-contained QA dataset integrity and retrieval scoring tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_qa_dataset.py -v
```

Run the self-contained tokenizer-budget chunking tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_token_aware_chunking.py -v
```

The complete suite uses the supplied HTML/PDF/log fixtures under `data/` and
the OCR language files installed above:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 24 tests passed on the original local corpus before publication. The local
index run also validated all 9,664 vectors from 9,580 ready source chunks.
