"""Resumable extraction of every supplied PDF, including mislabeled files."""

import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import hashlib
from functools import lru_cache
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "normalized"


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Windows readers/antivirus can briefly hold a file without delete sharing.
    # Retry the atomic rename rather than discarding the entire extraction.
    for attempt in range(12):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 11:
                raise
            time.sleep(0.02 * (attempt + 1))


def fingerprint():
    digest = hashlib.sha256()
    for name in ("parse_pdf.py", "parse_harmonogram_pdf.py"):
        digest.update((ROOT / "tools" / name).read_bytes())
    digest.update(b"pymupdf4llm=1.28.2;ocr=auto;language=slk+eng;images=true")
    return digest.hexdigest()


def pdf_inputs():
    mapping = json.loads((DATA / "url_mapping.json").read_text(encoding="utf-8-sig"))
    inputs = {}
    for folder in ("raw_pdfs", "analytics"):
        for path in sorted((DATA / folder).rglob("*")):
            if not path.is_file():
                continue
            content = path.read_bytes()
            if path.suffix.lower() != ".pdf" and not content[:1024].lstrip().startswith(b"%PDF-"):
                continue
            digest = hashlib.sha256(content).hexdigest()
            identifier = "pdf-" + digest[:20]
            item = inputs.setdefault(identifier, {"id": identifier, "sha256": digest, "sources": [],
                                                 "scope": "knowledge" if folder == "raw_pdfs" else "supporting"})
            item["sources"].append({"path": str(path.resolve()), "relative_path": path.relative_to(DATA).as_posix(),
                                    "url": mapping.get(path.relative_to(DATA).as_posix())})
            if folder == "raw_pdfs":
                item["scope"] = "knowledge"
    return list(inputs.values())


def cached_result(item, output, version):
    directory = output / "extractions" / item["id"]
    metadata = directory / "cache.json"
    if not metadata.exists():
        return None
    cached = json.loads(metadata.read_text(encoding="utf-8"))
    if cached.get("fingerprint") != version or cached.get("sha256") != item["sha256"]:
        return None
    target = Path(cached["output_json"])
    if not target.exists() or not target.with_suffix(".md").exists():
        return None
    document = json.loads(target.read_text(encoding="utf-8"))
    if document.get("partial") or len(document.get("pages", [])) != document.get("page_count"):
        return None
    return cached


@lru_cache(maxsize=1)
def verified_cache():
    report = DATA / "parsed_pdf" / "batch_report.json"
    results = {}
    if report.exists():
        for record in json.loads(report.read_text(encoding="utf-8")):
            if record.get("status") == "error" or record.get("partial"):
                continue
            target = Path(record["output_json"])
            if not target.exists() or not target.with_suffix(".md").exists():
                continue
            document = json.loads(target.read_text(encoding="utf-8"))
            if (not document.get("partial") and len(document.get("pages", [])) == document.get("page_count")
                    and record.get("processed_pages") == document["page_count"]):
                results[document["source_sha256"]] = (document, target)
    return results


def migrate_checked_cache(item, output, version):
    """Reuse the nine full extractions already verified in this workspace."""
    if item["sha256"] in verified_cache():
        document, target = verified_cache()[item["sha256"]]
        result = result_record(item, document, target, version)
        result["reused_verified_extraction"] = True
        atomic_json(output / "extractions" / item["id"] / "cache.json", result)
        return result
    return None


def result_record(item, document, target, version):
    return {"id": item["id"], "sha256": item["sha256"], "fingerprint": version,
            "output_json": str(target), "status": document["status"], "profile": document["profile"],
            "pages": document["page_count"], "processed_pages": len(document["pages"]),
            "review_pages": sum(bool(page.get("warnings")) for page in document["pages"]),
            "sources": item["sources"], "scope": item["scope"]}


