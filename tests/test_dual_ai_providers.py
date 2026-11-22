"""Dual AI Provider Integration & Safety Test Suite

Comprehensive tests for:
- Provider abstraction (Ollama & Groq resolution and switching)
- Groq generation, authentication, rate limits, timeouts, and error normalization
- Grounded citation verification, claim support, contradiction detection, and abstention
- Embedding dimensional integrity (768-dim nomic-embed-text) and ingestion safeguards
- Non-exposure of API secrets in responses, logs, and frontend contracts
"""

import pytest
from unittest.mock import MagicMock, patch
import httpx
from fastapi.testclient import TestClient

from backend.config import config, DocuMindConfig
from backend.ai.providers import (
    get_provider,
    set_active_provider,
    get_available_providers,
    get_ollama_provider,
    get_groq_provider,
    AIProviderAuthError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIProviderError
)
from backend.ai.providers.groq_provider import GroqProvider
from backend.ai.providers.ollama_provider import OllamaProvider
from backend.api.app import app
from backend.db.models import Document, DocumentChunk, ProcessingJob, DocumentStatus, JobStatus
from backend.generation.grounded_generator import GroundedAnswerGenerator
from backend.evidence.selector import EvidencePacket, SelectedEvidence
from backend.jobs.worker import process_job_sync

client = TestClient(app)

# ==========================================
# 1. PROVIDER ABSTRACTION TESTS
# ==========================================

def test_available_providers():
    providers = get_available_providers()
    assert "ollama" in providers
    assert "groq" in providers

def test_get_provider_resolution():
    ollama_p = get_provider("ollama")
    assert isinstance(ollama_p, OllamaProvider)
    assert ollama_p.name == "ollama"

    groq_p = get_provider("groq")
    assert isinstance(groq_p, GroqProvider)
    assert groq_p.name == "groq"

def test_invalid_provider_raises():
    with pytest.raises(ValueError) as exc:
        get_provider("unsupported_ai")
    assert "Unsupported AI provider" in str(exc.value)

def test_provider_switching():
    original = config.ai_provider
    try:
        p1 = set_active_provider("ollama")
        assert p1.name == "ollama"
        assert config.ai_provider == "ollama"

        p2 = set_active_provider("groq")
        assert p2.name == "groq"
        assert config.ai_provider == "groq"

        with pytest.raises(ValueError):
            set_active_provider("fake_provider")
    finally:
        set_active_provider(original)

def test_groq_missing_key_behavior(monkeypatch):
    groq_p = GroqProvider()
    monkeypatch.setattr(config, "groq_api_key", None)
    
    # generate should raise AIProviderAuthError
    with pytest.raises(AIProviderAuthError) as exc:
        groq_p.generate(prompt="Hello")
    assert "GROQ_API_KEY is not configured" in str(exc.value) or "not configured" in str(exc.value)

    # health check should report unconfigured
    health = groq_p.health_check(force=True)
    assert health["status"] == "unconfigured"
    assert health["available"] is False

# ==========================================
# 2. GROQ ERROR NORMALIZATION TESTS
# ==========================================

def test_groq_auth_failure_normalization(monkeypatch):
    groq_p = GroqProvider()
    monkeypatch.setattr(config, "groq_api_key", "test_key_xyz")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    
    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(AIProviderAuthError) as exc:
            groq_p.generate(prompt="test prompt")
        assert "authentication failed" in str(exc.value).lower()
        # Verify key is never leaked
        assert "test_key_xyz" not in str(exc.value)

def test_groq_rate_limit_normalization(monkeypatch):
    groq_p = GroqProvider()
    monkeypatch.setattr(config, "groq_api_key", "test_key_xyz")

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(AIProviderRateLimitError) as exc:
            groq_p.generate(prompt="test prompt")
        assert "rate limit" in str(exc.value).lower()
        assert "test_key_xyz" not in str(exc.value)

def test_groq_timeout_normalization(monkeypatch):
    groq_p = GroqProvider()
    monkeypatch.setattr(config, "groq_api_key", "test_key_xyz")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(AIProviderTimeoutError) as exc:
            groq_p.generate(prompt="test prompt")
        assert "timed out" in str(exc.value).lower()
        assert "test_key_xyz" not in str(exc.value)

