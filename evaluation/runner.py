"""Evaluation Harness Runner

Loads the 40-case evaluation dataset and executes automated benchmarks
against the DocuMind pipeline, generating structured reports.
Supports real database-backed retrieval via DatabaseRetriever.
"""

import json
import os
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from evaluation.metrics import EvaluationCaseResult, EvaluationSummary
from backend.chunking.base import DocumentChunk
from backend.retrieval.db_retriever import DatabaseRetriever
from backend.retrieval.hybrid_retriever import LocalHybridRetriever
from backend.generation.ollama_generator import OllamaGenerator
from backend.citations.validator import CitationValidator

class EvaluationRunner:
    def __init__(
        self,
        dataset_path: str = "data/evaluation_dataset.json",
        db: Optional[Session] = None
    ):
        self.dataset_path = dataset_path
        self.db = db
        self.generator = OllamaGenerator()
        self.validator = CitationValidator()

    def load_dataset(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Evaluation dataset not found at {self.dataset_path}")
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("cases", [])

    def evaluate_case(self, case: Dict[str, Any], mode: str = "hybrid") -> EvaluationCaseResult:
        case_id = case["case_id"]
        category = case["category"]
        question = case["question"]
        expected_ans = case["expected_answer"]
        passage = case["relevant_source_passage"]
        expected_abstain = case.get("should_abstain", case.get("expected_abstention", False))
        page_num = 1

        if self.db is not None:
            retriever = DatabaseRetriever(db=self.db)
            search_results = retriever.retrieve(query=question, top_k=3, mode=mode)
            retrieved_chunks = [
                DocumentChunk(
                    chunk_id=r.chunk_id,
                    doc_id=r.document_id,
                    page_numbers=[r.page_number],
                    text=r.text
                )
                for r in search_results
            ]
        else:
            # Fallback to in-memory synthetic chunk if db is not provided
            loc = case.get("expected_source_location")
            if isinstance(loc, dict):
                page_num = loc.get("page", 1)
            chunk = DocumentChunk(
                chunk_id=f"chk_{case_id}",
                doc_id=case.get("document_id", case.get("doc_id", "doc_default")),
                page_numbers=[page_num],
                text=passage
            )
            local_retriever = LocalHybridRetriever()
            local_retriever.index([chunk])
            scored = local_retriever.retrieve(question, top_k=1)
            retrieved_chunks = [s.chunk for s in scored]

        t0 = time.perf_counter()
        resp = self.generator.generate(question, retrieved_chunks)
        latency = time.perf_counter() - t0

        validation = self.validator.validate(resp, retrieved_chunks)

        # Score correctness
        if expected_abstain:
            is_correct = resp.abstained
        else:
            is_correct = (not resp.abstained) and (
                any(w.lower() in resp.answer.lower() for w in expected_ans.split()[:4])
            )

        return EvaluationCaseResult(
            case_id=case_id,
            category=category,
            question=question,
            expected_answer=expected_ans,
            model_answer=resp.answer,
            expected_abstention=expected_abstain,
            actual_abstained=resp.abstained,
            correctness_score=1.0 if is_correct else 0.0,
            latency_seconds=round(latency, 2),
            grounding_score=validation.grounding_score
        )
