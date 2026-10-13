"""Normalize the supplied FIIT bundle into a traceable Markdown/JSON/JSONL corpus.

Run --stage web while batch_dataset_pdfs.py is working, then --stage finalize.
Original files are read only. All extraction uncertainty is explicit.
"""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, unquote
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    # Also support direct CLI execution: python tools/normalize_dataset.py.
    sys.path.insert(0, str(ROOT))

from chunking.block_aware import chunk_segment

if __package__:
    from .extract_main_content import extract_saved_page, decode_html, html_to_markdown
    from .batch_dataset_pdfs import atomic_json
else:
    from extract_main_content import extract_saved_page, decode_html, html_to_markdown
    from batch_dataset_pdfs import atomic_json

DATA = ROOT / "data"
OUTPUT = DATA / "normalized"
RAW_FOLDERS = ("raw_html", "raw_pdfs", "raw_xml", "markdown", "analytics", "bot_logs", "hf_export", "models")
ROOT_SOURCES = (
    "ablation_stage1_results.json", "ablation_stage1_v2_results.json", "evaluation_results.json",
    "eval_dataset.json", "fiit_abbreviations.json", "fiit_rag.interactions.json",
    "markdown_index_manifest.json", "md_url_mapping.json", "reindex_markdown.log", "reindex_markdown.pid",
    "search_comparison_results.json", "sitemap_relations.json", "url_mapping.json",
)
SCHEMA_VERSION = 1


def canonical_url(url):
    if not url:
        return None
    parts = urlsplit(url)
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                             if key not in {"bw", "font"}))
    scheme = "https" if parts.hostname and parts.hostname.endswith("stuba.sk") else parts.scheme.lower()
    return urlunsplit((scheme, parts.netloc.lower(), unquote(parts.path), query, ""))


def load_mapping(name):
    return json.loads((DATA / name).read_text(encoding="utf-8-sig"))


def inventory():
    mapping, md_mapping = load_mapping("url_mapping.json"), load_mapping("md_url_mapping.json")
    files = [path for folder in RAW_FOLDERS for path in (DATA / folder).rglob("*") if path.is_file()]
    files.extend(DATA / name for name in ROOT_SOURCES if (DATA / name).is_file())
    results = []
    for path in sorted(files):
        relative = path.relative_to(DATA).as_posix()
        raw = path.read_bytes()
        kind = "pdf" if raw[:1024].lstrip().startswith(b"%PDF-") else (
            "feed" if relative.startswith("raw_xml/") else
            "html" if relative.startswith("raw_html/") else
            "legacy_markdown" if relative.startswith("markdown/") else "supporting")
        results.append({"path": str(path.resolve()), "relative_path": relative, "size_bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(), "kind": kind,
                        "scope": "knowledge" if relative.split("/")[0] in RAW_FOLDERS[:4] else "supporting",
                        "source_url": mapping.get(relative) or md_mapping.get(relative),
                        "canonical_url": canonical_url(mapping.get(relative) or md_mapping.get(relative))})
    return results


def provenance(item):
    return {key: item.get(key) for key in ("path", "relative_path", "sha256", "source_url", "canonical_url")}


def write_document(document, output):
    directory = output / "documents"
    directory.mkdir(parents=True, exist_ok=True)
    document["schema_version"] = SCHEMA_VERSION
    document["markdown_file"] = (directory / (document["id"] + ".md")).relative_to(output).as_posix()
    document["json_file"] = (directory / (document["id"] + ".json")).relative_to(output).as_posix()
    header = "# " + document["title"] + "\n\n"
    url = next((source["source_url"] for source in document["sources"] if source.get("source_url")), None)
    if url:
        header += f"Source: [{url}]({url})\n\n"
    notice = document.get("structured_data", {}).get("validity_notice")
    if notice:
        header += "> " + notice + "\n\n"
    if document.get("warnings"):
        header += "> Extraction needs review: " + ", ".join(document["warnings"]) + ".\n\n"
    body = []
    for segment in document["segments"]:
        if document["kind"] == "pdf":
            body.append(f"## Page {segment['page_number']}\n\n")
        if segment.get("warnings"):
            body.append("> Review: " + ", ".join(segment["warnings"]) + ".\n\n")
        body.append(segment["markdown"].strip() + "\n\n")
    (directory / (document["id"] + ".md")).write_text(header + "".join(body), encoding="utf-8")
    atomic_json(directory / (document["id"] + ".json"), document)
    return document


