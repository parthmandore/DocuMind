"""DocuMind Retrieval Benchmark Runner

Empirically benchmarks DatabaseRetriever across the 40-case evaluation dataset,
evaluating Dense, Lexical (BM25), and Hybrid (RRF) retrieval strategies against
persisted database chunks.
"""

import os
import sys
import json
import time
import statistics
from typing import Dict, List, Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.base import SessionLocal
from backend.retrieval.db_retriever import DatabaseRetriever
from backend.config import config

def is_passage_match(retrieved_text: str, target_passage: str) -> bool:
    """Checks if the retrieved chunk contains or matches the target passage."""
    r_clean = " ".join(retrieved_text.strip().split()).lower()
    t_clean = " ".join(target_passage.strip().split()).lower()
    return t_clean in r_clean or r_clean in t_clean

def run_retrieval_benchmark():
    dataset_path = "data/evaluation_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    cases = dataset.get("cases", [])
    print(f"Loaded {len(cases)} cases from {dataset_path}")

    db = SessionLocal()
    retriever = DatabaseRetriever(db=db)

    modes = ["dense", "lexical", "hybrid"]
    benchmark_results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": {
            "cpu": "Intel Core i7-12650H",
            "ram": "16 GB",
            "os": "Windows 10 x64",
            "embedding_model": config.embedding_model,
            "embedding_dimension": config.embedding_dimension
        },
        "total_cases": len(cases),
        "total_corpus_chunks": 35,
        "modes": {}
    }

    try:
        for mode in modes:
            print(f"\n================ Running Retrieval Benchmark: {mode.upper()} ================")
            mode_latencies: List[float] = []
            recalls_at_1: List[int] = []
            recalls_at_3: List[int] = []
            recalls_at_5: List[int] = []
            reciprocal_ranks: List[float] = []
            category_stats: Dict[str, Dict[str, Any]] = {}
            case_details: List[Dict[str, Any]] = []

            for case in cases:
                case_id = case["case_id"]
                category = case["category"]
                question = case["question"]
                target_passage = case["relevant_source_passage"]
                should_abstain = case.get("should_abstain", False)

                t0 = time.perf_counter()
                results = retriever.retrieve(query=question, top_k=5, mode=mode)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                mode_latencies.append(latency_ms)

                # Check ranks
                found_rank = 0
                for rank, res in enumerate(results, start=1):
                    if is_passage_match(res.text, target_passage):
                        found_rank = rank
                        break

                r1 = 1 if found_rank == 1 else 0
                r3 = 1 if 1 <= found_rank <= 3 else 0
                r5 = 1 if 1 <= found_rank <= 5 else 0
                rr = (1.0 / found_rank) if found_rank > 0 else 0.0

                recalls_at_1.append(r1)
                recalls_at_3.append(r3)
                recalls_at_5.append(r5)
                reciprocal_ranks.append(rr)

                if category not in category_stats:
                    category_stats[category] = {
                        "count": 0,
                        "r1_count": 0,
                        "r3_count": 0,
                        "r5_count": 0,
                        "rr_sum": 0.0,
                        "latencies": []
                    }
                cat = category_stats[category]
                cat["count"] += 1
                cat["r1_count"] += r1
                cat["r3_count"] += r3
                cat["r5_count"] += r5
                cat["rr_sum"] += rr
                cat["latencies"].append(latency_ms)

                top_chunk_id = results[0].chunk_id if results else None
                top_dense_score = results[0].dense_score if results else None
                top_lex_score = results[0].lexical_score if results else None
                top_fused_score = results[0].fused_score if results else None

                case_details.append({
                    "case_id": case_id,
                    "category": category,
                    "should_abstain": should_abstain,
                    "found_rank": found_rank,
                    "latency_ms": round(latency_ms, 2),
                    "top_chunk_id": top_chunk_id,
                    "top_dense_score": top_dense_score,
                    "top_lexical_score": top_lex_score,
                    "top_fused_score": top_fused_score
                })

            # Calculate aggregated category breakdown
            cat_summary = {}
            for cat_name, stats in category_stats.items():
                cnt = stats["count"]
                cat_summary[cat_name] = {
                    "count": cnt,
                    "recall_at_1": round(stats["r1_count"] / cnt, 4) if cnt else 0.0,
                    "recall_at_3": round(stats["r3_count"] / cnt, 4) if cnt else 0.0,
                    "recall_at_5": round(stats["r5_count"] / cnt, 4) if cnt else 0.0,
                    "mrr": round(stats["rr_sum"] / cnt, 4) if cnt else 0.0,
                    "avg_latency_ms": round(statistics.mean(stats["latencies"]), 2) if stats["latencies"] else 0.0
                }

            sorted_latencies = sorted(mode_latencies)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0.0

            benchmark_results["modes"][mode] = {
                "recall_at_1": round(sum(recalls_at_1) / len(cases), 4),
                "recall_at_3": round(sum(recalls_at_3) / len(cases), 4),
                "recall_at_5": round(sum(recalls_at_5) / len(cases), 4),
                "mrr": round(sum(reciprocal_ranks) / len(cases), 4),
                "mean_latency_ms": round(statistics.mean(mode_latencies), 2),
                "p95_latency_ms": round(p95_latency, 2),
                "min_latency_ms": round(min(mode_latencies), 2),
                "max_latency_ms": round(max(mode_latencies), 2),
                "category_breakdown": cat_summary,
                "case_details": case_details
            }

            print(f"Results for {mode.upper()}:")
            print(f"  Recall@1: {benchmark_results['modes'][mode]['recall_at_1'] * 100:.1f}%")
            print(f"  Recall@3: {benchmark_results['modes'][mode]['recall_at_3'] * 100:.1f}%")
            print(f"  Recall@5: {benchmark_results['modes'][mode]['recall_at_5'] * 100:.1f}%")
            print(f"  MRR:      {benchmark_results['modes'][mode]['mrr']:.4f}")
            print(f"  Latency:  mean={benchmark_results['modes'][mode]['mean_latency_ms']:.2f}ms, p95={benchmark_results['modes'][mode]['p95_latency_ms']:.2f}ms")

        output_path = "results/retrieval_benchmark.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_results, f, indent=2)

        print(f"\nSaved empirical benchmark results to {output_path}")

    finally:
        db.close()

if __name__ == "__main__":
    run_retrieval_benchmark()
