"""Batch PDF extraction with layout detection, optional OCR and review flags."""

import argparse
from collections import Counter
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import unicodedata

import pymupdf
import pymupdf4llm

if __package__:
    from .parse_harmonogram_pdf import parse_harmonogram, to_markdown as schedule_markdown
else:
    from parse_harmonogram_pdf import parse_harmonogram, to_markdown as schedule_markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "parsed_pdf"


def check_output_directory(directory):
    directory = Path(directory).resolve()
    for folder in ("markdown", "raw_html", "raw_pdfs", "clean_markdown"):
        if directory.is_relative_to(ROOT / "data" / folder):
            raise ValueError("Choose a separate output directory to preserve existing data.")
    return directory


def configure_ocr(language):
    directory = Path(os.environ.get("TESSDATA_PREFIX", ROOT / ".cache" / "tessdata"))
    if not all((directory / f"{code}.traineddata").is_file() for code in language.split("+")):
        return None
    os.environ.setdefault("TESSDATA_PREFIX", str(directory.resolve()))
    from pymupdf4llm.ocr.tesseract_api import exec_ocr
    return exec_ocr


def split_marginalia(chunk):
    text, omitted = chunk["text"], []
    boxes = chunk.get("page_boxes", [])
    for box in sorted(boxes, key=lambda box: box["pos"][0], reverse=True):
        if box["class"] in {"page-header", "page-footer"}:
            start, end = box["pos"]
            omitted.append({"kind": box["class"], "bbox": box["bbox"], "text": chunk["text"][start:end].strip()})
            text = text[:start] + text[end:]
    # These are visual styles, not useful content. Keep tables and other HTML intact.
    text = re.sub(r"</?(?:mark|u)(?:\s[^>]*)?>", "", text)
    return text.strip(), list(reversed(omitted))


def text_coverage(native_text, extracted_text):
    def tokens(text):
        return Counter(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))
    original, extracted = tokens(native_text), tokens(extracted_text)
    return round(sum((original & extracted).values()) / sum(original.values()), 3) if original else None


def table_to_html(page, table):
    """Use physical cell borders, including merged cells, instead of guessed columns."""
    x_edges = sorted({round(cell[index], 1) for cell in table.cells for index in (0, 2)})
    y_edges = sorted({round(cell[index], 1) for cell in table.cells for index in (1, 3)})
    cells = {}
    for cell in table.cells:
        x0, y0, x1, y1 = [round(coordinate, 1) for coordinate in cell]
        column, row = x_edges.index(x0), y_edges.index(y0)
        colspan, rowspan = x_edges.index(x1) - column, y_edges.index(y1) - row
        # Preserve the PDF text order; sorting by baseline can displace underscores.
        text = page.get_text("text", clip=pymupdf.Rect(cell), sort=False).strip()
        attributes = (f' colspan="{colspan}"' if colspan > 1 else "") + (f' rowspan="{rowspan}"' if rowspan > 1 else "")
        cells[(row, column)] = f"<td{attributes}>{escape(text).replace(chr(10), '<br/>')}</td>"
    return "<table>" + "".join(
        "<tr>" + "".join(cells.get((row, column), "") for column in range(len(x_edges) - 1)) + "</tr>"
        for row in range(len(y_edges) - 1)
    ) + "</table>\n\n"


def improve_tables(page, chunk):
    boxes = chunk.get("page_boxes", [])
    table_boxes = [box for box in boxes if box["class"] == "table"]
    if not table_boxes:
        return [], []
    try:
        tables = page.find_tables(strategy="lines_strict", use_layout=False).tables
    except Exception:
        return ["table_geometry_failed"], []
    flags, methods = [], []
    for box in sorted(table_boxes, key=lambda box: box["pos"][0], reverse=True):
        region = pymupdf.Rect(box["bbox"])
        matches = [table for table in tables if (region & pymupdf.Rect(table.bbox)).get_area()
                   > max(region.get_area(), pymupdf.Rect(table.bbox).get_area()) * 0.7]
        if len(matches) != 1:
            flags.append("table_structure_requires_review")
            continue
        table = matches[0]
        replacement = table_to_html(page, table)
        start, end = box["pos"]
        chunk["text"] = chunk["text"][:start] + replacement + chunk["text"][end:]
        delta = len(replacement) - (end - start)
        for other in boxes:
            if other is box:
                other["pos"] = [start, start + len(replacement)]
            elif other["pos"][0] >= end:
                other["pos"] = [position + delta for position in other["pos"]]
        methods.append({"method": "vector_cell_borders", "bbox": list(table.bbox), "physical_cells": len(table.cells)})
    return list(dict.fromkeys(flags)), methods