def parse_feed(item):
    raw = Path(item["path"]).read_bytes()
    root = ET.fromstring(raw)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel is missing")
    entries, seen = [], set()
    for node in channel.findall(".//item"):
        link = node.findtext("link", "").strip()
        title = node.findtext("title", "").strip()
        description = node.findtext("description", "")
        key = (title, link, description)
        if key in seen:
            continue
        seen.add(key)
        entries.append({"title": title, "url": link, "published_at": node.findtext("pubDate"),
                        "guid": node.findtext("guid"),
                        "description_markdown": html_to_markdown(BeautifulSoup(description, "html.parser"))})
    title = channel.findtext("title", "RSS")
    markdown = "# " + title + "\n\n" + "\n\n".join(
        f"## [{entry['title']}]({entry['url']})\n\n" +
        (f"Published: {entry['published_at']}\n\n" if entry['published_at'] else "") + entry["description_markdown"]
        for entry in entries)
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"id": "feed-" + digest[:20], "kind": "feed", "scope": "knowledge", "title": title,
            "profile": "rss", "status": "parsed" if entries else "needs_review",
            "warnings": [] if entries else ["empty_feed"], "sources": [provenance(item)],
            "derived_markdown_sources": [], "links": [entry["url"] for entry in entries],
            "feed_metadata": {"published_at": channel.findtext("pubDate"), "language": channel.findtext("language")},
            "structured_data": {"entries": entries},
            "segments": [{"page_number": None, "markdown": markdown, "status": "parsed" if entries else "needs_review",
                          "warnings": [] if entries else ["empty_feed"]}]}


def decode_json_stream(text):
    """Accept JSONL and consecutive pretty-printed JSON values without data loss."""
    decoder, values, warnings, position = json.JSONDecoder(), [], [], 0
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        try:
            value, position = decoder.raw_decode(text, position)
            values.append(value)
        except json.JSONDecodeError as error:
            end = text.find("\n", position)
            end = len(text) if end == -1 else end
            line = text.count("\n", 0, position) + 1
            message = f"invalid_json_at_line_{line}: {error.msg}"
            warnings.append(message)
            # Retain the unparsed material in the normalized supporting export too.
            values.append({"_parse_error": message, "_raw_text": text[position:end]})
            position = end
    return values, warnings


