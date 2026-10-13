"""Regression checks against the events visually read from the source PDF."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.parse_harmonogram_pdf import convert_file, parse_harmonogram, to_markdown


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw_pdfs/harmonogram_2526_2026-02-06.pdf"
MAPPING = ROOT / "data/url_mapping.json"
SOURCE_URL = "https://www.fiit.stuba.sk/buxus/docs/organizacia_studia/harmonogram_2526_2026-02-06.pdf"

# Labels and values were checked on all three rendered pages, including both columns.
EXPECTED_GROUPS = [
    ("", "", {
        "Letný semester": "16. 02. 2026 - 31. 08. 2026",
        "Výučba v letnom semestri": "16. 02. 2026 - 15. 05. 2026",
        "Skúškové obdobie": "18. 05. 2026 - 04. 07. 2026",
        "Letné prázdniny": "06. 07. 2026 - 31. 08. 2026",
        "Začiatok akademického roka 2026/27": "14. 09. 2026",
    }),
    ("Štátne sviatky a dni pracovného pokoja a dni s prekážkou vo výučbe:", "", {
        "Rektorské voľno": "26.03.2026 (štvrtok)",
        "Veľkonočné sviatky": "03.04.2026 - 06. 04. 2026 (piatok-pondelok)",
        "IIT.SRC 2026": "29.04.2026 (streda)",
        "Sviatok práce": "01. 05. 2026 (piatok)",
        "Sviatok svätého Cyrila a Metoda": "05. 07. 2026 (nedeľa)",
    }),
    ("Náhrada výučby:", "", {
        "výučba ako v pondelok, náhrada 06. 04. 2026": "11. 05. 2026 (pondelok)",
        "výučba ako v piatok, náhrada 03. 04. 2026": "12. 05. 2026 (utorok)",
        "výučba ako v stredu, náhrada 29. 04. 2026": "13. 05. 2026 (streda)",
        "výučba ako vo štvrtok, náhrada 26. 03. 2026": "14. 05. 2026 (štvrtok)",
        "výučba ako v piatok, náhrada 01. 05. 2026": "15. 05. 2026 (piatok)",
    }),
    ("Vypísanie projektov", "BP", {
        "Zverejnenie zadaní": "01. 05. 2026",
        "Ukončenie prideľovania": "18. 05. 2026",
    }),
    ("Odovzdávanie projektov", "Letný semester", {
        "BP2": "11. 05. 2026 o 13:00",
        "DP1": "01. 06. 2026 o 13:00",
        "DP2": "18. 05. 2026 o 13:00",
        "DP3": "04. 05. 2026 o 13:00",
        "DizP2": "31. 05. 2026",
        "DizP3": "31. 08. 2026 (diz. skúška)",
        "DizP4e": "04. 05. 2026 (diz. skúška)",
        "DizP2e, DizP6e": "31. 05. 2026",
    }),
    ("Obhajoby a štátnice", "Letný semester", {
        "BP2": "09. - 10. 06. 2026",
        "DP2": "10. - 11. 06. 2026",
        "DP3": "02. - 03. 06. 2026",
        "DizP2": "17. - 18. 06. 2026",
        "DizP4e": "17. - 18. 06. 2026",
        "DizP6, DizP8e": "08/2026",
    }),
    ("Promócie", "Bakalárske", {"Bakalárske": "25. 06. 2026 (štvrtok)"}),
    ("Promócie", "Inžinierske", {"Inžinierske": "24. 06. 2026 (streda)"}),
    ("Prihlasovanie na rozvrhové akcie v ZS 2026/27", "", {
        "Zverejnenie": "16. 09. 2026 (streda)",
        "Prihlasovanie": "17. 09. 2026 (štvrtok)",
    }),
    ("Registrácia predmetov na akademický rok 2026/27", "", {"Online": "04. 06. 2026"}),
    ("Bakalárske slovenské", "", {
        "Termín podania prihlášky": "31. 03. 2026",
        "1. kolo konania prijímacej skúšky": "23. 01. 2026",
        "2. kolo konania prijímacej skúšky": "17. 04. 2026",
    }),
    ("Bakalárske anglické", "", {
        "Termín podania prihlášky": "31. 03. 2026",
        "Termín konania prijímacej skúšky": "14. - 17. 04. 2026",
    }),
    ("Inžinierske", "", {
        "Termín podania prihlášky": "31. 05. 2026",
        "Termín konania prijímacej skúšky": "22. 06. 2026",
    }),
    ("Doktorandské", "", {
        "Termín podania prihlášky": "31. 05. 2026",
        "Termín konania prijímacej skúšky": "23. 06. 2026",
    }),
]


class ScheduleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = parse_harmonogram(INPUT)
        cls.document["source_url"] = SOURCE_URL

    def test_all_event_labels_and_dates_match_the_source(self):
        expected = {(section, context, label): value
                    for section, context, events in EXPECTED_GROUPS for label, value in events.items()}
        actual, count = {}, 0
        for section in self.document["sections"]:
            name = section["heading_path"][-1] if len(section["heading_path"]) > 1 else ""
            for entry in section["entries"]:
                if entry["type"] == "event":
                    actual[(name, entry["context"], entry["label"])] = entry["value"]
                    count += 1
        self.assertEqual(actual, expected)
        self.assertEqual(count, 45)  # Also catches duplicate records collapsed by the dictionary.

    def test_validity_and_source_page_are_preserved(self):
        self.assertEqual(self.document["valid_as_of"], "2026-02-06")
        self.assertEqual(self.document["academic_years"], ["2025/26", "2026/27"])
        self.assertEqual(self.document["page_count"], 3)
        self.assertEqual(to_markdown(self.document).count("Dátumy sú aktuálne"), 1)
        for section in self.document["sections"]:
            for entry in section["entries"]:
                if entry["type"] == "event":
                    self.assertEqual(entry["source_page"], section["source_page"])
                    x0, y0, x1, y1 = entry["bbox"]
                    self.assertLess(x0, x1)
                    self.assertLess(y0, y1)

    def test_conversion_writes_reviewable_outputs_without_changing_sources(self):
        original_md = ROOT / "data/markdown/harmonogram_2526_2026-02-06.md"
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (INPUT, original_md)]
        with tempfile.TemporaryDirectory() as directory:
            result = convert_file(INPUT, directory, MAPPING)
            self.assertEqual(result.name, "harmonogram_2526_2026-02-06.md")
            self.assertIn("**BP2:** 11. 05. 2026 o 13:00", result.read_text(encoding="utf-8"))
            stored = json.loads(result.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(stored["source_url"], SOURCE_URL)
            self.assertEqual(stored["sections"], self.document["sections"])
        self.assertEqual(before, [hashlib.sha256(path.read_bytes()).hexdigest() for path in (INPUT, original_md)])
        with self.assertRaises(ValueError):
            convert_file(INPUT, ROOT / "data/markdown", MAPPING)


if __name__ == "__main__":
    unittest.main()
