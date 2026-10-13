"""Check token budgets, table relationships and preservation of cleaned inputs."""

from copy import deepcopy
from types import SimpleNamespace
import unittest

from bs4 import BeautifulSoup

from chunking.token_aware import embedding_input, split_chunk


def chunk(text):
    return {"id": "example:p15:c0000", "document_id": "example", "title": "FIIT", "section_path": [],
            "text": text, "source_file": "raw_pdfs/example.pdf", "source_url": "https://example.org/a.pdf",
            "page_number": 15, "status": "parsed", "scope": "knowledge", "warnings": [], "kind": "pdf"}


class TokenAwareChunkingTests(unittest.TestCase):
    def setUp(self):
        # Character-count tokenizer makes exact boundary/preservation checks deterministic.
        self.tokenizer = SimpleNamespace(encode=lambda text, add_special_tokens=True: list(text))

    def test_small_chunk_keeps_its_text_id_and_source(self):
        original = chunk("Letný semester začína 16. februára 2026.")
        before = deepcopy(original)
        records = list(split_chunk(original, self.tokenizer, max_tokens=200))
        self.assertEqual(original, before)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], original["id"])
        self.assertEqual(records[0]["text"], original["text"])
        self.assertEqual(records[0]["page_number"], 15)

    def test_long_unicode_text_is_preserved_and_context_counts_toward_budget(self):
        text = "Žiadosť o štúdium. " * 80
        original = chunk(text)
        records = list(split_chunk(original, self.tokenizer, max_tokens=150))
        self.assertEqual("".join(record["text"] for record in records), text.strip())
        self.assertTrue(all(len(record["embedding_text"]) <= 150 for record in records))
        self.assertTrue(all(record["parent_chunk_id"] == original["id"] for record in records))
        self.assertEqual(len({record["id"] for record in records}), len(records))

    def test_table_headers_and_rowspan_ownership_survive_splits(self):
        text = ('<table><tr><th>Kód</th><th>Termín</th><th>Kredity</th></tr>'
                '<tr><td rowspan="2">APC_B</td><td>Riadny</td><td>6</td></tr>'
                '<tr><td>Opravný</td><td>6</td></tr>'
                '<tr><td>ALG</td><td>Riadny</td><td>5</td></tr></table>')
        records = list(split_chunk(chunk(text), self.tokenizer, max_tokens=180))
        rows = []
        for record in records:
            self.assertLessEqual(record["token_count"], 180)
            table = BeautifulSoup(record["text"], "html.parser").find("table")
            self.assertIsNotNone(table)
            self.assertEqual(table.find("tr").get_text("|"), "Kód|Termín|Kredity")
            rows.extend(row.get_text("|", strip=True) for row in table.find_all("tr")[1:])
        self.assertIn("APC_B|Riadny|6", rows)
        self.assertIn("APC_B|Opravný|6", rows)
        self.assertIn("ALG|Riadny|5", rows)

    def test_multiple_tables_and_surrounding_text_are_retained(self):
        text = ('Before. <table><tr><td>' + "Course " * 40 + '</td></tr></table> '
                'Between. <table><tr><td>' + "Credit " * 40 + '</td></tr></table> After.')
        records = list(split_chunk(chunk(text), self.tokenizer, max_tokens=160))
        joined = " ".join(record["text"] for record in records)
        for word in ("Before.", "Between.", "After."):
            self.assertIn(word, joined)
        self.assertTrue(all(record["token_count"] <= 160 for record in records))

    def test_accidental_paragraph_heading_does_not_consume_the_entire_budget(self):
        original = chunk("A very long heading. " * 40)
        original["section_path"] = ["Study", original["text"]]
        records = list(split_chunk(original, self.tokenizer, max_tokens=150))
        self.assertTrue(all(record["token_count"] <= 150 for record in records))
        self.assertTrue(all(record["embedding_context_compacted"] for record in records))
        self.assertTrue(all(record["section_path"] == original["section_path"] for record in records))
        self.assertEqual("".join(record["text"] for record in records), original["text"].strip())


if __name__ == "__main__":
    unittest.main()
