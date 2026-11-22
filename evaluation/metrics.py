"""Evaluation Metrics for Document Intelligence RAG Pipelines"""

from typing import List
from pydantic import BaseModel

class EvaluationCaseResult(BaseModel):
    case_id: str
    category: str
    question: str
    expected_answer: str
    model_answer: str
    expected_abstention: bool
    actual_abstained: bool
    correctness_score: float  # 0.0 to 1.0
    latency_seconds: float
    grounding_score: float

class EvaluationSummary(BaseModel):
    total_cases: int
    passed_cases: int
    accuracy_percentage: float
    avg_latency_seconds: float
    avg_grounding_score: float
    category_breakdown: dict
