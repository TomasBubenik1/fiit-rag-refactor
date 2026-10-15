"""Regression checks against the supplied HTML templates and chunk boundaries."""

from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from chunking.block_aware import chunk_segment
from tools.extract_main_content import extract_saved_page
from tools.normalize_dataset import canonical_url, decode_json_stream, extract_html_group, normalize_image_paths, web_stage

ROOT = Path(__file__).resolve().parents[1]


class DatasetNormalizationTests(unittest.TestCase):
    def test_exact_html_copies_share_one_document_and_keep_known_source_url(self):
        canonical = "https://example.org/programs/final.html"
        content = (f'<html><head><meta property="og:url" content="{canonical}"></head>'
                   '<body><h1>Finale 2025</h1><p><a href="guide.pdf">Guide</a></p></body></html>').encode()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            items = []
            for name, raw, url in [("final(1).html", content, None),
                                   ("alias.html", content, "https://example.org/other/alias.html"),
                                   ("final.html", content, canonical),
                                   ("final(2).html", content.replace(b"2025", b"2026"), canonical + "?year=2026")]:
                path = directory / name
                path.write_bytes(raw)
                items.append({"path": str(path), "relative_path": "raw_html/" + name, "kind": "html",
                              "sha256": hashlib.sha256(raw).hexdigest(), "source_url": url,
                              "canonical_url": canonical_url(url)})
            output = directory / "normalized"
            with patch("tools.normalize_dataset.inventory", return_value=items):
                web_stage(output)
            stage = json.loads((output / "web_stage.json").read_text(encoding="utf-8"))
            self.assertEqual(len(stage["documents"]), 2)
            self.assertEqual(stage["failures"], [])
            docs = [json.loads(path.read_text(encoding="utf-8")) for path in (output / "documents").glob("*.json")]
            shared = next(doc for doc in docs if len(doc["sources"]) == 3)
            self.assertIn("https://example.org/programs/guide.pdf", shared["segments"][0]["markdown"])
            self.assertNotIn("https://example.org/other/guide.pdf", shared["segments"][0]["markdown"])
            self.assertEqual({source["relative_path"] for source in shared["sources"]},
                             {"raw_html/final(1).html", "raw_html/final.html", "raw_html/alias.html"})
            self.assertIsNone(next(source for source in shared["sources"] if "(1)" in source["relative_path"])["source_url"])
            self.assertTrue(all(chunk["source_url"] == canonical
                                for chunk in chunk_segment(shared["segments"][0], shared)))
            self.assertEqual((directory / "final(1).html").read_bytes(), content)
            self.assertEqual(stage["html_deduplication"]["duplicate_copies"], 2)

    def test_html_byte_deduplication_keeps_saved_homepage_alias_warnings(self):
        content = (ROOT / "data/raw_html/index.html").read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        items = [{"path": str(ROOT / "data/raw_html/index.html"), "relative_path": "raw_html/" + name,
                  "sha256": digest, "source_url": url, "canonical_url": canonical_url(url)}
                 for name, url in [("missing.html", "https://www.fiit.stuba.sk/missing.html"),
                                   ("index.html", "https://www.fiit.stuba.sk/")]]
        page, sources, extraction = extract_html_group(items)
        self.assertNotIn("saved_homepage_instead_of_requested_page", page["warnings"])
        self.assertIn("saved_homepage_instead_of_requested_page",
                      next(source for source in sources if source["relative_path"].endswith("missing.html"))["warnings"])
        self.assertEqual(extraction["base_url"], "https://www.fiit.stuba.sk/")
        self.assertEqual(sources[0]["source_url"], "https://www.fiit.stuba.sk/")

    def page(self, name, url=None):
        return extract_saved_page((ROOT / "data/raw_html" / name).read_bytes(),
                                  url or "https://www.fiit.stuba.sk/" + name)

    def test_main_content_has_schedule_links_without_navigation(self):
        page = self.page("harmonogram-studia.html")
        self.assertEqual(page["profile"], "fiit_content")
        self.assertIn("harmonogram", page["markdown"].lower())
        self.assertTrue(any("harmonogram_2526" in link for link in page["links"]))
        self.assertNotIn("accessibility-settings", page["markdown"])
        self.assertNotIn("Späť na vrch", page["markdown"])
        self.assertNotIn("main-header", page["html"])

    def test_listing_extracts_entries_and_removes_filters(self):
        page = self.page("451.html")
        self.assertEqual(page["profile"], "fiit_listing")
        self.assertIn("Výberové konanie", page["markdown"])
        self.assertNotIn("Filtre a možnosti zobrazenia", page["markdown"])

    def test_wrong_homepage_alias_and_empty_source_are_explicit(self):
        good = self.page("index.html", "https://www.fiit.stuba.sk/")
        wrong = self.page("index.html", "https://www.fiit.stuba.sk/missing-article.html")
        self.assertEqual(good["markdown"], wrong["markdown"])
        self.assertNotIn("saved_homepage_instead_of_requested_page", good["warnings"])
        self.assertIn("saved_homepage_instead_of_requested_page", wrong["warnings"])
        self.assertIn("empty_source", self.page("6232.html")["warnings"])

    def test_damaged_legacy_encoding_is_flagged_and_frames_remain_references(self):
        page = self.page("_gnipova.html")
        self.assertNotIn("\x00", page["markdown"])
        self.assertIn("damaged_utf16_source_recovered_partially", page["warnings"])
        frame = self.page("_jelemenska.html")
        self.assertIn("frame_contents_not_in_saved_page", frame["warnings"])
        self.assertTrue(frame["links"])

    def test_chunk_keeps_complete_merged_table_and_original_page(self):
        table = '<table><tr><td colspan="3">' + "Course " * 900 + '</td></tr></table>'
        document = {"id": "pdf-example", "title": "Study programme", "kind": "pdf", "scope": "knowledge", "warnings": [],
                    "sources": [{"relative_path": "raw_pdfs/example.pdf", "source_url": "https://example.org/a.pdf"}]}
        segment = {"page_number": 15, "status": "parsed", "warnings": [],
                   "markdown": "## Courses\n\nIntro.\n\n" + table + "\n\nFollowing paragraph."}
        chunks = list(chunk_segment(segment, document))
        matching = [chunk for chunk in chunks if "<table>" in chunk["text"]]
        self.assertEqual(len(matching), 1)
        self.assertIn("</table>", matching[0]["text"])
        self.assertTrue(matching[0]["oversized"])
        self.assertEqual(matching[0]["section_path"], ["Courses"])
        self.assertTrue(all(chunk["page_number"] == 15 for chunk in chunks))

    def test_url_matching_discards_display_controls_but_keeps_page_identity(self):
        url = "http://www.fiit.stuba.sk/a.html?page_id=100&bw=true&font=large#bottom"
        self.assertEqual(canonical_url(url), "https://www.fiit.stuba.sk/a.html?page_id=100")
        self.assertNotEqual(canonical_url(url), canonical_url(url.replace("100", "101")))

    def test_mixed_jsonl_and_pretty_json_records_are_all_recovered(self):
        text = (ROOT / "data/bot_logs/interactions.jsonl").read_text(encoding="utf-8-sig")
        records, warnings = decode_json_stream(text)
        self.assertEqual(warnings, [])
        self.assertEqual(len(records), 14)
        self.assertTrue(all("timestamp" in record for record in records))
        recovered, warnings = decode_json_stream('{"a": 1}\ninvalid record\n{"b": 2}\n')
        self.assertEqual(recovered[0], {"a": 1})
        self.assertEqual(recovered[-1], {"b": 2})
        self.assertEqual(recovered[1]["_raw_text"], "invalid record")
        self.assertTrue(warnings)

    def test_asset_references_render_after_moving_markdown_into_the_corpus(self):
        asset = next((ROOT / "data/analytics").rglob("*.png"))
        relative = asset.relative_to(ROOT).as_posix()
        text, missing = normalize_image_paths(f"![Chart]({relative})", ROOT / "data/parsed_pdf/example.json")
        self.assertEqual(missing, [])
        self.assertIn("<" + asset.resolve().as_posix() + ">", text)

    def test_nested_sponsor_table_stays_in_one_chunk(self):
        page = self.page("sponzori-konferencie-iit.src-2010.html")
        document = {"id": "html-sponsors", "title": page["title"], "kind": "html", "scope": "knowledge", "warnings": [],
                    "sources": [{"relative_path": "raw_html/sponsors.html", "source_url": "https://www.fiit.stuba.sk/sponsors.html"}]}
        segment = {"page_number": None, "markdown": page["markdown"], "status": "parsed", "warnings": []}
        chunks = list(chunk_segment(segment, document))
        tables = [chunk for chunk in chunks if "<table" in chunk["text"]]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["text"].count("<table"), 2)
        self.assertEqual(tables[0]["text"].count("</table>"), 2)


if __name__ == "__main__":
    unittest.main()
