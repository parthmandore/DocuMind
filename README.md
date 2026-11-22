# DocuMind

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

DocuMind is a local-first document intelligence and research workspace for document question answering with hybrid retrieval and automated citation verification.

The platform processes documents locally, generating 768-dimensional embeddings via Ollama and storing records in an SQLite database to ensure data privacy. For answer synthesis, DocuMind supports dual AI routing: offline inference via local Ollama models or high-throughput generation using cloud APIs (Groq).

---

## Key Features

- **Multi-Format Ingestion**: Ingests `.pdf`, `.docx`, `.txt`, and `.md` files with automated text and layout parsing.
- **Layout-Aware Extraction & Chunking**: Preserves reading order across columns, heading hierarchy (H1–H3), and replicates table headers across chunk fragments.
- **Hybrid Retrieval Engine**: Fuses Okapi BM25 keyword matching with dense cosine similarity using Reciprocal Rank Fusion (RRF, $k=60$).
- **Dual AI Provider Routing**: Supports offline generation via Ollama (`qwen3:4b`) or cloud inference via Groq (`qwen/qwen3.8-27b`) while keeping embeddings strictly local.
- **Claim-Level Citation Verification**: Validates generated assertions across 5 support states with numerical fact checking and contradiction detection.
- **Interactive PDF Viewer**: Embedded canvas viewer with page navigation, zoom, rotation, and bounding box coordinate overlays.
- **Persistent Threads & Analytics**: Preserves multi-turn research conversations and tracks grounding rates, claim support distributions, and cross-document conflicts.

---

## How It Works

```
Document Upload
      │
      ▼
Text & Layout Extraction (PyMuPDF / python-docx / markdown)
      │
      ▼
Structural Analysis (Headings H1-H3 & Table Detection)
      │
      ▼
Layout-Aware Chunking (Token-bounded chunks with preserved table headers)
      │
      ▼
Local Embeddings (Ollama nomic-embed-text, 768 dimensions)
      │
      ▼
Hybrid Retrieval (BM25 keyword search + Dense cosine similarity + RRF fusion)
      │
      ▼
Answer Generation (Groq Cloud API or Local Ollama)
      │
      ▼
Citation Verification (6-point provenance check & 5-state claim audit)
```

1. **Extraction**: Documents are parsed into structured blocks with spatial bounding coordinates $(x0, y0, x1, y1)$.
2. **Chunking**: Text is split into token-bounded chunks (250–400 tokens) preserving heading hierarchy and replicating table headers.
3. **Embedding**: Chunks are embedded with `nomic-embed-text` (768-dim) via local Ollama and stored in SQLite.
4. **Hybrid Retrieval**: Queries execute dense vector search and BM25 concurrently, merged via Reciprocal Rank Fusion ($k=60$, $w_{\text{dense}}=0.6$, $w_{\text{lex}}=0.4$).
5. **Synthesis & Verification**: Answers are synthesized under prompt defense boundaries, then audited sentence-by-sentence against source passages.

---

## Engineering Highlights & Improvements

- **768-Dimensional Local Embeddings**: Vector embeddings are computed on-device with `nomic-embed-text` via Ollama, ensuring raw text and vectors remain private.
- **RRF Hybrid Search with Graceful Fallback**: Combines dense vector similarity with Okapi BM25 ($k=60$). If Ollama is busy, the engine degrades gracefully to lexical BM25 without failing queries.
- **Table-Header Preservation**: Tables exceeding chunk limits split along row boundaries, replicating markdown headers across fragments to prevent headless context rows.
- **6-Point Provenance Verification**: Citations are verified for document existence, chunk existence, chunk-document ownership, exact/fuzzy quote match, page alignment, and bounding box validity.
- **5-State Claim Verification & Numerical Checks**: Classifies claims as `Supported`, `Partially Supported`, `Unsupported`, `Contradicted`, or `Insufficient Evidence`, while verifying numbers, percentages, and engineering units (%, MPa, RPM, kW).
- **Hardware Arbiter & Memory Guard**: Serializes Ollama operations via dual-lock mutual exclusion and halts inference if RAM utilization exceeds 92%, preventing swapping crashes on 16 GB machines.
- **Build & CI Verification**: Automated CI verifies backend application integrity and imports alongside strict TypeScript checking (`tsc -b`) and Vite production bundling.

---

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite (WAL mode), PyMuPDF (fitz), python-docx, rank-bm25, httpx, Pydantic v2
- **Frontend**: TypeScript, React 18, Vite 6, Tailwind CSS, TanStack Query v5, Lucide Icons, PDF.js
- **Local AI**: Ollama (`nomic-embed-text` for 768d embeddings; optional `qwen3:4b` for generation)
- **Cloud AI**: Groq Cloud API (`qwen/qwen3.8-27b` for fast synthesis)
- **Database & Retrieval**: SQLite (WAL), Okapi BM25, Cosine Similarity, Reciprocal Rank Fusion ($k=60$)
- **Document Processing**: PyMuPDF (layout extraction & coordinate bounding boxes), python-docx

---

## Getting Started

### Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+ (with `npm`)
- **Ollama**: Running locally with `nomic-embed-text` (`ollama pull nomic-embed-text`)
- **Groq API Key**: Optional, for cloud answer generation

### Installation

```bash
# 1. Clone repository
git clone https://github.com/parthmandore/DocuMind.git
cd DocuMind

# 2. Backend setup
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 3. Frontend setup
cd frontend && npm install && cd ..
```

### Running Locally

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend (http://127.0.0.1:8000)
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000

# Terminal 3: Start Frontend (http://localhost:3000)
cd frontend && npm run dev
```

---

## Configuration

Configure `.env` as needed:

- **Embeddings**: Local Ollama (`http://127.0.0.1:11434`) running `nomic-embed-text` is required.
- **Generation Provider**: Set `AI_PROVIDER=groq` (with `GROQ_API_KEY`) for cloud synthesis, or `AI_PROVIDER=ollama` for offline generation.
- **Security**: API keys reside solely in backend environment variables and are never sent to the client.

---

## Limitations

- **Scanned Documents**: The PDF parser processes text-layer PDFs; scanned image OCR is not bundled by default.
- **Host Concurrency**: Local generation and embedding share host resources; operations are serialized to prevent RAM exhaustion.
- **Single-Machine Storage**: Default storage is SQLite with WAL mode, intended for single-workstation use rather than distributed deployments.

---

## Project Structure

```
DocuMind/
├── backend/                  # FastAPI backend application
│   ├── ai/                   # AI provider integrations (Groq, Ollama)
│   ├── api/                  # REST endpoints, middleware, and schemas
│   ├── chunking/             # Layout-aware and table-header chunking
│   ├── citations/            # 6-point verification, numerical checks, contradictions
│   ├── db/                   # SQLAlchemy models, sessions, and SQLite database
│   ├── evidence/             # Evidence selection and sufficiency assessment
│   ├── extraction/           # Multi-format parsers (PDF, DOCX, TXT, MD)
│   ├── generation/           # Prompt construction and grounded synthesis
│   ├── ollama_runtime/       # Concurrency arbiter and Ollama client
│   └── retrieval/            # Hybrid retrieval (BM25 + Dense + RRF)
├── docs/                     # Architecture, API, and setup documentation
├── frontend/                 # React 18 TypeScript application (Vite 6)
│   ├── src/
│   │   ├── components/       # UI, PDF viewer, and layout components
│   │   ├── pages/            # Dashboard, Research, Documents, Insights, Settings
│   │   └── services/         # API client and query hooks
│   └── package.json          # Frontend dependencies and scripts
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```