def parse_supporting(item, output):
    path = Path(item["path"])
    identifier = "support-" + hashlib.sha256(item["relative_path"].encode()).hexdigest()[:20]
    target = output / "supporting" / identifier
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"id": identifier, "source": provenance(item), "kind": path.suffix.lower().lstrip("."),
              "scope": "supporting", "status": "preserved", "warnings": [], "output_files": []}
    try:
        suffix = path.suffix.lower()
        if suffix in {".json", ".jsonl", ".ndjson", ".csv"}:
            text, encoding, flags = decode_html(path.read_bytes())
            record.update(encoding=encoding, warnings=flags)
            if suffix == ".json":
                data = json.loads(text)
                values = data if isinstance(data, list) else [data]
                record["root_type"] = type(data).__name__
            elif suffix == ".csv":
                values = list(csv.DictReader(io.StringIO(text)))
            else:
                values, flags = decode_json_stream(text)
                record["warnings"].extend(flags)
            result = target.with_suffix(".jsonl")
            with result.open("w", encoding="utf-8") as stream:
                for number, value in enumerate(values, 1):
                    stream.write(json.dumps({"schema_version": SCHEMA_VERSION, "source_file": item["relative_path"],
                                             "record_number": number, "data": value}, ensure_ascii=False) + "\n")
            record.update(status="parsed", record_count=len(values), output_files=[result.relative_to(output).as_posix()])
        elif suffix == ".db":
            # Immutable mode reads the supplied database without creating/modifying SHM files.
            connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
            tables = []
            with connection:
                integrity = connection.execute("PRAGMA quick_check").fetchall()
                if integrity != [("ok",)]:
                    record["warnings"].append("sqlite_integrity_check_failed")
                names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                for table in names:
                    escaped = '"' + table.replace('"', '""') + '"'
                    cursor = connection.execute(f"SELECT * FROM {escaped}")
                    columns = [column[0] for column in cursor.description]
                    result = target.parent / f"{identifier}-table-{len(tables):03}.jsonl"
                    count = 0
                    with result.open("w", encoding="utf-8") as stream:
                        for row in cursor:
                            data = {key: {"encoding": "hex", "value": value.hex()} if isinstance(value, bytes) else value
                                    for key, value in zip(columns, row)}
                            count += 1
                            stream.write(json.dumps({"table": table, "record_number": count, "data": data}, ensure_ascii=False) + "\n")
                    tables.append({"name": table, "columns": columns, "records": count,
                                   "output_file": result.relative_to(output).as_posix()})
            connection.close()
            record.update(status="parsed", tables=tables, record_count=sum(table["records"] for table in tables),
                          output_files=[table["output_file"] for table in tables])
        elif suffix in {".txt", ".log", ".md", ".pid"} or not suffix:
            text, encoding, flags = decode_html(path.read_bytes())
            result = target.with_suffix(".txt")
            result.write_text(text, encoding="utf-8")
            record.update(status="parsed", encoding=encoding, warnings=flags,
                          output_files=[result.relative_to(output).as_posix()])
        else:
            # Image artifacts, SQLite SHM and the trained language model remain binary sources.
            record["preservation_reason"] = "Binary artifact; original path and checksum retained."
        if record["warnings"]:
            record["status"] = "needs_review"
    except Exception as error:
        record.update(status="error", error=f"{type(error).__name__}: {error}")
    atomic_json(target.with_suffix(".json"), record)
    return record


def web_stage(output):
    sources = inventory()
    atomic_json(output / "source_inventory.json", sources)
    documents, failures, supporting = {}, [], []
    for item in sources:
        if item["kind"] not in {"html", "feed", "supporting"}:
            continue
        if item["kind"] == "supporting":
            supporting.append(parse_supporting(item, output))
            continue
        try:
            if item["kind"] == "feed":
                document = parse_feed(item)
            else:
                page = extract_saved_page(Path(item["path"]).read_bytes(), item["source_url"] or Path(item["path"]).as_uri())
                digest = hashlib.sha256(page["markdown"].encode("utf-8")).hexdigest()
                # Empty files must retain distinct identities and their original error provenance.
                identifier = "html-" + (digest if page["markdown"].strip() else item["sha256"])[:20]
                status = "needs_review" if page["warnings"] else "parsed"
                document = {"id": identifier, "kind": "html", "scope": "knowledge", "title": page["title"] or Path(item["path"]).stem,
                            "profile": page["profile"], "status": status, "warnings": [],
                            "sources": [dict(provenance(item), warnings=page["warnings"])], "derived_markdown_sources": [],
                            "links": page["links"], "embedded_sources": page["embedded_sources"], "encoding": page["encoding"],
                            "segments": [{"page_number": None, "markdown": page["markdown"], "status": status,
                                          "warnings": page["warnings"]}], "clean_html": page["html"]}
            if document["id"] in documents:
                existing = documents[document["id"]]
                existing["sources"].extend(document["sources"])
                # A valid homepage alias can supply this content even if other requested URLs redirected there.
                if document["status"] == "parsed" and existing["status"] != "parsed":
                    existing.update(status="parsed", segments=document["segments"])
            else:
                documents[document["id"]] = document
        except Exception as error:
            failures.append({"source": provenance(item), "status": "error", "error": f"{type(error).__name__}: {error}"})
    for document in documents.values():
        write_document(document, output)
    atomic_json(output / "web_stage.json", {"documents": [document["id"] for document in documents.values()],
                                            "failures": failures, "supporting": supporting})
    print(f"Web/feed documents: {len(documents)}; extraction errors: {len(failures)}; supporting sources: {len(supporting)}", flush=True)
    return sources


