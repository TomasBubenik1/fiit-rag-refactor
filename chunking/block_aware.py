"""Chunk cleaned document segments using Markdown blocks and a soft size target."""

import re

SCHEMA_VERSION = 1


def _markdown_blocks(text):
    """Keep tables and fenced code intact, even when longer than the chunk target."""
    blocks, current, fenced, table_depth = [], [], False, 0
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced:
            table_depth += len(re.findall(r"<table(?:\s|>)", line, flags=re.I))
            table_depth -= len(re.findall(r"</table\s*>", line, flags=re.I))
        current.append(line)
        if not line.strip() and not fenced and table_depth <= 0:
            if "\n".join(current).strip():
                blocks.append("\n".join(current).strip())
            current = []
    if "\n".join(current).strip():
        blocks.append("\n".join(current).strip())
    # Pipe tables produced by markdownify consist of one paragraph and stay intact.
    return blocks


def chunk_segment(segment, document, target=2400):
    """Yield chunks with source metadata without modifying the cleaned inputs.

    ``target`` is a soft character limit. Each segment is handled independently,
    keeping PDF page boundaries and complete tables/code blocks intact.
    """
    chunks, current, size, headings = [], [], 0, []
    context = []

    def flush():
        nonlocal current, size, context
        if current:
            text = "\n\n".join(current)
            chunks.append({"section_path": context.copy(), "text": text,
                           "oversized": len(text) > target * 2})
        current, size = [], 0

    for block in _markdown_blocks(segment["markdown"]):
        match = re.match(r"^(#{1,6})\s+(.+)$", block.splitlines()[0])
        if match:
            level = len(match.group(1))
            if size > target // 2:
                flush()
            headings = [pair for pair in headings if pair[0] < level] + [(level, match.group(2))]
        if current and size + len(block) > target:
            flush()
        if not current:
            context = [title for _, title in headings]
        current.append(block)
        size += len(block) + 2
    flush()
    source = next((item for item in document["sources"] if item.get("source_url") and not item.get("warnings")), document["sources"][0])
    for number, chunk in enumerate(chunks):
        yield {"schema_version": SCHEMA_VERSION,
               "id": f"{document['id']}:p{segment['page_number'] or 0}:c{number:04}",
               "document_id": document["id"], "title": document["title"], "kind": document["kind"],
               "scope": document["scope"], "source_url": source.get("source_url"),
               "source_file": source["relative_path"], "page_number": segment["page_number"],
               "valid_as_of": document.get("structured_data", {}).get("valid_as_of"),
               "academic_years": document.get("structured_data", {}).get("academic_years", []),
               "status": "needs_review" if document["warnings"] or segment["warnings"] else segment["status"],
               "warnings": list(dict.fromkeys(document["warnings"] + segment["warnings"])), **chunk}