def page_warnings(native, chunk, ocr_used, blank, ocr_available, images_exported):
    flags = []
    boxes = chunk.get("page_boxes", [])
    content_boxes = [box for box in boxes if box["class"] not in {"page-header", "page-footer"}]
    coverage = text_coverage(native, chunk["text"])
    if ocr_used:
        flags.append("ocr_requires_review")
    if not blank and not native.strip() and not ocr_used:
        flags.append("ocr_unavailable" if not ocr_available else "no_text_extracted")
    if coverage is not None and coverage < 0.9:
        flags.append("low_native_text_coverage")
    if "\ufffd" in chunk["text"] or any(ord(char) < 32 and char not in "\n\r\t" for char in chunk["text"]):
        flags.append("unreadable_characters")
    if any(box["class"] == "formula" for box in content_boxes):
        flags.append("formula_requires_review")
    if any(box["class"] == "picture" for box in content_boxes):
        flags.append("visual_content_requires_review")
        if not images_exported:
            flags.append("images_not_exported")
    # All words can be present even when labels and values were placed in separate blocks.
    text_boxes = [box for box in content_boxes if box["class"] in {"text", "list-item"}]
    for left in text_boxes:
        label_text = chunk["text"][slice(*left["pos"])]
        if label_text.count(":") < 2:
            continue
        for right in text_boxes:
            a, b = left["bbox"], right["bbox"]
            overlap = min(a[3], b[3]) - max(a[1], b[1])
            if b[0] >= a[2] and overlap > min(a[3] - a[1], b[3] - b[1]) * 0.6:
                flags.append("aligned_label_value_blocks_require_review")
                break
    return list(dict.fromkeys(flags)), coverage


def parse_pdf(input_path, source_url=None, pages=None, ocr="auto", language="slk+eng",
              password=None, asset_dir=None, generic=False, progress_callback=None):
    input_path = Path(input_path).resolve()
    with pymupdf.open(input_path) as pdf:
        if not pdf.is_pdf:
            raise ValueError("The input is not a PDF.")
        requires_password = pdf.needs_pass
        if requires_password and (not password or not pdf.authenticate(password)):
            raise ValueError("This PDF requires a valid password.")
        selected = sorted(set(pages)) if pages is not None else list(range(len(pdf)))
        if not selected or any(number < 0 or number >= len(pdf) for number in selected):
            raise ValueError("Requested pages are outside the PDF page range.")
        source_pages = {}
        for number in selected:
            page = pdf[number]
            widgets = [{"name": widget.field_name, "value": widget.field_value,
                        "type": widget.field_type_string, "bbox": list(widget.rect)}
                       for widget in page.widgets() or []]
            native = page.get_text()
            source_pages[number] = {
                "native_text": native, "form_fields": widgets,
                "links": [{"uri": link.get("uri"), "target_page": link.get("page"), "bbox": list(link["from"])}
                          for link in page.get_links()],
                "blank": not native.strip() and not page.get_images() and not page.get_drawings(),
            }
        result = {
            "schema_version": 1, "source_file": str(input_path), "source_url": source_url,
            "source_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "page_count": len(pdf), "selected_pages": [number + 1 for number in selected],
            "partial": len(selected) != len(pdf), "pdf_metadata": pdf.metadata,
            "profile": "generic", "pages": [],
        }
        profile_error = None
        if not generic and pages is None and not requires_password and re.search(
            r"Spresnenie\s+harmonogramu\s+.+?\s+semestra\s+\d{4}/\d{2,4}", pdf[0].get_text()
        ):
            try:
                schedule = parse_harmonogram(input_path)
                schedule["source_url"] = source_url or input_path.as_posix()
                result.update({"profile": "fiit_semester_schedule", "structured_data": schedule,
                               "markdown": schedule_markdown(schedule)})
                for number in selected:
                    page_data = dict(schedule, sections=[section for section in schedule["sections"]
                                                        if section["source_page"] == number + 1])
                    result["pages"].append({"page_number": number + 1, "markdown": schedule_markdown(page_data),
                                            "native_text": source_pages[number]["native_text"],
                                            "ocr_used": False, "warnings": [], "status": "parsed"})
                result["status"] = "parsed"
                return result
            except ValueError as error:
                profile_error = str(error)

        ocr_function = configure_ocr(language) if ocr != "off" else None
        if ocr == "force" and ocr_function is None:
            raise ValueError("OCR language models are missing. Run tools/setup_pdf_ocr.py first.")
        ocr_pages = set()

        def tracked_ocr(page, **kwargs):
            ocr_function(page, **kwargs)
            # The engine can pass a temporary one-page copy whose page.number is 0.
            ocr_pages.add(current_page)

        if asset_dir:
            Path(asset_dir).mkdir(parents=True, exist_ok=True)
        for current_page in selected:
            if progress_callback:
                progress_callback(current_page + 1, len(pdf))
            chunk = pymupdf4llm.to_markdown(
                pdf, pages=[current_page], page_chunks=True, header=True, footer=True,
                use_ocr=ocr_function is not None, force_ocr=ocr == "force",
                ocr_function=tracked_ocr if ocr_function else None,
                ocr_language=language, ocr_dpi=200, show_progress=False,
                table_output="html", force_text=True,
                write_images=asset_dir is not None,
                image_path=str(asset_dir) if asset_dir else "",
            )[0]
            number = current_page
            original = source_pages[number]
            table_flags, table_methods = improve_tables(pdf[number], chunk)
            text, marginalia = split_marginalia(chunk)
            flags, coverage = page_warnings(original["native_text"], chunk, number in ocr_pages,
                                            original["blank"], ocr_function is not None, asset_dir is not None)
            flags.extend(table_flags)
            if ocr == "off":
                flags = ["ocr_disabled" if flag == "ocr_unavailable" else flag for flag in flags]
            if profile_error:
                flags.append("schedule_profile_failed")
            review_image = None
            if not original["blank"] and len(re.findall(r"\w+", text)) < 15:
                flags.append("sparse_text_requires_review")
                if asset_dir:
                    review_image = Path(asset_dir) / f"page-{number + 1}-review.png"
                    pdf[number].get_pixmap(dpi=150, alpha=False).save(review_image)
                    text += f"\n\n![Strana {number + 1} na kontrolu]({review_image.as_posix()})"
            filled_fields = [field for field in original["form_fields"] if field["value"] not in (None, "", "Off")]
            if filled_fields:
                text += "\n\n### Vyplnené polia formulára\n\n" + "\n".join(
                    f"- **{field['name']}:** {field['value']}" for field in filled_fields
                )
            result["pages"].append({
                "page_number": number + 1, "markdown": text, "native_text": original["native_text"],
                "full_markdown": chunk["text"], "layout_boxes": chunk.get("page_boxes", []),
                "omitted_marginalia": marginalia, "form_fields": original["form_fields"],
                "links": original["links"], "table_extraction": table_methods,
                "ocr_used": number in ocr_pages, "native_token_coverage": coverage,
                "review_image": str(review_image) if review_image else None,
                "warnings": flags, "status": "needs_review" if flags else "blank" if original["blank"] else "parsed",
            })
        result["status"] = "needs_review" if any(page["warnings"] for page in result["pages"]) else "parsed"
        result["ocr_language"] = language
        result["ocr_available"] = ocr_function is not None
        if profile_error:
            result["profile_error"] = profile_error
        result["markdown"] = "\n\n".join(page["markdown"] for page in result["pages"] if page["markdown"]) + "\n"
        return result


