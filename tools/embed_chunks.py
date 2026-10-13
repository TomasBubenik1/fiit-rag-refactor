"""Build a resumable local Qwen3 index from the cleaned RAG-ready chunks."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from chunking.token_aware import split_chunk
from embeddings.qwen3 import MODEL_DIRECTORY, MODEL_ID, MODEL_REVISION, encode_documents, load_model, load_tokenizer
from tools.batch_dataset_pdfs import atomic_json

DEFAULT_OUTPUT = ROOT / "data" / "embeddings" / "qwen3-0.6b"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_output(output, input_path):
    output = Path(output).resolve()
    protected = ("raw_html", "raw_pdfs", "raw_xml", "markdown", "normalized", "analytics", "bot_logs", "hf_export", "models")
    if output == ROOT / "data" or any(output.is_relative_to(ROOT / "data" / name) for name in protected):
        raise ValueError("Choose a separate embedding output directory to preserve source/cleaned data.")
    if Path(input_path).resolve().is_relative_to(output):
        raise ValueError("Input chunks must be outside the embedding output directory.")
    return output


def prepare_records(input_path, tokenizer, max_tokens, limit=None):
    records, parent_counts, lengths = [], Counter(), []
    with Path(input_path).open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            if limit is not None and index >= limit:
                break
            chunk = json.loads(line)
            if chunk["status"] != "parsed" or chunk["scope"] != "knowledge" or chunk["warnings"]:
                raise ValueError(f"Chunk is not ready faculty knowledge: {chunk['id']}")
            for record in split_chunk(chunk, tokenizer, max_tokens):
                record["embedding_row"] = len(records)
                records.append(record)
                parent_counts[chunk["id"]] += 1
                lengths.append(record["token_count"])
            if (index + 1) % 1000 == 0:
                print(f"Token audit: {index + 1} source chunks", flush=True)
    if not records:
        raise ValueError("Input contains no ready chunks.")
    # Group similar lengths to reduce padding work on the Pascal GPU.
    records.sort(key=lambda record: (record["token_count"], record["id"]))
    for row, record in enumerate(records):
        record["embedding_row"] = row
    return records, {"source_chunks": len(parent_counts), "embedding_chunks": len(records),
                     "split_source_chunks": sum(count > 1 for count in parent_counts.values()),
                     "compacted_context_source_chunks": len({record["parent_chunk_id"] for record in records if record["embedding_context_compacted"]}),
                     "minimum_tokens": min(lengths), "maximum_tokens": max(lengths),
                     "truncated_inputs": 0}


def build_index(input_path, output, model_directory=MODEL_DIRECTORY, device="cuda", batch_size=4,
                max_tokens=2048, limit=None):
    import numpy as np
    import torch
    output = validate_output(output, input_path)
    output.mkdir(parents=True, exist_ok=True)
    if not 128 <= max_tokens <= 32768 or batch_size < 1:
        raise ValueError("Use 128..32768 tokens and a positive batch size.")
    config = {"model_id": MODEL_ID, "model_revision": MODEL_REVISION, "input_file": str(Path(input_path).resolve()),
              "input_sha256": sha256(input_path), "max_tokens": max_tokens, "limit": limit,
              "chunker_sha256": sha256(ROOT / "chunking/token_aware.py"),
              "model_code_sha256": sha256(ROOT / "embeddings/qwen3.py"),
              "pipeline_code_sha256": sha256(__file__),
              "dtype": "float32", "normalize_embeddings": True, "embedding_dimensions": 1024}
    progress_path = output / "progress.json"
    previous = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else None
    if previous and previous["config"] != config:
        raise ValueError("This index uses different input/model settings. Choose a separate output directory.")
    manifest_path = output / "manifest.json"
    if previous and previous["status"] == "complete" and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        matrix = np.load(output / manifest["vectors"], mmap_mode="r")
        if (manifest["status"] != "complete" or manifest["config"] != config
                or previous["completed_rows"] != previous["total_rows"]
                or matrix.shape != (previous["total_rows"], 1024)
                or not (output / manifest["chunks"]).is_file()):
            raise ValueError("Completed index files are inconsistent. Run tools/validate_embeddings.py.")
        return output
    tokenizer = load_tokenizer(model_directory)
    records, audit = prepare_records(input_path, tokenizer, max_tokens, limit)
    ids = [record["id"] for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate embedding chunk IDs.")
    atomic_json(output / "token_audit.json", audit)
    with (output / "chunks.jsonl").open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    matrix_path = output / "vectors.npy"
    committed = previous["completed_rows"] if previous else 0
    if previous:
        matrix = np.load(matrix_path, mmap_mode="r+")
        if matrix.shape != (len(records), 1024) or not 0 <= committed <= len(records):
            raise ValueError("Stored vector matrix does not match the indexed chunks.")
    else:
        matrix = np.lib.format.open_memmap(matrix_path, mode="w+", dtype=np.float32, shape=(len(records), 1024))
        atomic_json(progress_path, {"config": config, "completed_rows": 0, "total_rows": len(records), "status": "running"})
    model = load_model(model_directory, device=device, max_tokens=max_tokens)
    hardware = {"device": device, "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
                "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None}
    started, last_report = time.time(), 0
    while committed < len(records):
        stop = min(committed + batch_size, len(records))
        texts = [record["embedding_text"] for record in records[committed:stop]]
        try:
            vectors = encode_documents(model, texts, batch_size=batch_size)
        except torch.cuda.OutOfMemoryError:
            if batch_size == 1:
                raise RuntimeError("A single input exhausted VRAM. Use fewer tokens in a separate index, or select --device cpu.")
            batch_size = max(1, batch_size // 2)
            torch.cuda.empty_cache()
            print(f"Reduced batch size to {batch_size} after a CUDA memory allocation failure.", flush=True)
            continue
        if vectors.shape != (stop - committed, 1024) or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding vector output.")
        if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
            raise ValueError("Embedding vectors are not normalized.")
        matrix[committed:stop] = vectors
        matrix.flush()
        committed = stop
        atomic_json(progress_path, {"config": config, "completed_rows": committed, "total_rows": len(records),
                                   "status": "complete" if committed == len(records) else "running", "hardware": hardware})
        if time.time() - last_report >= 20 or committed == len(records):
            print(f"Embedded {committed}/{len(records)} chunks, {time.time() - started:.0f}s", flush=True)
            last_report = time.time()
    atomic_json(output / "manifest.json", {"status": "complete", "config": config, "audit": audit, "hardware": hardware,
                "batch_size": batch_size, "model_directory": str(Path(model_directory).resolve()),
                "vectors": "vectors.npy", "chunks": "chunks.jsonl", "similarity": "cosine (dot product of unit vectors)",
                "elapsed_seconds_this_attempt": round(time.time() - started, 2)})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/normalized/chunks.ready.jsonl")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIRECTORY)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--limit", type=int, help="Use only this many source chunks for a smoke test")
    args = parser.parse_args()
    print(build_index(args.input, args.output_dir, args.model_dir, args.device, args.batch_size, args.max_tokens, args.limit))


if __name__ == "__main__":
    main()
