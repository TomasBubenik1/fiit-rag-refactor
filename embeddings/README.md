# Local Qwen3 embeddings

The model is `Qwen/Qwen3-Embedding-0.6B`, pinned to revision
`97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`. Files are downloaded from the official
Hugging Face repository and verified against its published LFS/Git checksums.
The local cache is `.cache/models/qwen3-embedding-0.6b/`.

Inference uses local files only, with Hugging Face offline mode and telemetry
disabled. No embedding service receives your documents or questions.

## Set up on this machine

```powershell
.\.venv\Scripts\python.exe tools/setup_embeddings.py --install-dependencies
```

`requirements-embedding.txt` pins the official Windows/Python 3.13 PyTorch 2.8.0
CUDA 12.6 wheel by SHA-256, plus Transformers and Sentence Transformers. CUDA
12.6 retains Pascal support for the GTX 1080 Ti. The installer uses temporary
files/cache on the project drive instead of filling the Windows system drive.
For a different OS/Python version, install the corresponding compatible PyTorch
build instead of this Windows wheel.

The loader uses FP32, SDPA's compatible backend and no generation KV cache.
This card has no BF16 or FlashAttention support. CPU inference is also available
with `--device cpu`; the default device is CUDA.
CUDA inference caps this process's allocator at half of the card's VRAM and
reclaims cached blocks sooner. This avoided Windows shared-memory spill during
the full index run. It is a ceiling, not a reservation of GPU memory.

## Build or resume the index

```powershell
.\.venv\Scripts\python.exe tools/embed_chunks.py
```

The default input is `data/normalized/chunks.ready.jsonl`. Review and supporting
chunks are excluded. The original cleaned documents and block-aware chunk files
remain unchanged.

The model supports 32,768 tokens, but this GPU setup defaults to **2,048 tokens**
per input and batches of 4. This is a practical inference budget, not a model
context limit. `chunking/token_aware.py` checks the chosen tokenizer, including
document title, heading context and validity metadata. Oversized chunks are
split again: table rows retain repeated context/headers and expanded rowspans.
An individually oversized row/text block is split further at Unicode/word
boundaries. Every result retains its parent chunk ID and source/page metadata.
An accidentally huge heading is omitted from repeated embedding context; its
complete value remains in chunk metadata and its original body text is retained.
`embedding_context_compacted` records this explicitly. No body text is silently
truncated. A CUDA memory failure reduces the batch size;
completed batches remain resumable.
Running the build command again returns an already completed index immediately.

Output in `data/embeddings/qwen3-0.6b/`:

- `vectors.npy`: normalized FP32 vectors, 1,024 dimensions, aligned with chunk rows.
- `chunks.jsonl`: embedding inputs, token counts and original provenance.
- `token_audit.json`: input coverage, split counts and maximum token length.
- `progress.json`: committed rows and exact input/model settings for resuming.
- `manifest.json`: completed index configuration and hardware details.
- `validation.json`: verified token lengths, vector norms, coverage and provenance.
- `build_runtime_snapshot/`: exact source and allocator settings used to build this index.

Validate the completed index against its cleaned source chunks:

```powershell
.\.venv\Scripts\python.exe tools/validate_embeddings.py
```

Use another output directory when changing model/input/token settings:

```powershell
.\.venv\Scripts\python.exe tools/embed_chunks.py --max-tokens 1024 --output-dir data/embeddings/qwen3-1024
```

## Search locally

```powershell
.\.venv\Scripts\python.exe tools/search_embeddings.py "Kedy sa začína letný semester 2025/26?" --top-k 5
```

Queries use Qwen's instruction format with a FIIT retrieval instruction;
documents do not use a query prompt. Both are normalized and compared by cosine
similarity. The small local index uses NumPy dot products, so it needs no database
server. Scores measure similarity, not answer correctness. The source corpus
contains historical documents, and retrieval quality needs evaluation on FIIT
questions before using it to answer students automatically.

The completed local run contains **9,664 vectors from 9,580 ready source chunks**.
All rows passed token-length, normalization, coverage and provenance checks.
The timetable query above ranked the correct 2025/26 PDF first. Course-credit
queries also returned relevant course tables, but older catalog editions ranked
above 2025/26 even when that year was in the question. Explicit year filtering
or reranking is still needed; a year in the query is not a retrieval constraint.
Saved examples are in `data/embeddings/qwen3-0.6b/search_smoke.json`.

[Model documentation](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
[Pascal/CUDA build policy](https://dev-discuss.pytorch.org/t/cuda-toolkit-version-and-architecture-support-update-maxwell-and-pascal-architecture-support-removed-in-cuda-12-8-and-12-9-builds/3128).