def normalize_image_paths(markdown, extraction_file):
    """Make exported PDF assets render from the normalized document location."""
    changes, missing = [], []
    for match in re.finditer(r"!\[[^\]\n]*\]\(", markdown):
        start, end, depth = match.end(), match.end(), 1
        while end < len(markdown) and depth:
            if markdown[end] == "(" and (end == 0 or markdown[end - 1] != "\\"):
                depth += 1
            elif markdown[end] == ")" and (end == 0 or markdown[end - 1] != "\\"):
                depth -= 1
            end += 1
        if depth:
            continue
        value = markdown[start:end - 1].strip().strip("<>")
        if urlsplit(value).scheme in {"http", "https", "data"}:
            continue
        path = Path(value)
        candidates = [path] if path.is_absolute() else [ROOT / path, Path(extraction_file).parent / path]
        found = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
        if found:
            changes.append((start, end - 1, "<" + found.as_posix() + ">"))
        else:
            missing.append(value)
    for start, end, value in reversed(changes):
        markdown = markdown[:start] + value + markdown[end:]
    return markdown, missing


def pdf_document(item, extraction):
    sources = [{"path": source["path"], "relative_path": source["relative_path"], "source_url": source["url"],
                "canonical_url": canonical_url(source["url"]), "sha256": item["sha256"]} for source in item["sources"]]
    # Prefer the actual PDF URL when the same bytes were also saved under a page URL.
    sources.sort(key=lambda source: (not urlsplit(source.get("source_url") or "").path.lower().endswith(".pdf"),
                                    not source["relative_path"].lower().endswith(".pdf")))
    warnings = []
    metadata = extraction.get("pdf_metadata", {})
    title = metadata.get("title", "").strip()
    if not title or title.lower() in {"untitled", "document", "microsoft word"} or len(title) > 250:
        title = Path(sources[0]["path"]).stem
    pages = extraction["pages"]
    first_heading = re.search(r"^#{1,3}\s+([^\n]{4,180})", pages[0]["markdown"], flags=re.M) if pages else None
    if first_heading and (not metadata.get("title") or title == Path(sources[0]["path"]).stem):
        title = first_heading.group(1).replace("**", "").strip()
    segments = [{"page_number": page["page_number"], "markdown": page["markdown"], "status": page["status"],
                 "warnings": page.get("warnings", []), "ocr_used": page.get("ocr_used", False),
                 "native_token_coverage": page.get("native_token_coverage"),
                 "omitted_marginalia": page.get("omitted_marginalia", []),
                 "review_image": page.get("review_image"), "form_fields": page.get("form_fields", []),
                 "table_extraction": page.get("table_extraction", []),
                 "links": [dict(link, target_page=link["target_page"] + 1 if isinstance(link.get("target_page"), int)
                                and link["target_page"] >= 0 else None) for link in page.get("links", [])]} for page in pages]
    for segment in segments:
        segment["markdown"], missing = normalize_image_paths(segment["markdown"], item["output_json"])
        if missing:
            segment["warnings"] = list(dict.fromkeys(segment["warnings"] + ["referenced_asset_missing"]))
            segment["missing_assets"] = missing
            segment["status"] = "needs_review"
    document = {"id": item["id"], "kind": "pdf", "scope": item["scope"], "title": title,
                "profile": extraction["profile"], "status": "needs_review" if any(segment["warnings"] for segment in segments) else extraction["status"], "warnings": warnings,
                "sources": sources, "derived_markdown_sources": [], "segments": segments,
                "page_count": extraction["page_count"], "partial": extraction["partial"],
                "pdf_metadata": metadata, "extraction_json": item["output_json"],
                "links": list(dict.fromkeys(link["uri"] for page in pages for link in page.get("links", []) if link.get("uri")))}
    if "structured_data" in extraction:
        document["structured_data"] = extraction["structured_data"]
    if extraction["profile"] == "fiit_semester_schedule":
        schedule = extraction["structured_data"]
        for segment in segments:
            blocks = segment["markdown"].strip().split("\n\n")
            if blocks and blocks[0] == "# " + schedule["title"]:
                blocks.pop(0)
            if blocks and blocks[0] == "> " + schedule["validity_notice"]:
                blocks.pop(0)
            if blocks and blocks[-1].startswith("Zdroj: [PDF harmonogram]("):
                blocks.pop()
            segment["markdown"] = "\n\n".join(blocks)
    return document