def configure_inference_threads():
    """Bound ONNX sessions before the layout engine creates its models.

    PyMuPDF Layout 1.28.2 does not expose this option. Its model factories
    construct ort.SessionOptions(), so adapt that factory in this worker only.
    The runtime's returned options are still the native SessionOptions type.
    """
    import onnxruntime as ort
    if getattr(ort, "_fiit_bounded_session_options", False):
        return
    constructor = ort.SessionOptions

    def session_options():
        options = constructor()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        options.add_session_config_entry("session.inter_op.allow_spinning", "0")
        return options

    ort.SessionOptions = session_options
    ort._fiit_bounded_session_options = True


def extract_worker(item, output, version):
    # Bound native inference threads as well as Python worker processes.
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
    configure_inference_threads()
    from parse_pdf import convert_file
    output = Path(output)
    directory = output / "extractions" / item["id"]
    source = item["sources"][0]
    started = time.time()

    def progress(page, total):
        try:
            atomic_json(directory / "progress.json", {"source": source["relative_path"], "page": page,
                        "total_pages": total, "updated_at": time.time(), "started_at": started})
        except OSError:
            # A progress display is optional; final extraction output is not.
            pass

    try:
        document, target = convert_file(Path(source["path"]), directory,
                                       source_url=source["url"], progress_callback=progress,
                                       asset_dir=directory / "assets")
        result = result_record(item, document, target, version)
        result["elapsed_seconds"] = round(time.time() - started, 2)
        atomic_json(directory / "cache.json", result)
        previous_error = directory / "error.json"
        if previous_error.exists():
            old = json.loads(previous_error.read_text(encoding="utf-8"))
            atomic_json(previous_error, {"status": "resolved", "previous_error": old, "output_json": str(target)})
        return result
    except Exception as error:
        result = {"id": item["id"], "status": "error", "error": f"{type(error).__name__}: {error}",
                  "sources": item["sources"], "scope": item["scope"]}
        atomic_json(directory / "error.json", result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == DATA or any(output.is_relative_to(DATA / folder) for folder in
                            ("raw_html", "raw_pdfs", "raw_xml", "markdown", "analytics", "bot_logs", "hf_export", "models")):
        parser.error("Output must be separate from the supplied files.")
    inputs, version = pdf_inputs(), fingerprint()
    import pymupdf
    for item in inputs:
        with pymupdf.open(item["sources"][0]["path"]) as pdf:
            item["pages"] = len(pdf)
    atomic_json(output / "pdf_inputs.json", inputs)
    done, pending = [], []
    for item in inputs:
        result = cached_result(item, output, version) or migrate_checked_cache(item, output, version)
        if result:
            result.update(sources=item["sources"], scope=item["scope"])
            done.append(result)
        else:
            pending.append(item)
    pending.sort(key=lambda item: item["pages"], reverse=True)
    started = time.time()
    total_pages = sum(item["pages"] for item in inputs)

    def report(active):
        processed = sum(item.get("processed_pages", 0) for item in done)
        value = {"status": "running" if active else "complete", "total_documents": len(inputs),
                 "source_files": sum(len(item["sources"]) for item in inputs), "total_pages": total_pages,
                 "completed_documents": len(done), "processed_pages": processed,
                 "errors": sum(item["status"] == "error" for item in done),
                 "elapsed_seconds": round(time.time() - started),
                 "timing_scope": "Current command invocation, including reuse of completed extraction caches.",
                 "updated_at": time.time(), "results": done}
        atomic_json(output / "pdf_report.json", value)
        print(f"PDFs {len(done)}/{len(inputs)}, pages {processed}/{total_pages}, errors {value['errors']}", flush=True)

    report(bool(pending))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        active = {pool.submit(extract_worker, item, str(output), version): item for item in pending}
        last_report = 0
        while active:
            finished, _ = wait(active, timeout=20, return_when=FIRST_COMPLETED)
            for future in finished:
                item = active.pop(future)
                try:
                    done.append(future.result())
                except Exception as error:
                    done.append({"id": item["id"], "status": "error", "error": str(error),
                                 "sources": item["sources"], "scope": item["scope"]})
            if time.time() - last_report >= 20 or not active:
                report(bool(active))
                last_report = time.time()
    return int(any(item["status"] == "error" for item in done))


if __name__ == "__main__":
    raise SystemExit(main())
