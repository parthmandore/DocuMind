# Configuration Guide — DocuMind

**Project**: DocuMind — AI-Powered Document Intelligence & Research Platform  
DocuMind uses environment variables (loaded from `.env` in the repository root) and Pydantic configuration models in `backend/config.py` to manage dual AI provider routing, hardware execution thresholds, retrieval hyperparameters, and security policies.

---

## 1. Environment Variables Overview

Copy `.env.example` to `.env` to customize settings:

```bash
cp .env.example .env
```

| Variable | Type | Default | Description |
|---|:---:|:---:|---|
| `AI_PROVIDER` | String | `groq` | Active generation provider: `groq` (cloud synthesis) or `ollama` (100% local). |
| `GROQ_API_KEY` | String | *None* | Required if `AI_PROVIDER=groq`. API key for Groq Cloud. |
| `GROQ_BASE_URL` | URL | `https://api.groq.com/openai/v1` | OpenAI-compatible Groq API endpoint. |
| `GROQ_MODEL` | String | `qwen/qwen3.8-27b` | LLM model deployed on Groq. |
| `GROQ_TIMEOUT_SECONDS` | Float | `120.0` | HTTP request timeout for Groq inference. |
| `OLLAMA_HOST` | URL | `http://127.0.0.1:11434` | Local Ollama daemon host address. |
| `OLLAMA_GENERATION_MODEL` | String | `qwen3:4b` | Model used for local LLM generation. |
| `OLLAMA_EMBEDDING_MODEL` | String | `nomic-embed-text` | 768-dimensional local embedding model. |
| `EMBEDDING_BATCH_SIZE` | Integer | `8` | Chunk embedding batch size for Ollama inference. |
| `LLM_NUM_PREDICT` | Integer | `2400` | Maximum token generation limit. |
| `CORS_ALLOWED_ORIGINS` | Comma-list | `http://localhost:3000,...` | Allowed CORS origins for browser API access. |
| `ENABLE_HSTS` | Boolean | `false` | Enables `Strict-Transport-Security` header over HTTPS. |
| `DOCUMIND_PG_DSN` | String | `postgresql+psycopg://...` | Connection URI when using PostgreSQL instead of SQLite. |
| `SMTP_HOST` | String | *None* | Optional SMTP relay host for support feedback notifications. |
| `SMTP_PORT` | Integer | `587` | SMTP port (e.g., 587 for STARTTLS). |
| `SMTP_USER` | String | *None* | Optional SMTP authentication username. |
| `SMTP_PASSWORD` | String | *None* | Optional SMTP authentication password. |
| `SMTP_SENDER` | Email | `noreply@documind.local` | Sender address for dispatched support messages. |
| `SUPPORT_EMAIL_RECIPIENT` | Email | `support@documind.local` | Destination address for user support inquiries. |

---

## 2. AI Provider Routing Modes

DocuMind features a dual-provider architecture allowing you to balance cloud generation speed against 100% offline air-gapped data sovereignty.

### Mode 1: Cloud-Accelerated Generation (Default)
In this mode, document embeddings are computed locally using Ollama (`nomic-embed-text`), but answers are generated via Groq's high-speed inference engine.
```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Mode 2: 100% Air-Gapped / Offline Local Mode
In this mode, zero external network requests are made. Both embeddings and answer generation run via Ollama on localhost.
```env
AI_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_GENERATION_MODEL=qwen3:4b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

---

## 3. Database Persistence

DocuMind uses SQLite with Write-Ahead Logging (WAL) enabled by default for multi-reader concurrency and crash resilience:

- **Default Location**: `data/documind.db`
- **WAL Mode**: Initialized automatically on connection (`PRAGMA journal_mode=WAL;`).
- **PostgreSQL Support**: PostgreSQL with `pgvector` can be configured for enterprise deployments:
  ```env
  DOCUMIND_PG_DSN=postgresql+psycopg://documind:documind@localhost:5432/documind
  ```

---

## 4. Ingestion & Retrieval Hyperparameters

Parameters in `backend/config.py` are calibrated for technical, financial, and legal documentation:

- **Chunk Size**: 400 tokens with 50-token contextual overlap.
- **Table Preservation**: Multi-column markdown tables replicate headers across fragment splits.
- **Dense Vector Search**: Top-k cosine similarity over 768-dimensional embeddings.
- **Sparse BM25 Search**: Top-k keyword matches using Okapi BM25.
- **Hybrid Fusion**: Reciprocal Rank Fusion (RRF) with constant \(k=60\).
- **Document Boundary Scoping**: Queries execute with explicit `document_id` SQL filters to prevent cross-document contamination.
