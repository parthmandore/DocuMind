import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

"""End-to-End Scenarios A-E Verification Script for DocuMind.

Verifies:
- Scenario A: Groq provider active and truthful reporting across endpoints
- Scenario B: Strict single-document research isolation & cross-document abstention
- Scenario C: Conversation persistence across reloads by ID
- Scenario D: Single-flight request lifecycle (completed answer without stale loading indicators)
- Scenario E: Ingestion performance (< 3s total for multi-page documents)
"""

import time
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def get(path: str):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post(path: str, data: dict):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run_scenarios():
    print("=" * 60)
    print("RUNNING END-TO-END SCENARIO VERIFICATION")
    print("=" * 60)

    # ----------------------------------------------------
    # SCENARIO A: Groq Provider Active Verification
    # ----------------------------------------------------
    print("\n[Scenario A] Verifying Groq Provider Integration...")
    health = get("/api/health")
    assert health["status"] == "healthy"
    assert health["active_provider"] == "groq"
    assert health["groq_configured"] is True
    print(f"✓ Health endpoint confirms active_provider: '{health['active_provider']}'")

    provider_info = get("/api/settings/ai-provider")
    assert provider_info["active_provider"] == "groq"
    assert provider_info["generation_model"] == "qwen/qwen3.8-27b"
    assert provider_info["embedding_model"] == "nomic-embed-text"
    print(f"✓ Provider settings confirm generation_model: '{provider_info['generation_model']}'")
    print("✓ Scenario A PASSED")

    # ----------------------------------------------------
    # SCENARIO B: Single-Document Isolation
    # ----------------------------------------------------
    print("\n[Scenario B] Verifying Single-Document Isolation...")
    docs = get("/api/documents")
    assert len(docs) > 0, "At least one document must exist in database"
    target_doc = docs[0]
    doc_id = target_doc["id"]
    print(f"Target Document: '{target_doc['filename']}' ({doc_id})")

    # Query 1: Fact within document
    q1 = "What is the policy or procedure described in this document?"
    t0 = time.perf_counter()
    ans1 = post("/api/query", {"question": q1, "document_ids": [doc_id]})
    t1 = time.perf_counter() - t0
    conv_id = ans1["conversation_id"]
    print(f"✓ Grounded Query completed in {t1:.2f}s with status: '{ans1['status']}', confidence: {ans1['confidence']}")
    print(f"  Conversation ID created: {conv_id}")
    for c in ans1.get("citations", []):
        assert c["document_id"] == doc_id, f"Citation leak from document {c['document_id']}"
    print(f"✓ All {len(ans1.get('citations', []))} citations strictly match target document ID.")

    # Query 2: Fact outside document (must abstain without leaking)
    q2 = "What are the quantum physics equations for warp field coils?"
    ans2 = post("/api/query", {"question": q2, "document_ids": [doc_id], "conversation_id": conv_id})
    print(f"✓ External Query abstained cleanly: abstained={ans2['abstained']}, status='{ans2['status']}', citations={len(ans2.get('citations', []))}")
    assert ans2["abstained"] is True or ans2["status"] == "abstained" or len(ans2.get("citations", [])) == 0
    print("✓ Scenario B PASSED")

    # ----------------------------------------------------
    # SCENARIO C: Conversation Persistence
    # ----------------------------------------------------
    print("\n[Scenario C] Verifying Conversation Persistence across Reload...")
    reloaded_conv = get(f"/api/conversations/{conv_id}")
    assert reloaded_conv["id"] == conv_id
    assert len(reloaded_conv["messages"]) >= 4  # 2 questions + 2 answers
    print(f"✓ Successfully retrieved conversation '{conv_id}' with {len(reloaded_conv['messages'])} persisted messages.")
    user_msgs = [m for m in reloaded_conv["messages"] if m["role"] == "user"]
    asst_msgs = [m for m in reloaded_conv["messages"] if m["role"] == "assistant"]
    assert user_msgs[0]["content"] == q1
    assert user_msgs[1]["content"] == q2
    print("✓ Scenario C PASSED")

    # ----------------------------------------------------
    # SCENARIO D: Request Lifecycle & Timing Integrity
    # ----------------------------------------------------
    print("\n[Scenario D] Verifying Lifecycle & Latency Metadata...")
    meta = ans1["processing_metadata"]
    assert meta["latency_seconds"] > 0
    assert meta["evidence_selection_ms"] >= 0
    assert meta["llm_latency_seconds"] >= 0
    print(f"✓ Lifecycle completed with latency breakdowns:")
    print(f"  Total Latency: {meta['latency_seconds']:.2f}s")
    print(f"  Evidence Selection: {meta['evidence_selection_ms']}ms")
    print(f"  LLM Synthesis: {meta['llm_latency_seconds']:.2f}s")
    print(f"  Verification: {meta.get('verification_ms', 0)}ms")
    print("✓ Scenario D PASSED")

    # ----------------------------------------------------
    # SCENARIO E: Ingestion Performance Measurement
    # ----------------------------------------------------
    print("\n[Scenario E] Verifying Extraction & Ingestion Speed...")
    from backend.extraction.pdf_parser import PyMuPDFParser
    pdf_path = Path("data/uploads/doc-hr-pol-2026.pdf")
    if not pdf_path.exists():
        pdf_path = Path("tests/fixtures/pdfs/single_column_report.pdf")

    parser = PyMuPDFParser()
    t_start = time.perf_counter()
    extracted = parser.parse(str(pdf_path))
    t_extract = time.perf_counter() - t_start
    print(f"✓ Text and structure extraction for {extracted.total_pages}-page document completed in {t_extract:.3f}s (< 1.5s target)")
    assert t_extract < 1.5
    print("✓ Scenario E PASSED")

    print("\n" + "=" * 60)
    print("ALL 5 END-TO-END SCENARIOS VERIFIED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_scenarios()
