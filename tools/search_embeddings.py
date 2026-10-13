"""Search the local Qwen3 index without an external inference service."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from embeddings.qwen3 import encode_query, load_model
from tools.embed_chunks import DEFAULT_OUTPUT


def search(query, directory=DEFAULT_OUTPUT, top_k=5, device="cuda"):
    import numpy as np
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise ValueError("The embedding index is incomplete.")
    matrix = np.load(directory / manifest["vectors"], mmap_mode="r")
    model = load_model(manifest["model_directory"], device=device, max_tokens=manifest["config"]["max_tokens"])
    vector = encode_query(model, query)
    scores = np.asarray(matrix @ vector)
    indices = np.argsort(scores)[::-1][:top_k]
    records = [json.loads(line) for line in (directory / manifest["chunks"]).open(encoding="utf-8")]
    return [{"score": round(float(scores[index]), 5), **records[index]} for index in indices]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    hits = search(args.query, args.index_dir, args.top_k, args.device)
    for hit in hits:
        print(f"{hit['score']:.4f}  {hit['title']} (page {hit['page_number'] or '-'})")
        print(hit["source_url"] or hit["source_file"])
        print(hit["text"][:700] + "\n")


if __name__ == "__main__":
    main()
