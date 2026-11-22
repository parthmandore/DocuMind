"""Tests for Phase 4 Security, Privacy, Headers, and Support Infrastructure"""

import pytest
from starlette.testclient import TestClient
from backend.api.app import app
from backend.config import config
from backend.api.routes.support import _RATE_LIMIT_MAX_REQUESTS, _ip_request_timestamps

@pytest.fixture
def client():
    return TestClient(app)

def test_security_headers_on_responses(client):
    """Verify production security headers are attached to API responses."""
    resp = client.get("/")
    assert resp.status_code == 200
    headers = resp.headers

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=(), payment=()"
    
    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "worker-src 'self' blob:" in csp

def test_hsts_disabled_on_local_http(client):
    """Ensure Strict-Transport-Security is NEVER sent on plain local HTTP requests."""
    resp = client.get("/")
    assert "strict-transport-security" not in resp.headers

def test_hsts_enabled_on_https_when_configured():
    """Ensure Strict-Transport-Security is attached when request is HTTPS and enabled in config."""
    orig_hsts = config.enable_hsts
    try:
        config.enable_hsts = True
        test_client = TestClient(app, base_url="https://documind.local")
        resp = test_client.get("/")
        assert "strict-transport-security" in resp.headers
        assert "max-age=31536000" in resp.headers["strict-transport-security"]
    finally:
        config.enable_hsts = orig_hsts

def test_contact_support_valid_submission(client):
    """POST /api/support/contact successfully receives and logs valid support submissions."""
    _ip_request_timestamps.clear()
    payload = {
        "name": "Security Researcher",
        "email": "researcher@example.com",
        "category": "bug",
        "subject": "Citation alignment edge case",
        "message": "When querying complex tables, coordinate boxes can occasionally overlap."
    }
    resp = client.post("/api/support/contact", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "received"
    assert "DM-" in data["reference_id"]
    assert "received your submission" in data["message"]

def test_contact_support_honeypot_triggers_silent_drop(client):
    """Anti-spam honeypot: automated bot filling 'website' is silently dropped with fake ref."""
    _ip_request_timestamps.clear()
    payload = {
        "name": "Spam Bot",
        "email": "bot@spammer.com",
        "category": "feedback",
        "subject": "Buy cheap pharmaceutical tokens",
        "message": "Check our external link now!",
        "website": "https://spammysite.example.com"
    }
    resp = client.post("/api/support/contact", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "received"
    # Returns success to deceive bot, but does not use standard DM- prefix
    assert not data["reference_id"].startswith("DM-")

def test_contact_support_validation_rejects_invalid_inputs(client):
    """Validation rejects missing fields, bad emails, or illegal control characters."""
    _ip_request_timestamps.clear()
    # 1. Invalid email
    bad_email_resp = client.post("/api/support/contact", json={
        "name": "Tester",
        "email": "not-an-email",
        "category": "bug",
        "subject": "Test subject",
        "message": "This is a valid test message with sufficient length."
    })
    assert bad_email_resp.status_code == 422

    # 2. CRLF injection in subject
    crlf_resp = client.post("/api/support/contact", json={
        "name": "Tester",
        "email": "test@example.com",
        "category": "bug",
        "subject": "Subject\r\nBcc: victim@example.com",
        "message": "This is a valid test message with sufficient length."
    })
    assert crlf_resp.status_code == 422

    # 3. Message too short
    short_msg_resp = client.post("/api/support/contact", json={
        "name": "Tester",
        "email": "test@example.com",
        "category": "bug",
        "subject": "Valid Subject",
        "message": "Short"
    })
    assert short_msg_resp.status_code == 422

def test_contact_support_rate_limiting(client):
    """Verify rate limiter blocks excessive submissions from the same IP."""
    _ip_request_timestamps.clear()
    payload = {
        "name": "Frequent Submitter",
        "email": "frequent@example.com",
        "category": "feedback",
        "subject": "Repeated submission test",
        "message": "Submitting multiple messages to test the rate limiting threshold."
    }

    # Submit up to max allowed
    for _ in range(_RATE_LIMIT_MAX_REQUESTS):
        resp = client.post("/api/support/contact", json=payload)
        assert resp.status_code == 200

    # Next submission must be rate limited
    limit_resp = client.post("/api/support/contact", json=payload)
    assert limit_resp.status_code == 429
    assert "Rate limit exceeded" in limit_resp.json()["detail"]
    assert "Retry-After" in limit_resp.headers

def test_secrets_masked_in_settings_and_health(client):
    """Ensure settings and health endpoints do not leak credentials or API keys."""
    # Settings check
    settings_resp = client.get("/api/settings/ai-provider")
    assert settings_resp.status_code == 200
    settings_data = settings_resp.json()
    assert "groq_api_key" not in settings_data
    assert "groq_configured" in settings_data

    # Health check
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert "groq_api_key" not in health_data
    assert "pg_dsn" not in health_data
