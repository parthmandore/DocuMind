# REST API Specification — DocuMind

**Project**: DocuMind — AI-Powered Document Intelligence & Research Platform  
**Base URL**: `http://127.0.0.1:8000/api`  
**API Specification**: OpenAPI 3.1.0  
**Interactive Documentation**:  
- Swagger UI: `http://127.0.0.1:8000/docs`  
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 1. System & Health

### `GET /api/health`
Returns system diagnostics, database connectivity, Ollama daemon status, active AI provider status, and hardware resource metrics.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "DocuMind",
  "database": "connected",
  "ollama_status": "connected",
  "free_disk_gb": 128.45,
  "active_provider": "groq",
  "generation_provider_status": "ready",
  "embedding_provider_status": "ready",
  "groq_configured": true,
  "arbiter_status": "idle",
  "ram_total_gb": 16.0,
  "ram_available_gb": 8.4,
  "ram_used_percent": 47.5,
  "cpu_count": 8
}
```

---

## 2. AI Provider Settings

### `GET /api/settings/ai-provider`
Returns current generation provider configuration and available alternatives without exposing API keys.

**Response `200 OK`**:
```json
{
  "active_provider": "groq",
  "available_providers": ["ollama", "groq"],
  "generation_model": "qwen/qwen3.8-27b",
  "embedding_provider": "ollama",
  "embedding_model": "nomic-embed-text",
  "embedding_dimension": 768,
  "embedding_available": true,
  "groq_configured": true,
  "provider_health": {
    "status": "ready",
    "model": "qwen/qwen3.8-27b",
    "available": true,
    "message": null
  },
  "warning": "Cloud inference active: Document excerpts for queries are processed via Groq API."
}
```

### `PUT /api/settings/ai-provider`
Switches active generation engine between `ollama` and `groq`. Validates credentials and endpoint reachability before persisting.

**Request Body**:
```json
{
  "provider": "ollama"
}
```

---

## 3. Document Lifecycle & Ingestion

### `POST /api/documents/upload`
Uploads a document for background text extraction, structural section parsing, layout chunking, and dense vector embedding.

- **Content-Type**: `multipart/form-data`
- **Fields**: `file` (Binary: `.pdf`, `.docx`, `.txt`, `.md`)

**Response `201 Created`**:
```json
{
  "document": {
    "id": "doc_8f1e2d4a",
    "title": "Quarterly_Report.pdf",
    "filename": "Quarterly_Report.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 1048576,
    "file_hash": "a1b2c3d4...",
    "status": "PENDING",
    "total_pages": 12,
    "total_chunks": 48
  },
  "job_id": "job_9b3e1f0a",
  "is_duplicate": false
}
```

### `GET /api/documents`
Lists all indexed documents with pagination and sorting.
- **Query Parameters**: `skip` (int, default `0`), `limit` (int, default `100`)

### `GET /api/documents/:id`
Returns detailed metadata for a single document.

### `GET /api/documents/:id/content`
Returns extracted layout chunks with bounding boxes, section levels, and page references for PDF coordinate citation mapping.

### `GET /api/documents/:id/file`
Streams the original document file with strict path-containment validation.

### `POST /api/documents/:id/reindex`
Forces re-extraction, re-chunking, and re-embedding of an existing document.

### `DELETE /api/documents/:id`
Deletes document record, associated chunks, vector embeddings, and physical upload file with transactional cascade.

---

## 4. Search & Retrieval

### `POST /api/search`
Executes lexical (BM25), dense vector, or hybrid retrieval over indexed document chunks.

**Request Body**:
```json
{
  "query": "What are the capital expenditure projections?",
  "document_ids": ["doc_8f1e2d4a"],
  "top_k": 5,
  "mode": "hybrid"
}
```

**Modes Supported**:
- `hybrid` (Reciprocal Rank Fusion of BM25 + dense vector embeddings)
- `dense` (768-dim `nomic-embed-text` cosine similarity)
- `lexical` (Okapi BM25 keyword matching)

---

## 5. Grounded Question Answering

### `POST /api/query`
Submits a natural-language research question against indexed document knowledge. Returns a grounded answer with claim-level verification and precise citation coordinates.

**Request Body**:
```json
{
  "question": "What is the policy on remote work equipment reimbursement?",
  "conversation_id": "conv_4a2c1b9e",
  "document_ids": ["doc_8f1e2d4a"],
  "retrieval_mode": "hybrid",
  "confidence_threshold": 0.5
}
```

**Response `200 OK`**:
```json
{
  "answer": "Employees are eligible for a one-time equipment reimbursement of up to $500 for home office setup [1].",
  "confidence_score": 0.94,
  "abstention": false,
  "abstention_reason": null,
  "claims": [
    {
      "claim_text": "Employees are eligible for a one-time equipment reimbursement of up to $500 for home office setup.",
      "status": "supported",
      "citations": [
        {
          "citation_id": 1,
          "document_id": "doc_8f1e2d4a",
          "document_title": "HR_Policy_2026.pdf",
          "page_number": 8,
          "exact_quote": "A one-time home office equipment stipend of up to $500 is provided upon onboarding.",
          "bboxes": [{"x0": 72.0, "y0": 180.0, "x1": 480.0, "y1": 204.0, "page": 8}],
          "is_verified": true,
          "grounding_score": 0.96
        }
      ]
    }
  ],
  "latency_ms": 1420.5,
  "provider": "groq",
  "model": "qwen/qwen3.8-27b"
}
```

---

## 6. Multi-Turn Conversations

- `GET /api/conversations`: Lists persistent conversational threads.
- `GET /api/conversations/:id`: Retrieves conversation message history and associated citations.
- `PATCH /api/conversations/:id`: Renames conversation title.
- `DELETE /api/conversations/:id`: Deletes conversation thread and cascades message citations.

---

## 7. Citation Analytics & Insights

### `GET /api/analytics/insights`
Aggregates real-time verification density, contradiction detection logs, claim status distributions, and corpus grounding metrics.

---

## 8. Support & Feedback Intake

### `POST /api/support/contact`
Receives user feedback, bug reports, and support queries with rate limiting (5 req / 10 min) and anti-spam protection.

**Request Body**:
```json
{
  "name": "Alex Mercer",
  "email": "alex.mercer@example.com",
  "category": "bug",
  "subject": "Citation bounding box offset in landscape PDF",
  "message": "When inspecting landscape orientation slides, coordinate bounding boxes appear offset by 90 degrees.",
  "website": null
}
```

**Response `200 OK`**:
```json
{
  "status": "received",
  "message": "Thank you for your feedback! Our engineering team has received your submission.",
  "reference_id": "DM-4A7F9B1E",
  "timestamp": "2026-11-14T11:15:00Z"
}
```
