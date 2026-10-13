"""Regression checks against the supplied HTML templates and chunk boundaries."""

from pathlib import Path
import unittest

from chunking.block_aware import chunk_segment
from tools.extract_main_content import extract_saved_page
from tools.normalize_dataset import canonical_url, decode_json_stream, normalize_image_paths

ROOT = Path(__file__).resolve().parents[1]


class DatasetNormalizationTests(unittest.TestCase):
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