def convert_file(input_path, output_dir=DEFAULT_OUTPUT, mapping=None, **options):
    input_path, output_dir = Path(input_path).resolve(), check_output_directory(output_dir)
    target = output_dir / f"{input_path.stem}.json"
    if target.exists() and json.loads(target.read_text(encoding="utf-8"))["source_file"] != str(input_path):
        raise ValueError("Another source already uses this output filename. Choose a separate output directory.")
    options.setdefault("source_url", (mapping or {}).get(input_path.as_posix()))
    options.setdefault("asset_dir", output_dir / f"{input_path.stem}.assets")
    document = parse_pdf(input_path, **options)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{input_path.stem}.md").write_text(document.pop("markdown"), encoding="utf-8")
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return document, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="PDF files or directories (directories are scanned recursively)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mapping", type=Path, default=ROOT / "data/url_mapping.json")
    parser.add_argument("--pages", nargs="+", type=int, help="One-based page numbers; omission processes every page")
    parser.add_argument("--ocr", choices=["auto", "off", "force"], default="auto")
    parser.add_argument("--language", default="slk+eng")
    parser.add_argument("--password-env", help="Environment variable containing the PDF password")
    parser.add_argument("--generic", action="store_true", help="Skip the optional schedule profile")
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args()
    try:
        args.output_dir = check_output_directory(args.output_dir)
    except ValueError as error:
        parser.error(str(error))
    files = list(dict.fromkeys(path.resolve() for item in args.inputs
                              for path in (sorted(item.rglob("*.pdf")) if item.is_dir() else [item])))
    if not files:
        parser.error("No PDF files found.")
    mapping = {}
    if args.mapping.exists():
        mapping = {(args.mapping.resolve().parent / key).resolve().as_posix(): value
                   for key, value in json.loads(args.mapping.read_text(encoding="utf-8-sig")).items()}
    report = []
    for path in files:
        try:
            options = {"pages": [page - 1 for page in args.pages] if args.pages is not None else None,
                       "ocr": args.ocr, "language": args.language, "generic": args.generic,
                       "password": os.environ.get(args.password_env) if args.password_env else None}
            if args.no_images:
                options["asset_dir"] = None
            document, output = convert_file(path, args.output_dir, mapping, **options)
            record = {"source_file": str(path), "output_json": str(output),
                      "status": document["status"], "profile": document["profile"],
                      "processed_pages": len(document["pages"]), "partial": document["partial"],
                      "review_pages": [page["page_number"] for page in document["pages"] if page["warnings"]]}
        except Exception as error:
            # One broken or locked PDF must not prevent processing the remaining files.
            record = {"source_file": str(path), "status": "error", "error": str(error)}
        report.append(record)
        print(f"{record['status']}: {path.name}", flush=True)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "batch_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(item["status"] == "error" for item in report))


if __name__ == "__main__":
    raise SystemExit(main())
