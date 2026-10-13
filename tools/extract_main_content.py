"""Extract the main content of saved FIIT HTML pages without fetching the web."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

from bs4 import BeautifulSoup, Comment, Tag
from markdownify import markdownify


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def html_to_markdown(content: Tag) -> str:
    content = deepcopy(content)
    preserved_tables = {}
    for table in content.find_all("table"):
        if table.find_parent("table"):
            continue
        loose_cells = any(cell.parent.name != "tr" for cell in table.find_all(["td", "th"]))
        if not loose_cells and not table.select("[rowspan], [colspan], table"):
            continue
        # Convert the surrounding text normally, then restore these tables as HTML.
        marker = "PRESERVEDTABLE" + uuid4().hex
        preserved_tables[marker] = str(table)
        table.replace_with(f"\n\n{marker}\n\n")

    result = markdownify(str(content), heading_style="ATX", bullets="-", newline_style="BACKSLASH")
    for marker, table in preserved_tables.items():
        result = result.replace(marker, table)
    return result.strip() + "\n"


def clean_content(main: Tag, source_url: str) -> tuple[Tag, list[str]]:
    clean_soup = BeautifulSoup("", "html.parser")
    for comment in main.find_all(string=lambda node: isinstance(node, Comment)):
        comment.extract()
    for node in main.select(
        "script, style, noscript, svg, nav, header, footer, form, button, "
        ".section-info-page-footer, .feedback-content, .modal, .pagination, "
        ".search-autocomplete, .search-autocomplete-overlay, .mobile-modal-menu"
    ):
        node.decompose()

    embedded_sources = []
    for frame in main.find_all("iframe"):
        source = urljoin(source_url, frame.get("src", ""))
        if not frame.get("src") or urlsplit(source).scheme not in {"http", "https"}:
            frame.decompose()
            continue
        embedded_sources.append(source)
        link = clean_soup.new_tag("a", href=source)
        link.string = (
            "Kalendár akademického roka"
            if urlsplit(source).hostname == "calendar.google.com"
            else frame.get("title") or "Vložený obsah"
        )
        frame.replace_with(link)

    for image in main.find_all("img"):
        width, height = image.get("width", ""), image.get("height", "")
        small_icon = (
            str(width).isdigit() and str(height).isdigit()
            and int(width) <= 24 and int(height) <= 24
        )
        if small_icon and not image.get("alt", "").strip():
            image.decompose()

    for node in main.find_all(["a", "img"]):
        attribute = "href" if node.name == "a" else "src"
        value = node.get(attribute)
        if value is None:
            continue
        resolved = urljoin(source_url, value)
        if urlsplit(resolved).scheme in {"http", "https", "mailto", "tel"}:
            node[attribute] = resolved
        else:
            del node[attribute]

    if not main.get_text(strip=True) and not main.find("img"):
        raise ValueError("The selected main content is empty.")
    return main, embedded_sources


def extract_content(html: str, source_url: str) -> tuple[Tag, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".content-section")
    if container is None:
        raise ValueError("Missing .content-section; this page needs a different extraction rule.")
    sections = container.select(".section-info-page-content")
    if not sections:
        raise ValueError("Missing .section-info-page-content; refusing to export the whole page.")

    clean_soup = BeautifulSoup("<main></main>", "html.parser")
    main = clean_soup.main
    heading = container.find("h1", recursive=False)
    if heading is not None:
        main.append(deepcopy(heading))
    for section in sections:
        if not any(parent in sections for parent in section.parents):
            main.append(deepcopy(section))
    return clean_content(main, source_url)


def decode_html(content: bytes):
    """Prefer intact UTF-8 over stale charset declarations from the old scraper."""
    flags = []
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        text, encoding = content.decode("utf-16"), "utf-16"
    else:
        try:
            text, encoding = content.decode("utf-8-sig"), "utf-8"
        except UnicodeDecodeError:
            declared = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", content[:4096], re.I)
            encoding = declared.group(1).decode("ascii") if declared else "windows-1250"
            try:
                text = content.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                text, encoding = content.decode("utf-8", errors="replace"), "utf-8-replaced"
    if "\x00" in text:
        # One supplied UTF-16 page was decoded and re-saved incorrectly upstream.
        # Only its surviving characters can be recovered; record that loss.
        text = text.replace("\x00", "").lstrip("\ufffd")
        flags.append("damaged_utf16_source_recovered_partially")
    if "\ufffd" in text:
        flags.append("source_contains_unrecoverable_characters")
    return text, encoding, flags


def extract_saved_page(content: bytes, source_url: str):
    """Handle FIIT content, listings, homepages and small legacy pages explicitly."""
    html, encoding, warnings = decode_html(content)
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    title = heading.get_text(" ", strip=True) if heading else soup.title.get_text(" ", strip=True) if soup.title else ""
    profile = "fiit_content"
    if not html.strip() or not soup.get_text(strip=True):
        return {"title": title, "markdown": "", "html": "", "encoding": encoding,
                "profile": "empty", "warnings": warnings + ["empty_source"], "links": [], "embedded_sources": []}
    try:
        main, embedded = extract_content(html, source_url)
    except ValueError:
        clean_soup = BeautifulSoup("<main></main>", "html.parser")
        main = clean_soup.main
        if soup.select_one("section.banner") and soup.select_one("header.main-header"):
            profile = "fiit_homepage"
            for section in soup.body.find_all("section", recursive=False):
                main.append(deepcopy(section))
            path = urlsplit(source_url).path.rstrip("/")
            if path not in {"", "/index.html", "/en.html", "/en"}:
                warnings.append("saved_homepage_instead_of_requested_page")
        elif soup.select_one("section.section-info-page"):
            profile = "fiit_listing"
            if heading:
                main.append(deepcopy(heading))
            main.append(deepcopy(soup.select_one("section.section-info-page")))
        elif soup.find("frameset"):
            profile = "legacy_frameset"
            warnings.append("frame_contents_not_in_saved_page")
            if title:
                h = clean_soup.new_tag("h1"); h.string = title; main.append(h)
            for frame in soup.find_all("frame"):
                link = clean_soup.new_tag("a", href=frame.get("src", ""))
                link.string = frame.get("name") or frame.get("src") or "Frame"
                paragraph = clean_soup.new_tag("p"); paragraph.append(link); main.append(paragraph)
        elif not soup.select_one("header.main-header") and len(content) < 100_000:
            profile = "legacy_body"
            for child in list((soup.body or soup).children):
                main.append(deepcopy(child))
        else:
            raise ValueError("Unknown page template: main content cannot be identified safely.")
        main, embedded = clean_content(main, source_url)
    links = list(dict.fromkeys(node["href"] for node in main.select("a[href]")))
    if "No data to display" in main.get_text() or "Žiadne údaje" in main.get_text():
        warnings.append("listing_contains_no_saved_entries")
    if "\ufffd" in main.get_text() and "source_contains_unrecoverable_characters" not in warnings:
        warnings.append("source_contains_unrecoverable_characters")
    # Presentation attributes from old editors have no place in the clean corpus.
    for node in main.find_all(True):
        node.attrs = {key: value for key, value in node.attrs.items()
                      if key in {"href", "src", "alt", "title", "rowspan", "colspan"}}
    return {"title": title, "markdown": html_to_markdown(main), "html": str(main),
            "encoding": encoding, "profile": profile, "warnings": warnings,
            "links": links, "embedded_sources": embedded}


def convert_file(input_path: Path, output_dir: Path, mapping_path: Path, source_url: str | None):
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    protected = [PROJECT_ROOT / "data" / folder for folder in ("markdown", "raw_html", "raw_pdfs")]
    if any(output_dir == folder or output_dir.is_relative_to(folder) for folder in protected):
        raise ValueError("Choose a separate output directory to preserve the original data.")

    if source_url is None:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8-sig"))
        key = input_path.relative_to(mapping_path.resolve().parent).as_posix()
        source_url = mapping.get(key)
    if not source_url or urlsplit(source_url).scheme not in {"http", "https"}:
        raise ValueError("Missing source URL; provide --source-url or a matching URL mapping.")

    html = input_path.read_text(encoding="utf-8-sig")
    main, embedded_sources = extract_content(html, source_url)
    markdown = html_to_markdown(main)

    # The companion HTML preserves the extracted structure for inspection.
    preview = BeautifulSoup(
        '<!doctype html><html lang="sk"><head><meta charset="utf-8"></head><body></body></html>',
        "html.parser",
    )
    preview.body.append(deepcopy(main))
    metadata = {
        "source_file": str(input_path),
        "source_url": source_url,
        "content_selector": ".content-section > h1, .content-section .section-info-page-content",
        "embedded_sources": embedded_sources,
        "embedded_content_fetched": False,
        "linked_pdf_urls": list(dict.fromkeys(
            link["href"] for link in main.select("a[href]")
            if urlsplit(link["href"]).path.lower().endswith(".pdf")
        )),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{input_path.stem}.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    (output_dir / f"{input_path.stem}.html").write_text(str(preview), encoding="utf-8")
    (output_dir / f"{input_path.stem}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Saved HTML files to extract")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "clean_markdown")
    parser.add_argument("--mapping", type=Path, default=PROJECT_ROOT / "data" / "url_mapping.json")
    parser.add_argument("--source-url", help="Explicit source URL for one input file")
    args = parser.parse_args()
    if args.source_url and len(args.inputs) != 1:
        parser.error("--source-url requires exactly one input file")
    failed = False
    for input_path in args.inputs:
        try:
            result = convert_file(input_path, args.output_dir, args.mapping, args.source_url)
            print(result)
        except (OSError, ValueError) as error:
            print(f"ERROR: {input_path}: {error}")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
