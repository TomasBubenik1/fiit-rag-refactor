"""General PDF regression checks on native text, real tables and scanned pages."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bs4 import BeautifulSoup

from tools.parse_pdf import ROOT, configure_ocr, parse_pdf


PDFS = ROOT / "data/raw_pdfs"


class GeneralPdfTests(unittest.TestCase):
    def test_schedule_is_routed_to_the_verified_profile(self):
        result = parse_pdf(PDFS / "harmonogram_2526_2026-02-06.pdf")
        self.assertEqual(result["profile"], "fiit_semester_schedule")
        events = [entry for section in result["structured_data"]["sections"]
                  for entry in section["entries"] if entry["type"] == "event"]
        self.assertEqual(len(events), 45)
        self.assertIn("**BP2:** 11. 05. 2026 o 13:00", result["markdown"])

    def test_catalog_preserves_merged_cells_course_code_and_credits(self):
        result = parse_pdf(PDFS / "katalog-predmetov_2025-26.pdf", pages=[14], ocr="off")
        page = result["pages"][0]
        table = BeautifulSoup(page["markdown"], "html.parser").table
        cells = [cell.get_text(" ", strip=True) for cell in table.find_all("td")]
        self.assertIn("Kód: APC_B", cells)
        self.assertIn("Názov: Aplikačné programovanie v C++", cells)
        self.assertIn("Počet kreditov: 6", cells)
        self.assertEqual(len(cells), 14)  # Fourteen physical cells on the rendered source page.
        self.assertTrue(table.select("[colspan]"))
        self.assertEqual(page["table_extraction"][0]["method"], "vector_cell_borders")
        self.assertEqual(page["page_number"], 15)
        self.assertEqual(result["selected_pages"], [15])
        self.assertEqual(result["page_count"], 190)
        self.assertTrue(result["partial"])

    def test_scanned_document_recovers_text_and_is_marked_for_review(self):
        if configure_ocr("slk+eng") is None:
            self.skipTest("Install OCR models with tools/setup_pdf_ocr.py")
        path = PDFS / "01-jendek.pdf"
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        result = parse_pdf(path)
        page = result["pages"][0]
        self.assertFalse(page["native_text"].strip())
        self.assertTrue(page["ocr_used"])
        self.assertGreater(len(page["markdown"]), 150)
        self.assertIn("simulator", page["markdown"].lower())
        self.assertIn("ocr_requires_review", page["warnings"])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_ocr_tracks_the_original_page_when_the_engine_uses_a_temporary_page(self):
        if configure_ocr("slk+eng") is None:
            self.skipTest("Install OCR models with tools/setup_pdf_ocr.py")
        result = parse_pdf(PDFS / "Zapisnica-VR-FIIT-STU_2012-1.pdf", pages=[1])
        self.assertEqual(result["pages"][0]["page_number"], 2)
        self.assertTrue(result["pages"][0]["ocr_used"])
        self.assertGreater(len(result["pages"][0]["markdown"]), 100)

    def test_disabling_ocr_does_not_turn_an_image_page_into_a_successful_empty_document(self):
        result = parse_pdf(PDFS / "01-jendek.pdf", ocr="off")
        self.assertFalse(result["pages"][0]["ocr_used"])
        self.assertIn("ocr_disabled", result["pages"][0]["warnings"])
        self.assertEqual(result["status"], "needs_review")

    def test_batch_continues_after_a_broken_file(self):
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.pdf"
            broken.write_bytes(b"not a PDF document")
            output = Path(directory) / "output"
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tools/parse_pdf.py"), str(broken),
                 str(PDFS / "2023-06-23_statut_fiitstu.pdf"), "--output-dir", str(output),
                 "--pages", "1", "--ocr", "off", "--no-images"],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(completed.returncode, 1)
            report = json.loads((output / "batch_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report[0]["status"], "error")
            self.assertNotEqual(report[1]["status"], "error")
            self.assertTrue(report[1]["partial"])
            self.assertTrue((output / "2023-06-23_statut_fiitstu.md").is_file())

    def test_cli_refuses_to_write_a_report_into_the_original_dataset(self):
        report_path = ROOT / "data/markdown/batch_report.json"
        before = report_path.read_bytes() if report_path.exists() else None
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools/parse_pdf.py"), str(PDFS / "01-jendek.pdf"),
             "--output-dir", str(ROOT / "data/markdown")],
            cwd=ROOT, capture_output=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(report_path.read_bytes() if report_path.exists() else None, before)


if __name__ == "__main__":
    unittest.main()
