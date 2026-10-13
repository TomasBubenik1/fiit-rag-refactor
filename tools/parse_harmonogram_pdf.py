"""Parse FIIT semester schedule PDFs into Markdown and structured events."""

import argparse
from datetime import date
import json
from pathlib import Path
import re

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BULLETS = {"-", "●", "▪"}
DATE_PATTERN = re.compile(
    r"(?<!\d)(?:\d{1,2}\.\s*(?:-\s*\d{1,2}\.\s*)?\d{1,2}\.\s*\d{4}|\d{1,2}/\d{4})(?!\d)"
)


def words_to_text(words):
    """Join adjacent fragments such as '0' + '6.' without inventing a space."""
    text = ""
    previous = None
    for word in sorted(words, key=lambda word: word["x0"]):
        separator = " " if previous and word["x0"] - previous["x1"] > 1 else ""
        text += separator + word["text"]
        previous = word
    return re.sub(r"\s+", " ", text.replace("–", "-").replace("—", "-")).strip()


def read_lines(page):
    words = page.extract_words(extra_attrs=["fontname", "size"])
    if not words:
        raise ValueError("This PDF has no selectable text; it needs OCR.")
    lines = []
    for word in sorted(words, key=lambda word: (word["top"], word["x0"])):
        if not lines or abs(word["top"] - lines[-1][0]["top"]) > 2.5:
            lines.append([])
        lines[-1].append(word)
    return [sorted(line, key=lambda word: word["x0"]) for line in lines]


def parse_event(words, context):
    if words and words[0]["text"] in BULLETS:
        words = words[1:]
    text = words_to_text(words)
    match = DATE_PATTERN.search(text)
    if not match:
        return None

    label, colon, value = text.partition(":")
    if colon and DATE_PATTERN.search(value) and not DATE_PATTERN.search(label):
        return label.strip(), value.strip()

    # A wide horizontal gap separates a label from its date, or a date from an event.
    gaps = [right["x0"] - left["x1"] for left, right in zip(words, words[1:])]
    if gaps and max(gaps) > 20:
        split_at = gaps.index(max(gaps)) + 1
        left, right = words_to_text(words[:split_at]), words_to_text(words[split_at:])
        left_date = DATE_PATTERN.match(left)
        if left_date:
            return right, left
        return left.rstrip(":"), right

    if match.start() > 0:
        return text[:match.start()].strip().rstrip(":"), text[match.start():]
    if context:
        return context, text
    raise ValueError(f"Date without an event label: {text}")


def parse_entries(lines, width, page_number):
    # Only independent lists have a bullet at the start of the right column.
    right_halves = [[word for word in line if word["x0"] >= width / 2] for line in lines]
    two_columns = any(words and words[0]["text"] in BULLETS for words in right_halves)
    if two_columns:
        left_halves = [[word for word in line if word["x0"] < width / 2] for line in lines]
        lines = [line for line in left_halves + right_halves if line]

    entries, context = [], ""
    for words in lines:
        text = words_to_text(words)
        if not text or text in BULLETS:
            continue
        event = parse_event(words, context)
        if event is None:
            context = text
            entries.append({"type": "context", "text": text})
            continue
        label, value = event
        entries.append({
            "type": "event", "label": label, "value": value, "context": context,
            "source_page": page_number,
            "bbox": [round(coordinate, 2) for coordinate in (
                min(word["x0"] for word in words), min(word["top"] for word in words),
                max(word["x1"] for word in words), max(word["bottom"] for word in words),
            )],
        })
    return entries


