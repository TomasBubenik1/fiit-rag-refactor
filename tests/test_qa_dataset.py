"""Regression checks for evidence integrity and honest retrieval denominators."""

from copy import deepcopy
from pathlib import Path
import unittest

from tools.evaluate_qa_retrieval import evaluate
from tools.validate_qa_dataset import read_jsonl, validate_records

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    chunk = {"id": "doc:p1:c0", "document_id": "doc", "kind": "pdf", "title": "Schedule",
             "text": "Teaching starts on 16 February.", "source_url": "https://example.org/source.pdf",
             "source_file": "raw_pdfs/source.pdf", "page_number": 1, "valid_as_of": "2026-02-06",
             "status": "parsed", "warnings": [], "scope": "knowledge"}
    row = {"schema_version": 1, "id": "q1", "query": "Kedy sa začína výučba?", "language": "sk",
           "category": "harmonogram", "type": "factual", "difficulty": "easy", "query_style": "standard",
           "answerability": "answerable", "reference_answer": "16. februára.", "required_facts": ["16. februára."],
           "academic_years": ["2025/26"], "annotation_status": "assistant_curated_source_checked",
           "annotation_note": "", "missing_information": [], "forbidden_claims": [], "split": "test", "group_id": "g1",
           "relevant_document_ids": ["doc"], "relevant_chunk_ids": [chunk["id"]], "support_sets": [[chunk["id"]]],
           "evidence": [{"chunk_id": chunk["id"], "document_id": "doc", "source_url": chunk["source_url"],
                         "source_file": chunk["source_file"], "page_number": 1, "source_valid_as_of": chunk["valid_as_of"],
                         "quotes": [{"text": chunk["text"], "start": 0, "end": len(chunk["text"])}],
                         "equivalent_chunk_ids": [chunk["id"]]}]}
    return row, chunk


class EvidenceIntegrityTests(unittest.TestCase):
    def test_valid_evidence_and_tampered_quote(self):
        row, chunk = fixture()
        self.assertEqual(validate_records([row], [chunk]), [])
        row["evidence"][0]["quotes"][0]["text"] = "Teaching starts on 17 February."
        self.assertTrue(any("quote span" in error for error in validate_records([row], [chunk])))

    def test_provenance_and_review_status_are_checked(self):
        row, chunk = fixture()
        row["evidence"][0]["page_number"] = 2
        chunk["warnings"] = ["ocr_requires_review"]
        errors = validate_records([row], [chunk])
        self.assertTrue(any("provenance mismatch" in error for error in errors))
        self.assertTrue(any("non-ready evidence" in error for error in errors))

    def test_evidence_cannot_leak_across_splits(self):
        row, chunk = fixture()
        other = deepcopy(row)
        other.update(id="q2", query="Kedy výučba začína?", split="dev", group_id="g2")
        self.assertTrue(any("crosses dev/test" in error for error in validate_records([row, other], [chunk])))

    def test_other_pdf_edition_is_not_an_equivalent_alias(self):
        row, chunk = fixture()
        other = {**chunk, "id": "old:p1:c0", "document_id": "old"}
        row["evidence"][0]["equivalent_chunk_ids"].append(other["id"])
        row["relevant_chunk_ids"].append(other["id"])
        row["relevant_document_ids"].append("old")
        self.assertTrue(any("unverified alternative" in error for error in validate_records([row], [chunk, other])))

    def test_nonanswerable_question_cannot_have_positive_evidence(self):
        row, chunk = fixture()
        row.update(answerability="unanswerable", type="unanswerable", annotation_note="No live data", forbidden_claims=["invented date"])
        self.assertTrue(any("positive retrieval labels" in error for error in validate_records([row], [chunk])))


class RetrievalEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_jsonl(ROOT / "evaluation/fiit_qa/dataset.jsonl")

    def test_oracle_labels_score_perfectly_on_the_actual_dataset(self):
        predictions = [{"id": row["id"], "retrieved_chunk_ids": [group[0] for group in row["support_sets"]],
                        "answerability": row["answerability"]} for row in self.rows]
        result = evaluate(self.rows, predictions, split="all")["summary"]
        self.assertEqual(result["questions"], 120)
        self.assertEqual(result["answerable_questions"], 100)
        self.assertEqual(result["complete_support@5"], 1.0)
        self.assertEqual(result["answerability_accuracy"], 1.0)

    def test_partial_evidence_is_not_complete_multi_source_support(self):
        row = next(row for row in self.rows if row["type"] == "multi_source")
        result = evaluate([row], [{"id": row["id"], "retrieved_chunk_ids": [row["support_sets"][0][0]]}], split="all")["summary"]
        self.assertEqual(result["known_evidence_hit@5"], 1.0)
        self.assertEqual(result["evidence_coverage@5"], 0.5)
        self.assertEqual(result["complete_support@5"], 0.0)
        self.assertIsNone(result["answerability_accuracy"])

    def test_missing_predictions_count_as_misses(self):
        positives = [row for row in self.rows if row["answerability"] == "answerable"][:2]
        first = positives[0]
        result = evaluate(positives, [{"id": first["id"], "retrieved_chunk_ids": [first["support_sets"][0][0]],
                                       "answerability": "answerable"}], split="all")["summary"]
        self.assertEqual(result["answerable_questions"], 2)
        self.assertEqual(result["known_evidence_hit@5"], 0.5)
        self.assertEqual(result["answerability_accuracy"], 0.5)

    def test_rank_cutoff_and_wrong_year_do_not_receive_credit(self):
        row = next(row for row in self.rows if row["category"] == "predmety" and row["answerability"] == "answerable")
        predictions = [{"id": row["id"], "retrieved_chunk_ids": ["pdf-older-edition:p1:c0", row["support_sets"][0][0]]}]
        self.assertEqual(evaluate([row], predictions, k=1, split="all")["summary"]["known_evidence_hit@1"], 0.0)
        self.assertEqual(evaluate([row], predictions, k=2, split="all")["summary"]["mrr@2"], 0.5)

    def test_no_retrieval_score_for_nonanswerable_questions(self):
        rows = [row for row in self.rows if row["answerability"] != "answerable"]
        predictions = [{"id": row["id"], "answerability": row["answerability"]} for row in rows]
        result = evaluate(rows, predictions, split="all")["summary"]
        self.assertIsNone(result["known_evidence_hit@5"])
        self.assertEqual(result["answerability_accuracy"], 1.0)

    def test_unknown_and_duplicate_question_ids_are_errors(self):
        with self.assertRaises(ValueError):
            evaluate(self.rows, [{"id": "unknown"}])
        qid = self.rows[0]["id"]
        with self.assertRaises(ValueError):
            evaluate(self.rows, [{"id": qid}, {"id": qid}])


if __name__ == "__main__":
    unittest.main()
