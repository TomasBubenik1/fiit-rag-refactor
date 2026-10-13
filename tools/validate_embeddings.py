"""Check a completed local embedding index against its cleaned source chunks."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from embeddings.qwen3 import load_tokenizer
from tools.batch_dataset_pdfs import atomic_json
from tools.embed_chunks import DEFAULT_OUTPUT


def validate(directory=DEFAULT_OUTPUT):
    import numpy as np
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    progress = json.loads((directory / "progress.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    if manifest["status"] != "complete" or progress["status"] != "complete":
        raise ValueError("The index has not finished.")
    if progress["config"] != config:
        raise ValueError("The checkpoint and manifest settings differ.")
    input_path = Path(config["input_file"])
    with input_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != config["input_sha256"]:
        raise ValueError("The cleaned input changed after indexing.")
    originals = [json.loads(line) for line in input_path.open(encoding="utf-8")]
    if config["limit"] is not None:
        originals = originals[:config["limit"]]
    parents = {record["id"]: record for record in originals}
    if len(parents) != len(originals):
        raise ValueError("Source chunk IDs are not unique.")
    records = [json.loads(line) for line in (directory / manifest["chunks"]).open(encoding="utf-8")]
    matrix = np.load(directory / manifest["vectors"], mmap_mode="r")
    with (directory / manifest["vectors"]).open("rb") as stream:
        vector_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if manifest.get("vectors_sha256", vector_digest) != vector_digest:
        raise ValueError("The saved vectors changed after index completion.")
    if matrix.dtype != np.float32 or matrix.shape != (len(records), config["embedding_dimensions"]):
        raise ValueError("The vector matrix does not match the chunk rows or dtype.")
    if progress["completed_rows"] != len(records) or progress["total_rows"] != len(records):
        raise ValueError("The checkpoint does not cover every row.")
    if not np.isfinite(matrix).all():
        raise ValueError("The index contains non-finite vectors.")
    norms = np.linalg.norm(matrix, axis=1)
    if not np.allclose(norms, 1, atol=1e-4):
        raise ValueError("The index contains unnormalized or unwritten vectors.")
    tokenizer = load_tokenizer(manifest["model_directory"])
    ids, coverage, lengths = set(), Counter(), []
    for row, record in enumerate(records):
        if record["id"] in ids or record["embedding_row"] != row:
            raise ValueError("Chunk IDs or vector row alignment are invalid.")
        ids.add(record["id"])
        parent = parents[record["parent_chunk_id"]]
        coverage[parent["id"]] += 1
        for key, value in parent.items():
            if key not in ("id", "text") and record.get(key) != value:
                raise ValueError(f"Source metadata changed: {record['id']} / {key}")
        if not record["token_aware_split"] and record["text"] != parent["text"]:
            raise ValueError("An unsplit chunk changed its source text.")
        count = len(tokenizer.encode(record["embedding_text"], add_special_tokens=True))
        if count != record["token_count"] or count > config["max_tokens"]:
            raise ValueError(f"Incorrect token budget: {record['id']}")
        lengths.append(count)
    if set(coverage) != set(parents):
        raise ValueError("The index is missing source chunks.")
    report = {
        "status": "passed", "source_chunks": len(parents), "embedding_rows": len(records),
        "dimensions": matrix.shape[1], "dtype": str(matrix.dtype),
        "unique_ids": len(ids), "source_metadata_preserved": True,
        "source_input_sha256": digest, "source_input_unchanged": True,
        "tokenizer_lengths_verified": len(lengths), "maximum_tokens": max(lengths),
        "token_budget": config["max_tokens"], "non_finite_vectors": 0,
        "maximum_unit_norm_error": float(np.max(np.abs(norms - 1))),
        "vectors_sha256": vector_digest,
        "split_source_chunks": sum(count > 1 for count in coverage.values()),
    }
    atomic_json(directory / "validation.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(validate(args.index_dir), indent=2))


if __name__ == "__main__":
    main()
