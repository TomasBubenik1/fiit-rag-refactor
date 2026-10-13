"""Audit corpus coverage, provenance, page references and JSONL routing."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

if __package__:
    from .normalize_dataset import OUTPUT, DATA
    from .batch_dataset_pdfs import atomic_json
else:
    from normalize_dataset import OUTPUT, DATA
    from batch_dataset_pdfs import atomic_json


def validate(output, verify_sources=True):
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    sources = json.loads((output / "sources.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    identifiers = {item["id"] for item in manifest}
    errors, counts = [], Counter()
    if len(identifiers) != len(manifest):
        errors.append("Duplicate document IDs")
    if report["status"] != "complete" or report["unaccounted_files"]:
        errors.append("Dataset processing is incomplete")
    by_id, seen_sources = {}, set()
    for item in manifest:
        document = json.loads((output / item["json_file"]).read_text(encoding="utf-8"))
        by_id[item["id"]] = document
        if not (output / item["markdown_file"]).is_file():
            errors.append("Missing Markdown: " + item["id"])
        if document["kind"] == "pdf":
            numbers = [segment["page_number"] for segment in document["segments"]]
            if document["partial"] or numbers != list(range(1, document["page_count"] + 1)):
                errors.append("Incomplete/incorrect PDF page coverage: " + item["id"])
            counts["pdf_pages"] += len(numbers)
        if document["kind"] == "html":
            if any(marker in document.get("clean_html", "") for marker in
                   ("main-header", "main-footer", "mobile-modal-menu", "search-autocomplete")):
                errors.append("Website chrome retained: " + item["id"])
        for source in document["sources"] + document["derived_markdown_sources"]:
            seen_sources.add(source["relative_path"])
    for source in sources:
        if source["action"] in {"extracted", "derived_alias", "extracted_legacy_markdown"} and source["relative_path"] not in seen_sources:
            errors.append("Source provenance missing: " + source["relative_path"])
        if source["action"] == "unaccounted":
            errors.append("Unaccounted source: " + source["relative_path"])
        if verify_sources:
            current = hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest()
            if current != source["sha256"]:
                errors.append("Original source changed: " + source["relative_path"])
            counts["source_checksums_verified"] += 1
    chunk_ids = set()
    for bucket in ("ready", "review", "supporting"):
        with (output / f"chunks.{bucket}.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                chunk = json.loads(line)
                counts[bucket + "_chunks"] += 1
                if chunk["id"] in chunk_ids:
                    errors.append("Duplicate chunk ID: " + chunk["id"])
                chunk_ids.add(chunk["id"])
                document = by_id.get(chunk["document_id"])
                if document is None:
                    errors.append("Unknown chunk document: " + chunk["id"])
                    continue
                pages = {segment["page_number"] for segment in document["segments"]}
                if chunk["page_number"] not in pages:
                    errors.append("Incorrect chunk page: " + chunk["id"])
                if bucket == "ready" and (chunk["warnings"] or chunk["status"] != "parsed" or chunk["scope"] != "knowledge"):
                    errors.append("Review/supporting content in ready index: " + chunk["id"])
                if bucket == "review" and chunk["status"] != "needs_review":
                    errors.append("Incorrect review routing: " + chunk["id"])
                if bucket == "supporting" and chunk["scope"] != "supporting":
                    errors.append("Incorrect supporting routing: " + chunk["id"])
                text = chunk["text"].lower()
                if text.count("<table") != text.count("</table>"):
                    errors.append("Split or malformed HTML table: " + chunk["id"])
    for bucket in ("ready", "review", "supporting"):
        if counts[bucket + "_chunks"] != report["counts"].get(bucket + "_chunks", 0):
            errors.append("Chunk count mismatch: " + bucket)
    if counts["pdf_pages"] != report["pdf_extraction"]["total_pages"]:
        errors.append("PDF extraction/corpus total page count mismatch")
    with (output / "corpus.jsonl").open(encoding="utf-8") as stream:
        corpus_ids = [json.loads(line)["id"] for line in stream]
    if set(corpus_ids) != identifiers or len(corpus_ids) != len(identifiers):
        errors.append("Corpus/manifest document mismatch")
    result = {"status": "passed" if not errors else "failed", "counts": dict(counts), "errors": errors,
              "documents_checked": len(manifest), "original_files_unchanged": verify_sources and not any("source changed" in error for error in errors),
              "known_extraction_failures": len(report["failures"])}
    atomic_json(output / "validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--skip-source-hashes", action="store_true")
    args = parser.parse_args()
    return int(validate(args.output_dir.resolve(), not args.skip_source_hashes)["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
