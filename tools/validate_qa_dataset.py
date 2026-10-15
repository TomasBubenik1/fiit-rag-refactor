"""Validate FIIT QA annotations, exact evidence spans and corpus snapshot hashes."""

import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "evaluation/fiit_qa"


def read_jsonl(path):
    records = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"{path}:{number}: empty JSONL record")
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{number}: expected an object")
            records.append(record)
    return records


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reference_text(text):
    """Normalize URL display aliases only for checking duplicate HTML evidence."""
    text = re.sub(r"!?\[([^\]]*)\]\([^\n)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", "", text)
    return " ".join(html.unescape(text).split())


def validate_records(records, source_chunks):
    errors = []
    chunks = {chunk["id"]: chunk for chunk in source_chunks}
    if len(chunks) != len(source_chunks):
        errors.append("Source chunk IDs are not unique")
    ids, queries = set(), set()
    group_splits, chunk_splits = defaultdict(set), defaultdict(set)
    documents = defaultdict(list)
    for chunk in source_chunks:
        documents[chunk["document_id"]].append(reference_text(chunk["text"]))
    document_texts = {key: "\n".join(value) for key, value in documents.items()}
    required = {
        "schema_version", "id", "query", "language", "category", "type", "difficulty",
        "query_style", "answerability", "reference_answer", "required_facts", "academic_years",
        "evidence", "support_sets", "relevant_chunk_ids", "relevant_document_ids",
        "annotation_status", "annotation_note", "missing_information", "forbidden_claims",
        "split", "group_id",
    }
    for index, row in enumerate(records, 1):
        label = row.get("id", f"row {index}")
        missing = required - row.keys()
        if missing:
            errors.append(f"{label}: missing fields {sorted(missing)}")
            continue
        if not all(isinstance(row[key], str) and row[key].strip() for key in (
            "id", "query", "language", "category", "type", "difficulty", "query_style",
            "answerability", "reference_answer", "annotation_status", "split", "group_id",
        )):
            errors.append(f"{label}: expected nonempty string fields")
            continue
        if row["id"] in ids:
            errors.append(f"{label}: duplicate ID")
        ids.add(row["id"])
        normalized_query = " ".join(row["query"].casefold().split())
        if normalized_query in queries:
            errors.append(f"{label}: duplicate query")
        queries.add(normalized_query)
        list_keys = ("required_facts", "academic_years", "evidence", "support_sets",
                     "relevant_chunk_ids", "relevant_document_ids", "missing_information", "forbidden_claims")
        if not all(isinstance(row[key], list) for key in list_keys):
            errors.append(f"{label}: expected list fields")
            continue
        if not row["required_facts"] or not all(isinstance(fact, str) and fact.strip() for fact in row["required_facts"]):
            errors.append(f"{label}: missing evaluation facts/behavior")
        if row["schema_version"] != 1 or row["language"] != "sk":
            errors.append(f"{label}: unsupported schema/language")
        if row["split"] not in {"dev", "test"}:
            errors.append(f"{label}: invalid split")
        if row["difficulty"] not in {"easy", "medium", "hard"}:
            errors.append(f"{label}: invalid difficulty")
        if row["type"] not in {"factual", "procedural", "comparison", "multi_source", "needs_clarification", "unanswerable"}:
            errors.append(f"{label}: invalid question type")
        if any(not isinstance(year, str) or not re.fullmatch(r"\d{4}/\d{2}", year) for year in row["academic_years"]):
            errors.append(f"{label}: invalid academic year")
        group_splits[row["group_id"]].add(row["split"])
        behavior = row["answerability"]
        if behavior not in {"answerable", "needs_clarification", "unanswerable"}:
            errors.append(f"{label}: invalid answerability")
        if behavior == "answerable":
            if not row["evidence"] or not row["support_sets"]:
                errors.append(f"{label}: answerable question has no evidence")
            if row["missing_information"] or row["type"] in {"needs_clarification", "unanswerable"}:
                errors.append(f"{label}: inconsistent answerable fields")
        else:
            if any(row[key] for key in ("evidence", "support_sets", "relevant_chunk_ids", "relevant_document_ids")):
                errors.append(f"{label}: non-answerable question has positive retrieval labels")
            if not row["forbidden_claims"] or not row["annotation_note"] or row["type"] != behavior:
                errors.append(f"{label}: missing negative rationale/behavior")
            if behavior == "needs_clarification" and not row["missing_information"]:
                errors.append(f"{label}: missing clarification requirements")
        groups = row["support_sets"]
        if any(not isinstance(group, list) or not group or not all(isinstance(cid, str) for cid in group) for group in groups):
            errors.append(f"{label}: invalid support sets")
            continue
        flat = {cid for group in groups for cid in group}
        if sorted(flat) != row["relevant_chunk_ids"]:
            errors.append(f"{label}: inconsistent relevant chunks")
        unknown = flat - chunks.keys()
        if unknown:
            errors.append(f"{label}: unknown source chunks {sorted(unknown)}")
        expected_docs = sorted({chunks[cid]["document_id"] for cid in flat if cid in chunks})
        if expected_docs != row["relevant_document_ids"]:
            errors.append(f"{label}: inconsistent relevant documents")
        evidence_groups = []
        for evidence in row["evidence"]:
            evidence_keys = {"chunk_id", "document_id", "source_url", "source_file", "page_number",
                             "source_valid_as_of", "quotes", "equivalent_chunk_ids"}
            if not isinstance(evidence, dict) or evidence_keys - evidence.keys():
                errors.append(f"{label}: malformed evidence")
                continue
            cid = evidence["chunk_id"]
            chunk = chunks.get(cid)
            if chunk is None:
                errors.append(f"{label}: unknown canonical evidence {cid}")
                continue
            for field in ("document_id", "source_url", "source_file", "page_number"):
                if evidence[field] != chunk[field]:
                    errors.append(f"{label}: provenance mismatch {cid}/{field}")
            if evidence["source_valid_as_of"] != chunk["valid_as_of"]:
                errors.append(f"{label}: validity mismatch {cid}")
            if not isinstance(evidence["quotes"], list) or not evidence["quotes"]:
                errors.append(f"{label}: no quotes for {cid}")
                continue
            for quote in evidence["quotes"]:
                if (not isinstance(quote, dict) or not {"text", "start", "end"} <= quote.keys()
                        or not isinstance(quote["text"], str) or not quote["text"]
                        or type(quote["start"]) is not int or type(quote["end"]) is not int
                        or not 0 <= quote["start"] < quote["end"] <= len(chunk["text"])
                        or chunk["text"][quote["start"]:quote["end"]] != quote["text"]):
                    errors.append(f"{label}: invalid exact quote span in {cid}")
            alternatives = evidence["equivalent_chunk_ids"]
            if (not isinstance(alternatives, list) or not all(isinstance(alt, str) for alt in alternatives)
                    or cid not in alternatives):
                errors.append(f"{label}: invalid alternative evidence {cid}")
                continue
            evidence_groups.append(alternatives)
            for alternate in alternatives:
                other = chunks.get(alternate)
                if other is None:
                    errors.append(f"{label}: unknown alternative {alternate}")
                    continue
                if other["status"] != "parsed" or other["warnings"] or other["scope"] != "knowledge":
                    errors.append(f"{label}: non-ready evidence {alternate}")
                if alternate != cid and (
                    chunk["kind"] != "html" or other["kind"] != "html"
                    or document_texts[chunk["document_id"]] != document_texts[other["document_id"]]
                    or reference_text(chunk["text"]) != reference_text(other["text"])
                ):
                    errors.append(f"{label}: unverified alternative evidence {alternate}")
                chunk_splits[alternate].add(row["split"])
        if evidence_groups != groups:
            errors.append(f"{label}: evidence groups differ from support sets")
        if row["type"] == "multi_source" and len(groups) < 2:
            errors.append(f"{label}: multi-source question requires at least two support sets")
    if any(len(splits) > 1 for splits in group_splits.values()):
        errors.append("A support group crosses dev/test splits")
    if any(len(splits) > 1 for splits in chunk_splits.values()):
        errors.append("A labeled evidence chunk/alias crosses dev/test splits")
    if not records:
        errors.append("Dataset is empty")
    return errors