def test_groq_network_error_normalization(monkeypatch):
    groq_p = GroqProvider()
    monkeypatch.setattr(config, "groq_api_key", "test_key_xyz")

    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("refused", request=req)):
        with pytest.raises(AIProviderError) as exc:
            groq_p.generate(prompt="test prompt")
        assert "network error" in str(exc.value).lower()
        assert "test_key_xyz" not in str(exc.value)

def test_groq_successful_generation_mocked(monkeypatch):
    groq_p = GroqProvider()
    monkeypatch.setattr(config, "groq_api_key", "test_key_xyz")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "The system operating pressure is 4.5 MPa [P1].",
                "reasoning": "Reasoning about pressure."
            }
        }],
        "usage": {
            "completion_tokens": 28
        }
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = groq_p.generate(prompt="What is pressure?", system="You are DocuMind.")
        assert res["response"] == "The system operating pressure is 4.5 MPa [P1]."
        assert res["thinking"] == "Reasoning about pressure."
        assert res["eval_count"] == 28
        assert res["provider"] == "groq"

# ==========================================
# 3. SETTINGS & HEALTH API TESTS
# ==========================================

def test_get_settings_ai_provider():
    resp = client.get("/api/settings/ai-provider")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_provider" in data
    assert "available_providers" in data
    assert "embedding_provider" in data
    assert data["embedding_provider"] == "ollama"
    assert data["embedding_dimension"] == 768

    # CRITICAL SECURITY CHECK: Ensure API key is never in the response
    raw_text = resp.text.lower()
    assert "groq_api_key" not in raw_text
    assert "gsk_" not in raw_text

def test_put_settings_switch_provider():
    original = config.ai_provider
    try:
        # Switch to ollama
        resp = client.put("/api/settings/ai-provider", json={"provider": "ollama"})
        assert resp.status_code == 200
        assert resp.json()["active_provider"] == "ollama"

        # Switch to invalid
        resp_bad = client.put("/api/settings/ai-provider", json={"provider": "anthropic"})
        assert resp_bad.status_code == 400

        # Switch to groq (when configured)
        if config.is_groq_configured:
            resp_groq = client.put("/api/settings/ai-provider", json={"provider": "groq"})
            assert resp_groq.status_code == 200
            assert resp_groq.json()["active_provider"] == "groq"
    finally:
        set_active_provider(original)

def test_health_endpoint_dual_provider():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "database" in data
    assert "ollama_status" in data
    assert "active_provider" in data
    assert "generation_provider_status" in data
    assert "embedding_provider_status" in data
    assert "groq_configured" in data
    
    # Security: No secret exposure
    raw_text = resp.text.lower()
    assert "gsk_" not in raw_text

# ==========================================
# 4. GROUNDED GENERATION WITH DUAL PROVIDERS
# ==========================================

def test_grounded_answer_with_groq_provider(db_session, monkeypatch):
    """Verify that GroundedAnswerGenerator works through Groq and verifies citations."""
    doc = Document(
        id="doc_dual_test",
        title="Dual Provider Test Document",
        filename="dual.pdf",
        storage_path="/tmp/dual.pdf",
        mime_type="application/pdf",
        file_size_bytes=400,
        file_hash="hash_dual_test",
        status="INDEXED"
    )
    db_session.add(doc)
    c1 = DocumentChunk(
        id="c_dual_1",
        document_id="doc_dual_test",
        chunk_index=0,
        page_number=1,
        text="The turbine inlet temperature is 1150 degrees Celsius [P1].",
        token_count=12
    )
    db_session.add(c1)
    db_session.commit()

    generator = GroundedAnswerGenerator(db=db_session)
    packet = EvidencePacket(
        query="What is the turbine inlet temperature?",
        selected_items=[
            SelectedEvidence(
                chunk_id="c_dual_1",
                document_id="doc_dual_test",
                document_filename="dual.pdf",
                page_number=1,
                text="The turbine inlet temperature is 1150 degrees Celsius.",
                dense_score=0.92
            )
        ]
    )
    monkeypatch.setattr(generator.evidence_selector, "select", lambda **kwargs: packet)

    # Mock Groq provider response
    mock_groq_resp = {
        "response": "The turbine inlet temperature is 1150 degrees Celsius [P1].",
        "thinking": "Grounded in passage P1.",
        "eval_count": 20,
        "model": "qwen/qwen3.8-27b",
        "provider": "groq"
    }

    groq_p = get_groq_provider()
    monkeypatch.setattr(groq_p, "generate", lambda **kwargs: mock_groq_resp)

    original_provider = config.ai_provider
    try:
        set_active_provider("groq")
        answer = generator.answer_question("What is the turbine inlet temperature?")

        assert answer.status == "answered"
        assert answer.abstained is False
        assert len(answer.citations) >= 1
        assert "1150" in answer.answer
        assert answer.processing_metadata["provider"] == "groq"
        assert answer.processing_metadata["numerical_facts_verified"] is True
    finally:
        set_active_provider(original_provider)

