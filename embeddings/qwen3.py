"""Pinned, offline Qwen3 embedding inference for the local GTX 1080 Ti."""

from pathlib import Path
import hashlib
import json
import os
import ssl
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
MODEL_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
MODEL_DIRECTORY = ROOT / ".cache" / "models" / "qwen3-embedding-0.6b"
QUERY_INSTRUCTION = "Given a question about FIIT STU, retrieve relevant passages that answer the question."


def download_model(directory=MODEL_DIRECTORY):
    import certifi
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context(cafile=certifi.where())
    metadata_url = f"https://huggingface.co/api/models/{MODEL_ID}/revision/{MODEL_REVISION}?blobs=true"
    with urllib.request.urlopen(metadata_url, context=context, timeout=60) as response:
        metadata = json.load(response)
    if metadata["sha"] != MODEL_REVISION:
        raise ValueError("Hugging Face returned a different model revision.")
    required = {"config.json", "config_sentence_transformers.json", "generation_config.json", "modules.json",
                "1_Pooling/config.json", "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "model.safetensors"}
    records = []
    for item in metadata["siblings"]:
        name = item["rfilename"]
        if name not in required:
            continue
        target = (directory / name).resolve()
        if not target.is_relative_to(directory):
            raise ValueError("Model download path escapes its cache directory.")
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = item.get("lfs", {}).get("sha256")
        def valid(path):
            if not path.is_file() or path.stat().st_size != item["size"]:
                return False
            if expected:
                with path.open("rb") as stream:
                    return hashlib.file_digest(stream, "sha256").hexdigest() == expected
            digest = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
            with path.open("rb") as stream:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            return digest.hexdigest() == item["blobId"]
        if not valid(target):
            temporary = target.with_suffix(target.suffix + ".download")
            offset = temporary.stat().st_size if temporary.exists() else 0
            request = urllib.request.Request(f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{name}",
                                             headers={"Range": f"bytes={offset}-"} if offset else {})
            with urllib.request.urlopen(request, context=context, timeout=90) as response:
                append = bool(offset and response.status == 206)
                received = offset if append else 0
                last_report = received
                with temporary.open("ab" if append else "wb") as stream:
                    while block := response.read(4 * 1024 * 1024):
                        stream.write(block); received += len(block)
                        if received - last_report >= 100 * 1024 * 1024:
                            print(f"{name}: {received / 1024**2:.0f}/{item['size'] / 1024**2:.0f} MiB", flush=True)
                            last_report = received
            if not valid(temporary):
                raise ValueError(f"Model checksum mismatch: {name}")
            temporary.replace(target)
            print(f"Downloaded and verified: {name}", flush=True)
        records.append({"file": name, "size": item["size"], "sha256": expected, "git_blob": item["blobId"]})
    if {record["file"] for record in records} != required:
        raise ValueError("Required model files are missing from the pinned revision.")
    (directory / "source.json").write_text(json.dumps({"model_id": MODEL_ID, "revision": MODEL_REVISION,
                                                       "files": records}, indent=2) + "\n", encoding="utf-8")
    return directory


def load_tokenizer(directory=MODEL_DIRECTORY):
    _offline_runtime()
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(str(directory), local_files_only=True, padding_side="left")


def load_model(directory=MODEL_DIRECTORY, device="cuda", max_tokens=2048, cuda_memory_fraction=0.5):
    _offline_runtime()
    if device == "cuda":
        if not 0 < cuda_memory_fraction <= 1:
            raise ValueError("CUDA memory fraction must be greater than 0 and at most 1.")
        # Keep the Windows GPU allocator below the shared-memory spill threshold.
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF",
                              "garbage_collection_threshold:0.5,max_split_size_mb:128")
    import torch
    from sentence_transformers import SentenceTransformer
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Check the CUDA 12.6 PyTorch build or select --device cpu.")
    if device == "cuda":
        torch.cuda.set_per_process_memory_fraction(cuda_memory_fraction)
    # Pascal has no BF16/FlashAttention support. SDPA can select its math backend.
    model = SentenceTransformer(str(directory), device=device, local_files_only=True,
                               model_kwargs={"dtype": torch.float32, "attn_implementation": "sdpa"},
                               tokenizer_kwargs={"padding_side": "left"})
    model.max_seq_length = max_tokens
    model[0].auto_model.config.use_cache = False
    model.default_prompt_name = None
    model.eval()
    return model


def _offline_runtime():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def encode_documents(model, texts, batch_size=4):
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        convert_to_numpy=True, show_progress_bar=False)


def encode_query(model, query):
    text = f"Instruct: {QUERY_INSTRUCTION}\nQuery: {query}"
    count = len(model.tokenizer.encode(text, add_special_tokens=True))
    if count > model.max_seq_length:
        raise ValueError(f"Query exceeds the configured limit: {count} > {model.max_seq_length} tokens.")
    return encode_documents(model, [text], batch_size=1)[0]