def finalize(output, allow_partial=False):
    sources = json.loads((output / "source_inventory.json").read_text(encoding="utf-8"))
    stage = json.loads((output / "web_stage.json").read_text(encoding="utf-8"))
    pdf_report = json.loads((output / "pdf_report.json").read_text(encoding="utf-8"))
    if pdf_report["status"] != "complete" and not allow_partial:
        raise ValueError("PDF extraction is still running; finalize after it completes.")
    documents = {identifier: json.loads((output / "documents" / (identifier + ".json")).read_text(encoding="utf-8"))
                 for identifier in stage["documents"]}
    failures = stage["failures"][:]
    for item in pdf_report["results"]:
        if item["status"] == "error":
            failures.append(item)
            continue
        extraction = json.loads(Path(item["output_json"]).read_text(encoding="utf-8"))
        documents[item["id"]] = pdf_document(item, extraction)
    url_documents, path_documents = defaultdict(list), defaultdict(list)
    for document in documents.values():
        for source in document["sources"]:
            path_documents[source["relative_path"]].append(document["id"])
            if source["canonical_url"]:
                url_documents[source["canonical_url"]].append(document["id"])
    # Derived Markdown is provenance, not a second copy of the same evidence.
    for item in sources:
        if item["kind"] != "legacy_markdown":
            continue
        matches = list(dict.fromkeys(url_documents.get(item["canonical_url"], [])))
        if matches:
            for identifier in matches:
                documents[identifier]["derived_markdown_sources"].append(provenance(item))
            path_documents[item["relative_path"]].extend(matches)
        else:
            text, encoding, flags = decode_html(Path(item["path"]).read_bytes())
            identifier = "markdown-" + item["sha256"][:20]
            documents[identifier] = {"id": identifier, "kind": "markdown", "scope": "knowledge",
                                     "title": Path(item["path"]).stem, "profile": "legacy_markdown_fallback",
                                     "sources": [provenance(item)], "derived_markdown_sources": [], "links": [],
                                     "status": "needs_review", "warnings": ["raw_source_extraction_unavailable"] + flags,
                                     "segments": [{"page_number": None, "markdown": text, "status": "needs_review", "warnings": []}]}
            path_documents[item["relative_path"]].append(identifier)
    counts, warnings = Counter(), Counter()
    manifest, edges, seen_edges = [], [], set()
    review_rows = []
    ready = (output / "chunks.ready.jsonl").open("w", encoding="utf-8")
    review = (output / "chunks.review.jsonl").open("w", encoding="utf-8")
    support = (output / "chunks.supporting.jsonl").open("w", encoding="utf-8")
    corpus = (output / "corpus.jsonl").open("w", encoding="utf-8")
    try:
        for document in sorted(documents.values(), key=lambda doc: doc["id"]):
            write_document(document, output)
            corpus.write(json.dumps(document, ensure_ascii=False) + "\n")
            counts["documents"] += 1; counts[document["kind"] + "_documents"] += 1
            counts[document["scope"] + "_documents"] += 1
            counts["source_aliases"] += len(document["sources"])
            for segment in document["segments"]:
                counts["segments"] += 1
                counts["ocr_pages"] += int(segment.get("ocr_used", False))
                counts["review_segments"] += int(bool(document["warnings"] or segment["warnings"]))
                warnings.update(set(document["warnings"] + segment["warnings"]))
                if document["warnings"] or segment["warnings"]:
                    review_rows.append({"document_id": document["id"], "title": document["title"],
                        "page_number": segment["page_number"], "markdown_file": document["markdown_file"],
                        "source_url": document["sources"][0].get("source_url"),
                        "warnings": "; ".join(dict.fromkeys(document["warnings"] + segment["warnings"])),
                        "review_image": segment.get("review_image")})
                for chunk in chunk_segment(segment, document):
                    destination = support if chunk["scope"] == "supporting" else review if chunk["status"] == "needs_review" else ready
                    destination.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    bucket = "supporting_chunks" if destination is support else "review_chunks" if destination is review else "ready_chunks"
                    counts[bucket] += 1
                    counts["oversized_chunks"] += int(chunk["oversized"])
            for url in document["links"] + document.get("embedded_sources", []):
                canonical = canonical_url(url)
                targets = list(dict.fromkeys(url_documents.get(canonical, [])))
                key = (document["id"], canonical)
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"source_document_id": document["id"], "target_url": url,
                                  "target_document_ids": targets, "available_in_bundle": bool(targets)})
            manifest.append({key: document.get(key) for key in ("id", "kind", "scope", "title", "status", "profile", "page_count",
                                                                 "markdown_file", "json_file", "sources", "derived_markdown_sources")})
    finally:
        for stream in (ready, review, support, corpus):
            stream.close()
    support_by_path = {record["source"]["relative_path"]: record for record in stage["supporting"]}
    failure_paths = {failure["source"]["relative_path"]: failure for failure in failures if "source" in failure}
    for failure in failures:
        for source in failure.get("sources", []):
            failure_paths[source["relative_path"]] = failure
    accounted = []
    for item in sources:
        identifiers = list(dict.fromkeys(path_documents.get(item["relative_path"], [])))
        result = dict(item, document_ids=identifiers)
        if identifiers:
            if item["kind"] == "legacy_markdown":
                result["action"] = "extracted_legacy_markdown" if all(documents[identifier]["profile"] == "legacy_markdown_fallback"
                                                                     for identifier in identifiers) else "derived_alias"
            else:
                result["action"] = "extracted"
        elif item["relative_path"] in support_by_path:
            metadata = support_by_path[item["relative_path"]]
            result.update(action=metadata["status"], supporting_id=metadata["id"])
        elif item["relative_path"] in failure_paths:
            result.update(action="error", error=failure_paths[item["relative_path"]].get("error"))
        else:
            result["action"] = "unaccounted"
        accounted.append(result)
    # Preserve evaluation references while making old document names usable with this corpus.
    evaluation = []
    for query in load_mapping("eval_dataset.json"):
        copied = dict(query, normalized_relevant_docs=[], normalized_references=[], unresolved_relevant_docs=[])
        for name in query.get("relevant_docs", []):
            reference = Path(name)
            candidates = [item for item in accounted if item["kind"] == "legacy_markdown" and
                          (Path(item["path"]).name == reference.name or
                           (not reference.suffix and Path(item["path"]).stem == reference.name))]
            identifiers = list(dict.fromkeys(identifier for item in candidates for identifier in item["document_ids"]))
            copied["normalized_relevant_docs"].extend(identifiers)
            copied["normalized_references"].append({"original_name": name, "document_ids": identifiers})
            if not identifiers:
                copied["unresolved_relevant_docs"].append(name)
        copied["normalized_relevant_docs"] = list(dict.fromkeys(copied["normalized_relevant_docs"]))
        evaluation.append(copied)
    atomic_json(output / "evaluation.normalized.json", evaluation)
    glossary = load_mapping("fiit_abbreviations.json")
    glossary_source = next(item for item in sources if item["relative_path"] == "fiit_abbreviations.json")
    atomic_json(output / "abbreviations.json", {"schema_version": SCHEMA_VERSION, "source": provenance(glossary_source),
                "metadata": glossary["metadata"], "entries": [dict(code=code, **value) for code, value in glossary["abbreviations"].items()]})
    atomic_json(output / "manifest.json", manifest)
    write_catalog(output, manifest)
    with (output / "review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["document_id", "title", "page_number", "markdown_file", "source_url", "warnings", "review_image"])
        writer.writeheader(); writer.writerows(review_rows)
    atomic_json(output / "sources.json", accounted)
    atomic_json(output / "links.json", edges)
    report = {"schema_version": SCHEMA_VERSION, "status": "complete" if pdf_report["status"] == "complete" else "partial",
              "counts": dict(counts), "input_files": len(sources),
              "source_actions": dict(Counter(item["action"] for item in accounted)),
              "input_categories": dict(Counter(item["relative_path"].split("/")[0] if "/" in item["relative_path"] else "root_metadata" for item in sources)),
              "pdf_extraction": {key: value for key, value in pdf_report.items() if key != "results"},
              "warnings_by_segment": dict(warnings), "failures": failures,
              "supporting": {"files": len(stage["supporting"]), "states": dict(Counter(item["status"] for item in stage["supporting"]))},
              "link_resolution": {"links": len(edges), "available_in_bundle": sum(edge["available_in_bundle"] for edge in edges)},
              "evaluation_references": {"queries": len(evaluation),
                  "references": sum(len(query["relevant_docs"]) for query in evaluation),
                  "unresolved": sum(len(query["unresolved_relevant_docs"]) for query in evaluation)},
              "query_expansion_abbreviations": len(glossary["abbreviations"]),
              "unaccounted_files": [item["relative_path"] for item in accounted if item["action"] == "unaccounted"]}
    atomic_json(output / "report.json", report)
    readme(output, report)
    print(json.dumps({"counts": dict(counts), "source_actions": report["source_actions"], "failures": len(failures)}, indent=2), flush=True)
    return report


def write_catalog(output, manifest):
    rows = sorted(manifest, key=lambda item: (item["scope"], item["kind"], item["title"].casefold()))
    with (output / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["id", "title", "kind", "scope", "status", "page_count", "markdown_file", "source_url", "source_aliases"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in rows:
            writer.writerow({**{field: item.get(field) for field in fields[:-2]},
                             "source_url": item["sources"][0].get("source_url"), "source_aliases": len(item["sources"])})
    lines = ["# Document index", "", "Search by title. Source aliases and extraction details are in `manifest.json`.", "",
             "| Document | Kind | Pages | Status |", "| --- | --- | ---: | --- |"]
    for item in rows:
        label = re.sub(r"[\r\n\t]+", " ", item["title"]).replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")
        lines.append(f"| [{label}]({item['markdown_file']}) | {item['kind']} | {item.get('page_count') or ''} | {item['status']} |")
    (output / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def readme(output, report):
    text = """# Normalized FIIT dataset

The original bundle is unchanged. This directory was generated from saved files; no fresh web content was fetched.

- `documents/*.md`: readable main content with source URLs and PDF page boundaries.
- `documents/*.json`: common document schema, provenance, segments, links and quality flags.
- `corpus.jsonl`: the same documents, one JSON object per line.
- `chunks.ready.jsonl`: knowledge chunks with no detected extraction warnings; suitable for initial RAG ingestion.
- `chunks.review.jsonl`: extracted knowledge requiring review (OCR, damaged encoding, table ambiguity, empty/incorrect snapshots).
- `chunks.supporting.jsonl`: extracted analytics PDFs, separate from faculty knowledge.
- `manifest.json`: document index, original aliases and paths to readable outputs.
- `INDEX.md` and `catalog.csv`: searchable document titles with links to readable outputs.
- `sources.json`: every supplied file, SHA-256, source URL and processing outcome. Markdown derivatives point to their normalized raw source.
- `links.json`: links between documents plus references not included in the bundle.
- `evaluation.normalized.json`: original evaluation questions and matching normalized document IDs.
- `abbreviations.json`: the supplied glossary as structured entries for query expansion; ambiguity flags and categories are preserved.
- `supporting/`: normalized JSON/JSONL/CSV, logs and read-only SQLite exports; binary images/models retain original paths and checksums.
- `extractions/`: detailed PDF extraction diagnostics, original native text, layout boxes, images and resumable cache.
- `report.json`: coverage counts, failures and quality flags.
- `review.csv`: document/page list for inspecting extraction warnings.
- `validation.json` and `quality_checks.json`: full corpus audit and regression/integration check results.

## Format and use

UTF-8 throughout. A document has `id`, `kind`, `scope`, `title`, `profile`, `status`, `sources`, `segments` and `warnings`.
Each PDF segment represents one original page, numbered from 1. HTML/feed segments have `page_number: null`.
Internal PDF link target pages also start at 1; URLs without an internal target have `target_page: null`.
Sources include the original path, URL and checksum; aliases preserve duplicate URLs and legacy Markdown provenance.
Header/footer text from PDFs is stored in `omitted_marginalia`; website navigation, menus and interface controls are removed.
Complex tables retain HTML cells and merged spans instead of flattening into ambiguous text.

The cleaned Markdown, document JSON and `corpus.jsonl` can be used independently of any chunking method.
Chunk files are derived outputs; another method can reuse these documents without parsing the originals again.
The current method is implemented in `chunking/block_aware.py`, with one file per chunking method.

Chunks include document ID, title, heading context, source URL, original source file, page, text and review status.
Semester schedule chunks also retain `valid_as_of` and `academic_years`; the readable document prints the validity notice once.
Chunks stay within a page and retain complete tables/code blocks. `oversized: true` identifies atomic blocks larger than the target.
The chunk target is 2,400 characters; it is not a model-specific token limit. Embeddings are deliberately not generated.
Do not ingest review/supporting chunks into faculty knowledge until they have been inspected.
`parsed` means no automated extraction issue was detected; it does not establish factual correctness or current validity.
The bundle contains historical documents as well as recent ones. Dates and academic years in the content are preserved.
Unresolved links and embedded calendars are references, not fabricated document contents.
Some originally requested URLs saved the homepage instead; their alias warnings remain in `sources` even when a valid homepage copy exists.

## Reproduce or resume

```powershell
.\\.venv\\Scripts\\python.exe tools/normalize_dataset.py --stage web
.\\.venv\\Scripts\\python.exe tools/batch_dataset_pdfs.py --workers 3
.\\.venv\\Scripts\\python.exe tools/normalize_dataset.py --stage finalize
```

PDF jobs reuse complete extractions when source SHA-256, parser code fingerprint and extraction options match.
The nine complete PDF extractions already validated in this workspace are reused with their original detailed outputs.
An interrupted PDF is rerun; completed PDFs are skipped. Originals are never overwritten.
"""
    text += "\n## Run results\n\n```json\n" + json.dumps({"input_files": report["input_files"],
        "counts": report["counts"], "source_actions": report["source_actions"], "failures": len(report["failures"])}, indent=2) + "\n```\n"
    (output / "README.md").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["web", "finalize", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--allow-partial", action="store_true", help="Explicitly produce a partial snapshot while PDFs run")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == DATA or any(output.is_relative_to(DATA / folder) for folder in RAW_FOLDERS):
        parser.error("Output must be separate from the supplied files.")
    if args.stage in {"web", "all"}:
        web_stage(output)
    if args.stage in {"finalize", "all"}:
        result = finalize(output, args.allow_partial)
        return int(bool(result["unaccounted_files"] or result["failures"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