def test_grounded_answer_abstains_when_unsupported(db_session, monkeypatch):
    """Verify abstention behavior still strictly triggers regardless of AI provider."""
    generator = GroundedAnswerGenerator(db=db_session)
    empty_packet = EvidencePacket(
        query="What is the CEO personal phone number?",
        selected_items=[]
    )
    monkeypatch.setattr(generator.evidence_selector, "select", lambda **kwargs: empty_packet)

    original = config.ai_provider
    try:
        set_active_provider("groq")
        answer = generator.answer_question("What is the CEO personal phone number?")
        assert answer.abstained is True
        assert "do not contain information" in answer.answer.lower()
    finally:
        set_active_provider(original)

# ==========================================
# 5. EMBEDDING INTEGRITY & SAFEGUARDS
# ==========================================

def test_768_dimension_validation():
    """Verify vectors are strictly enforced to 768 dimensions."""
    chunk = DocumentChunk(
        id="c_dim_test",
        document_id="doc_dim",
        chunk_index=0,
        page_number=1,
        text="Sample text",
        token_count=2
    )

    valid_vector = [0.01] * 768
    chunk.set_embedding(valid_vector, model_name=config.embedding_model, expected_dim=768)
    assert chunk.embedding_dim == 768
    assert len(chunk.embedding) == 768

    invalid_dim_1536 = [0.01] * 1536
    with pytest.raises(ValueError) as exc:
        chunk.set_embedding(invalid_dim_1536, model_name=config.embedding_model, expected_dim=768)
    assert "Incompatible embedding vector dimension" in str(exc.value)

def test_ingestion_waiting_when_embedding_provider_down(db_session, monkeypatch):
    """Verify that when local Ollama embedding is unreachable, documents are NOT falsely marked completed."""
    doc = Document(
        id="doc_embed_wait_test",
        title="Embed Wait Doc",
        filename="embed_wait.txt",
        storage_path="/tmp/embed_wait.txt",
        mime_type="text/plain",
        file_size_bytes=100,
        file_hash="hash_wait_123",
        status=DocumentStatus.CHUNKED.value
    )
    chunk = DocumentChunk(
        id="c_wait_1",
        document_id="doc_embed_wait_test",
        chunk_index=0,
        page_number=1,
        text="A chunk needing dense embedding.",
        token_count=6,
        embedding=None,
        embedding_model=None
    )
    job = ProcessingJob(
        id="job_wait_test",
        document_id="doc_embed_wait_test",
        job_type="INGEST",
        status=JobStatus.PENDING.value
    )
    db_session.add_all([doc, chunk, job])
    db_session.commit()

    # Simulate Ollama embedding daemon being unreachable
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Ollama offline")):
        success = process_job_sync(
            doc_id=doc.id,
            job_id=job.id,
            db=db_session,
            skip_embedding=False
        )

        assert success is False
        db_session.refresh(doc)
        db_session.refresh(job)

        # Document must NOT be marked COMPLETED or INDEXED
        assert doc.status != DocumentStatus.COMPLETED.value
        assert "waiting for local embedding provider" in doc.error_message.lower()
        assert job.status == JobStatus.FAILED.value
        assert chunk.embedding is None

# ==========================================
# 6. SECURITY & SECRET EXCLUSION AUDIT
# ==========================================

def test_gitignore_contains_env():
    """Verify that .env files and settings overrides are strictly excluded from version control."""
    gitignore_path = config.project_root / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
    assert "data/ai_settings.json" in content

def test_env_example_has_no_real_secrets():
    """Verify .env.example contains only template placeholders."""
    env_ex = config.project_root / ".env.example"
    assert env_ex.exists()
    content = env_ex.read_text(encoding="utf-8")
    assert "gsk_" not in content
    assert "your_groq_api_key_here" in content