def validate(directory=DEFAULT_DATASET, corpus_directory=ROOT / "data/normalized"):
    directory, corpus_directory = Path(directory), Path(corpus_directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    records = read_jsonl(directory / "dataset.jsonl")
    chunks = read_jsonl(corpus_directory / "chunks.ready.jsonl")
    errors = validate_records(records, chunks)
    blind = read_jsonl(directory / "questions.jsonl")
    expected = [{key: row[key] for key in ("id", "query", "language", "split")} for row in records]
    if blind != expected:
        errors.append("Blind questions differ from dataset or contain unexpected fields")
    if manifest["total_questions"] != len(records):
        errors.append("Manifest question count mismatch")
    for key, counts in manifest["counts"].items():
        if counts != dict(Counter(row[key] for row in records)):
            errors.append(f"Manifest counts mismatch: {key}")
    for name, metadata in manifest["artifacts"].items():
        if sha256(directory / name) != metadata["sha256"]:
            errors.append(f"Artifact hash mismatch: {name}")
    for key, filename in (("ready_chunks", "chunks.ready.jsonl"), ("corpus", "corpus.jsonl"), ("report", "report.json")):
        if sha256(corpus_directory / filename) != manifest["corpus_snapshot"][key]["sha256"]:
            errors.append(f"Corpus snapshot changed: {filename}")
    if manifest["corpus_snapshot"]["ready_chunks"]["count"] != len(chunks):
        errors.append("Manifest source chunk count mismatch")
    return {"status": "failed" if errors else "passed", "questions_checked": len(records),
            "evidence_records_checked": sum(len(row["evidence"]) for row in records),
            "exact_quotes_checked": sum(len(e["quotes"]) for row in records for e in row["evidence"]),
            "answerability": dict(Counter(row["answerability"] for row in records)),
            "splits": dict(Counter(row["split"] for row in records)), "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--corpus-dir", type=Path, default=ROOT / "data/normalized")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = validate(args.dataset_dir, args.corpus_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"status": "failed", "errors": [str(exc)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
