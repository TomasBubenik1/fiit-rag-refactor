"""Score saved retrieval results against the FIIT QA known evidence sets."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from tools.validate_qa_dataset import DEFAULT_DATASET, read_jsonl

BEHAVIORS = {"answerable", "needs_clarification", "unanswerable"}


def evaluate(records, predictions, k=5, split="test"):
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    if split not in {"dev", "test", "all"}:
        raise ValueError("split must be dev, test or all")
    known = {row["id"] for row in records}
    saved = {}
    for prediction in predictions:
        qid = prediction.get("id")
        if qid not in known or qid in saved:
            raise ValueError(f"Unknown or duplicate prediction ID: {qid}")
        hits = prediction.get("retrieved_chunk_ids", [])
        if not isinstance(hits, list) or not all(isinstance(cid, str) and cid for cid in hits):
            raise ValueError(f"{qid}: retrieved_chunk_ids must be a list of chunk IDs")
        if len(hits) != len(set(hits)):
            raise ValueError(f"{qid}: duplicate retrieved chunk IDs")
        if "answerability" in prediction and prediction["answerability"] not in BEHAVIORS:
            raise ValueError(f"{qid}: invalid answerability")
        saved[qid] = prediction
    selected = [row for row in records if split == "all" or row["split"] == split]
    if not selected:
        raise ValueError("No questions in selected split")
    details = []
    for row in selected:
        prediction = saved.get(row["id"], {})
        hits = prediction.get("retrieved_chunk_ids", [])[:k]
        detail = {"id": row["id"], "category": row["category"],
                  "expected_answerability": row["answerability"], "prediction_present": bool(prediction),
                  "predicted_answerability": prediction.get("answerability"),
                  "behavior_correct": prediction.get("answerability") == row["answerability"]}
        if row["answerability"] == "answerable":
            support = [set(group) for group in row["support_sets"]]
            relevant = set().union(*support)
            rank = next((rank for rank, cid in enumerate(hits, 1) if cid in relevant), None)
            coverage = sum(bool(set(hits) & group) for group in support) / len(support)
            detail.update(hit=int(rank is not None), reciprocal_rank=1 / rank if rank else 0.0,
                          evidence_coverage=coverage, complete_support=int(coverage == 1.0))
        details.append(detail)

    def summarize(items):
        positives = [item for item in items if item["expected_answerability"] == "answerable"]
        denominator = len(positives)
        behavior_count = sum(item["predicted_answerability"] is not None for item in items)
        metrics = {f"{name}@{k}": round(sum(item[field] for item in positives) / denominator, 6) if denominator else None
                   for name, field in (("known_evidence_hit", "hit"), ("mrr", "reciprocal_rank"),
                                       ("evidence_coverage", "evidence_coverage"), ("complete_support", "complete_support"))}
        return {"questions": len(items), "answerable_questions": denominator,
                "predictions_present": sum(item["prediction_present"] for item in items),
                "behavior_predictions_present": behavior_count,
                "answerability_accuracy": round(sum(item["behavior_correct"] for item in items) / len(items), 6) if behavior_count else None, **metrics}

    categories = defaultdict(list)
    behaviors = defaultdict(list)
    for detail in details:
        categories[detail["category"]].append(detail)
        behaviors[detail["expected_answerability"]].append(detail)
    return {"split": split, "k": k, "summary": summarize(details),
            "by_category": {key: summarize(value) for key, value in sorted(categories.items())},
            "by_answerability": {key: summarize(value) for key, value in sorted(behaviors.items())},
            "limitations": ["Known evidence sets are not exhaustive relevance judgments.",
                            "Missing selected predictions count as misses. If behavior labels are supplied, missing labels count as incorrect; otherwise accuracy is null.",
                            "Answerability is classification only; answer text, factuality and citation correctness are not scored."],
            "details": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="test")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(read_jsonl(args.dataset_dir / "dataset.jsonl"), read_jsonl(args.predictions), args.top_k, args.split)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Evaluation failed: {exc}\n")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"split": result["split"], "k": result["k"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
