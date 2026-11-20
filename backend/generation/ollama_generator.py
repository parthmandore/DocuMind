"""Local Ollama LLM Generator Implementation

Interfaces with local Ollama service through the centralized OllamaHardwareArbiter,
handling dual-stream reasoning tokens (thinking vs final response), strict context grounding,
and abstention protocols.
"""

import time
from typing import List, Optional
from backend.generation.base import Generator, GenerationResponse, CitationRef
from backend.retrieval.base import ScoredChunk
from backend.config import config
from backend.ollama_runtime.client import ollama_client

DEFAULT_SYSTEM_PROMPT = """You are DocuMind, an enterprise document intelligence assistant.
Your answers MUST be strictly grounded in the provided document context passages.
Rules:
1. Rely ONLY on the clear facts directly mentioned in the context.
2. If the context does not contain sufficient information to answer the question, state: "The provided documents do not contain information to answer this question." Do not extrapolate or guess.
3. If documents contradict each other or contain superseding clauses, explicitly state the contradiction or the most recent prevailing rule.
4. Keep the answer direct, concise, and factual.
"""

class OllamaGenerator(Generator):
    def __init__(
        self,
        host: str = None,
        model: str = None,
        temperature: float = None,
        num_predict: int = None,
        timeout: float = None
    ):
        self.host = (host or config.ollama_host).rstrip("/")
        self.model = model or config.llm_model
        self.temperature = temperature if temperature is not None else config.llm_temperature
        self.num_predict = num_predict if num_predict is not None else config.llm_num_predict
        self.timeout = timeout if timeout is not None else config.llm_timeout_seconds

    def _build_context_prompt(self, query: str, context_chunks: List[ScoredChunk]) -> str:
        prompt_parts = ["CONTEXT PASSAGES:\n"]
        for idx, sc in enumerate(context_chunks):
            c = sc.chunk
            pages = ",".join(str(p) for p in c.page_numbers)
            prompt_parts.append(
                f"--- Passage {idx + 1} (Doc: {c.doc_id}, Page: {pages}, Chunk: {c.chunk_id}) ---\n"
                f"{c.text}\n"
            )
        prompt_parts.append(f"\nUSER QUESTION:\n{query}\n\nANSWER:")
        return "\n".join(prompt_parts)

    def generate(
        self,
        query: str,
        context_chunks: List[ScoredChunk],
        system_instruction: Optional[str] = None
    ) -> GenerationResponse:
        system = system_instruction or DEFAULT_SYSTEM_PROMPT
        user_prompt = self._build_context_prompt(query, context_chunks)

        t0 = time.perf_counter()
        options = {
            "temperature": self.temperature,
            "num_predict": self.num_predict
        }

        gen_result = ollama_client.generate(
            prompt=user_prompt,
            system=system,
            model=self.model,
            options=options,
            timeout=self.timeout
        )

        latency = time.perf_counter() - t0
        full_answer = gen_result.get("response", "").strip()
        full_thinking = gen_result.get("thinking", "").strip()
        eval_count = gen_result.get("eval_count", 0)

        # Detect abstention
        abstention_phrases = [
            "do not contain information",
            "not mentioned in the provided",
            "insufficient information",
            "cannot answer",
            "not found in the context"
        ]
        is_abstained = any(p in full_answer.lower() for p in abstention_phrases)

        # Build basic citations from provided chunks
        citations = []
        if not is_abstained:
            for sc in context_chunks:
                primary_page = sc.chunk.page_numbers[0] if sc.chunk.page_numbers else 1
                citations.append(CitationRef(
                    chunk_id=sc.chunk.chunk_id,
                    doc_id=sc.chunk.doc_id,
                    page=primary_page,
                    quote=sc.chunk.text[:120] + "..." if len(sc.chunk.text) > 120 else sc.chunk.text
                ))

        return GenerationResponse(
            answer=full_answer,
            thinking=full_thinking if full_thinking else None,
            citations=citations,
            abstained=is_abstained,
            tokens_used=eval_count,
            latency_seconds=round(latency, 3),
            model=self.model
        )
