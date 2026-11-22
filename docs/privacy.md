# Data Handling, Privacy & Confidentiality Architecture

**DocuMind — Local-First AI Document Intelligence & Research Assistant**

DocuMind is engineered from first principles for privacy-sensitive enterprises, legal teams, and security-conscious researchers. This document defines the exact data movement boundaries, local persistence mechanics, external inference transmission policies, and zero-leakage guarantees.

---

## 1. Core Privacy Principles

1. **Local Storage by Default**: User document binaries, layout-aware text extracts, SQLite database records, and vector embeddings remain strictly on the host workstation running the DocuMind service.
2. **100% Cookie-Free Client**: The DocuMind web interface sets **zero (`0`)** tracking cookies, advertising beacons, or third-party tracking scripts.
3. **No Non-Essential Telemetry**: Product milestone telemetry is **disabled by default (opt-in only)** and is cryptographically and strictly stripped of any document text, queries, citations, filenames, or user identifiers.
4. **Transparent Cloud Inference**: Cloud AI generation is strictly optional. Users retain 100% control over whether evidence text ever leaves their host machine.

---

## 2. Data Flow Architecture

```
[User Document (.pdf, .docx, .txt, .md)]
                  │
                  ▼
[Local Extraction Engine (PyMuPDF / docx)]
                  │
                  ├──► [Saved to Local Filesystem: data/uploads/]
                  │
                  ▼
[Local Structural Layout Chunker]
                  │
                  ▼
[Local Vector Embeddings (Ollama: nomic-embed-text)]
                  │
                  ├──► [Stored in Local SQLite WAL: data/documind.db]
                  │
                  ▼
[User Query Input] ──► [Local Hybrid Retrieval (Okapi BM25 + Dense Vector RRF)]
                                    │
                                    ▼
                        [Relevant Evidence Chunks]
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
      [Provider 1: Local Ollama]             [Provider 2: Groq Cloud]
      - 100% Offline / Air-Gapped            - Optional Cloud Synthesis
      - Zero bytes leave localhost           - ONLY selected evidence snippets sent
      - Run entirely on local CPU/GPU        - Raw document binary NEVER transmitted
                                             - No model training on user API inputs
```

---

## 3. Inference Transmission Disclosure

When switching providers via the UI or `AI_PROVIDER=groq`:
- **What is transmitted**: Only the specific, top-ranked evidence passages required to answer the current query, along with the user's natural language question.
- **What is NEVER transmitted**:
  - Full original document files (`.pdf`, `.docx`, etc.).
  - Unrelated corpus chunks and vector indices.
  - User's database file or upload folder contents.
  - Internal reasoning traces or thinking tokens.
- **Air-Gap Mode**: When `AI_PROVIDER=ollama` is selected, all embeddings, retrieval, generation, and verification execute entirely against local loopback daemons (`127.0.0.1:11434`), enabling complete operation in air-gapped, isolated network environments.

---

## 4. Browser Storage Governance

Browser storage is governed by a strict key whitelist enforced in `frontend/src/utils/storage.ts`:

| Storage Key | Storage Mechanism | Data Stored | Privacy Impact |
|---|---|---|:---:|
| `documind_theme_mode` | `localStorage` | `'dark' \| 'light' \| 'system'` | Non-sensitive UI preference |
| `documind_sidebar_collapsed` | `localStorage` | `boolean` | Non-sensitive layout state |
| `documind_split_ratio` | `localStorage` | `number` (e.g., `0.5`) | Non-sensitive evidence layout |
| `documind_last_conv_id` | `localStorage` | Conversation UUID | Seamless session restoration |
| `documind_telemetry_enabled` | `localStorage` | `boolean` (default: `false`) | User consent state |
| `documind_active_research_session` | `sessionStorage` | Ephemeral active query state | Transient form preservation |

Attempts to store document contents, chunk texts, vector arrays, or sensitive answers in browser storage are strictly blocked by the storage controller.

---

## 5. Security & Threat Mitigation

- **Path Containment Enforcement**: All document preview requests served via `GET /api/documents/:id/file` enforce common-path containment checks against `data/uploads/`. Path traversal attempts (`../`) are aborted with HTTP 400.
- **MIME & Extension Whitelisting**: Uploads are restricted to verified extensions (`.pdf`, `.docx`, `.txt`, `.md`, `.markdown`) and standard document MIME types, capped at 50 MB (`config.max_upload_size_bytes`).
- **Secret Isolation**: Server-side API keys (`GROQ_API_KEY`) are loaded into memory and are never exposed via browser network payloads, client bundles, or settings API endpoints.
- **Rate-Limited Support Intake**: The support endpoint (`POST /api/support/contact`) applies in-memory IP rate limiting and hidden honeypot spam traps. Operational logs mask email addresses (`j***n@domain.com`).