def parse_harmonogram(input_path):
    sections, notices, body_text, title = [], [], [], None
    with pdfplumber.open(input_path) as pdf:
        page_count = len(pdf.pages)
        for number, page in enumerate(pdf.pages, start=1):
            lines = read_lines(page)
            footer = next((index for index, line in enumerate(lines)
                           if words_to_text(line) == "Upozornenie"
                           and line[0]["top"] > page.height * 0.8), None)
            if footer is None:
                raise ValueError(f"Page {number}: the schedule validity notice is missing.")
            notices.append(" ".join(words_to_text(line) for line in lines[footer + 1:]
                                    if not re.fullmatch(r"\d+\s*\|\s*\d+", words_to_text(line))))
            page_path, admission_path, section = [], None, None
            for line in lines[:footer]:
                text = words_to_text(line)
                body_text.append(text)
                is_heading = all("Bold" in word["fontname"] for word in line)
                if is_heading:
                    if max(word["size"] for word in line) >= 13:
                        if title is None:
                            title = text
                            if not re.fullmatch(r"Spresnenie harmonogramu .+ semestra \d{4}/\d{2,4}", title):
                                raise ValueError("Unsupported PDF: expected a FIIT semester schedule.")
                        page_path = [title] if text == title else [title, text]
                        heading_path = page_path
                        admission_path = None
                    elif admission_path and text.startswith(("Bakalárske", "Inžinierske", "Doktorandské")):
                        heading_path = admission_path + [text]
                    else:
                        heading_path = page_path + [text]
                        admission_path = heading_path if text.startswith("PRIJÍMACIE KONANIE") else None
                    section = {"heading_path": heading_path, "source_page": number, "entries": []}
                    sections.append(section)
                elif section is None:
                    raise ValueError(f"Page {number}: text before the first heading.")
                else:
                    section.setdefault("lines", []).append(line)
            for item in sections:
                if item["source_page"] == number:
                    item["entries"] = parse_entries(item.pop("lines", []), page.width, number)

    if not title or len(set(notices)) != 1:
        raise ValueError("Missing title or inconsistent validity notices across PDF pages.")
    validity = re.search(r"aktuálne k (\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", notices[0])
    if not validity:
        raise ValueError("The document's validity date could not be read.")
    day, month, year = map(int, validity.groups())
    return {
        "title": title, "page_count": page_count, "parser_profile": "fiit_semester_schedule",
        "academic_years": list(dict.fromkeys(re.findall(r"\b\d{4}/\d{2,4}\b", " ".join(body_text)))),
        "valid_as_of": date(year, month, day).isoformat(), "validity_notice": notices[0],
        "sections": sections,
    }


def to_markdown(document):
    parts = ["# " + document["title"], "> " + document["validity_notice"]]
    for section in document["sections"]:
        path = section["heading_path"]
        if len(path) > 1:
            parts.append("#" * len(path) + " " + path[-1])
        for entry in section["entries"]:
            if entry["type"] == "context":
                parts.append("#" * (len(path) + 1) + " " + entry["text"])
            elif entry["label"] == entry["context"]:
                parts.append("- " + entry["value"])
            else:
                parts.append(f"- **{entry['label']}:** {entry['value']}")
    parts.append(f"Zdroj: [PDF harmonogram]({document['source_url']})")
    return "\n\n".join(parts) + "\n"


def convert_file(input_path, output_dir, mapping_path, source_url=None):
    input_path, output_dir = Path(input_path).resolve(), Path(output_dir).resolve()
    for folder in ("markdown", "raw_html", "raw_pdfs"):
        if output_dir.is_relative_to(PROJECT_ROOT / "data" / folder):
            raise ValueError("Choose a separate output directory to preserve the original data.")
    if source_url is None:
        mapping_path = Path(mapping_path).resolve()
        mapping = json.loads(mapping_path.read_text(encoding="utf-8-sig"))
        source_url = mapping.get(input_path.relative_to(mapping_path.parent).as_posix())
    if not source_url or not source_url.startswith(("https://", "http://")):
        raise ValueError("Missing source URL; provide --source-url or a matching URL mapping.")
    document = parse_harmonogram(input_path)
    document.update({"source_file": str(input_path), "source_url": source_url})
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{input_path.stem}.md"
    markdown_path.write_text(to_markdown(document), encoding="utf-8")
    (output_dir / f"{input_path.stem}.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return markdown_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="A saved FIIT semester schedule PDF")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "clean_markdown")
    parser.add_argument("--mapping", type=Path, default=PROJECT_ROOT / "data" / "url_mapping.json")
    parser.add_argument("--source-url")
    args = parser.parse_args()
    try:
        print(convert_file(args.input, args.output_dir, args.mapping, args.source_url))
    except (OSError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
