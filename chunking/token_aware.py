"""Split existing chunks to a tokenizer budget; retain table rows and context.

The cleaned documents and original block-aware chunks are never modified.
Only oversized embedding inputs need this second chunking step.
"""

from copy import deepcopy
import re

from bs4 import BeautifulSoup


def embedding_input(chunk, text=None):
    fields = ["Title: " + chunk["title"]]
    if chunk.get("section_path"):
        fields.append("Section: " + " > ".join(chunk["section_path"]))
    if chunk.get("academic_years"):
        fields.append("Academic years: " + ", ".join(chunk["academic_years"]))
    if chunk.get("valid_as_of"):
        fields.append("Valid as of: " + chunk["valid_as_of"])
    return "\n".join(fields) + "\n\n" + (chunk["text"] if text is None else text)


def token_count(tokenizer, text):
    return len(tokenizer.encode(text, add_special_tokens=True))


def _blocks(text):
    result, lines, fence, depth = [], [], False, 0
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence:
            depth += len(re.findall(r"<table(?:\s|>)", line, re.I)) - len(re.findall(r"</table\s*>", line, re.I))
        lines.append(line)
        if not line.strip() and not fence and depth <= 0:
            if "\n".join(lines).strip():
                result.append("\n".join(lines).strip())
            lines = []
    if "\n".join(lines).strip():
        result.append("\n".join(lines).strip())
    return result


def _text_windows(text, fits):
    """Use Unicode character boundaries and prefer complete words; never truncate."""
    while text:
        if fits(text):
            yield text
            break
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if fits(text[:middle]):
                low = middle
            else:
                high = middle - 1
        if low == 0:
            raise ValueError("The token budget is too small for the document context and one character.")
        boundary = max(text.rfind("\n", 0, low), text.rfind(" ", 0, low))
        end = boundary + 1 if boundary >= low // 2 else low
        piece = text[:end]
        while not fits(piece):
            end -= 1; piece = text[:end]
        if not end:
            raise ValueError("Cannot fit a text fragment within the token budget.")
        yield piece
        text = text[end:]


def _table_rows(table):
    """Expand rowspans so a continued row keeps its owning cell in each fragment."""
    active, result = {}, []
    rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
    for row in rows:
        occupied, next_active = {}, {}
        for column, (cell, remaining, width) in active.items():
            occupied[column] = (cell, width)
            if remaining > 1:
                next_active[column] = (cell, remaining - 1, width)
        column = 0
        for original in row.find_all(["td", "th"], recursive=False):
            width, height = int(original.get("colspan", 1)), int(original.get("rowspan", 1))
            while any(column < start + span and start < column + width for start, (_, span) in occupied.items()):
                column += 1
            cell = deepcopy(original)
            cell.attrs.pop("rowspan", None)
            occupied[column] = (cell, width)
            if height > 1:
                next_active[column] = (cell, height - 1, width)
            column += width
        result.append("<tr>" + "".join(str(cell) for _, (cell, _) in sorted(occupied.items())) + "</tr>")
        active = next_active
    return result


def _single_table_parts(block, fits):
    soup = BeautifulSoup(block, "html.parser")
    table = soup.find("table")
    if table is None:
        yield from _text_windows(block, fits)
        return
    rows = _table_rows(table)
    if not rows:
        yield from _text_windows(block, fits)
        return
    header = rows[0] if len(rows) > 1 and fits("<table>" + rows[0] + "</table>") else ""
    body = rows[1:] if header else rows
    current = []
    for row in body:
        candidate = "<table>" + header + "".join(current + [row]) + "</table>"
        if fits(candidate):
            current.append(row)
            continue
        if current:
            yield "<table>" + header + "".join(current) + "</table>"
            current = []
        candidate = "<table>" + header + row + "</table>"
        if fits(candidate):
            current = [row]
        else:
            # A single huge row cannot be kept atomic. Retain its text in windows,
            # with the table context repeated; the complete table remains in source.
            context = BeautifulSoup(header, "html.parser").get_text(" ", strip=True)
            prefix = ("Table context: " + context + "\n\n") if context else ""
            if not fits(prefix + "x"):
                prefix = ""
            text = BeautifulSoup(row, "html.parser").get_text(" | ", strip=True)
            for piece in _text_windows(text, lambda value: fits(prefix + value)):
                yield prefix + piece
    if current:
        yield "<table>" + header + "".join(current) + "</table>"


def _table_parts(block, fits):
    ranges, depth, start = [], 0, 0
    for match in re.finditer(r"</?table(?:\s[^>]*|)>", block, re.I):
        if match.group().lower().startswith("</"):
            depth -= 1
            if depth == 0:
                ranges.append((start, match.end()))
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    if not ranges:
        yield from _text_windows(block, fits)
        return
    position = 0
    for start, end in ranges:
        if block[position:start].strip():
            yield from _text_windows(block[position:start], fits)
        yield from _single_table_parts(block[start:end], fits)
        position = end
    if block[position:].strip():
        yield from _text_windows(block[position:], fits)


def split_chunk(chunk, tokenizer, max_tokens=2048):
    """Yield embedding records with a verified token budget and parent provenance."""
    context = dict(chunk)
    context_budget = min(512, max_tokens // 3)
    if token_count(tokenizer, embedding_input(context, "")) > context_budget:
        # Some saved HTML treats an entire paragraph as a heading. Its text is
        # already in the body; do not duplicate thousands of tokens in context.
        context["section_path"] = [heading for heading in chunk.get("section_path", [])
                                   if token_count(tokenizer, heading) <= context_budget // 2]
        while context["section_path"] and token_count(tokenizer, embedding_input(context, "")) > context_budget:
            context["section_path"].pop()
        if token_count(tokenizer, embedding_input(context, "")) > context_budget:
            title_fits = lambda value: token_count(tokenizer, embedding_input(dict(context, title=value), "")) <= context_budget
            context["title"] = next(_text_windows(chunk["title"], title_fits))
    compacted = context["title"] != chunk["title"] or context.get("section_path", []) != chunk.get("section_path", [])

    def fits(text):
        return token_count(tokenizer, embedding_input(context, text)) <= max_tokens

    if fits(chunk["text"]):
        pieces = [chunk["text"]]
    else:
        pieces, current = [], []
        for block in _blocks(chunk["text"]):
            candidate = "\n\n".join(current + [block])
            if fits(candidate):
                current.append(block)
                continue
            if current:
                pieces.append("\n\n".join(current)); current = []
            if fits(block):
                current = [block]
            elif "<table" in block.lower():
                pieces.extend(_table_parts(block, fits))
            else:
                pieces.extend(_text_windows(block, fits))
        if current:
            pieces.append("\n\n".join(current))
    for index, text in enumerate(pieces):
        encoded = embedding_input(context, text)
        count = token_count(tokenizer, encoded)
        if count > max_tokens:
            raise ValueError("Token-aware chunk exceeds its configured limit.")
        yield dict(chunk, id=f"{chunk['id']}:t{index:04}" if len(pieces) > 1 else chunk["id"],
                   parent_chunk_id=chunk["id"], text=text, embedding_text=encoded,
                   token_count=count, token_aware_split=len(pieces) > 1,
                   embedding_context_compacted=compacted,
                   embedding_context={"title": context["title"], "section_path": context.get("section_path", [])})
