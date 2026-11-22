# Contributing to DocuMind

Thank you for your interest in contributing to DocuMind! We welcome contributions that preserve our core principles: factual accuracy, evidence grounding, strict document isolation, and reproducible performance.

---

## 1. Development Principles

1. **Evidence Grounding First:** Answers must be directly verifiable against source documents. We never accept unverified or hallucinated claims to boost artificial benchmark scores.
2. **Document Isolation:** Retrieval and generation must strictly respect user document filters. Cross-document contamination is treated as a security defect.
3. **Reproducibility:** All retrieval, verification, and chunking behavior must be deterministic and fully covered by automated tests.
4. **Zero Secret Leaks:** Never commit `.env`, credentials, or private document datasets.

---

## 2. Local Setup Guide

### Prerequisites
- Python 3.11+ (Tested on Python 3.14)
- Node.js 18+ (Tested on Node 22) & npm
- Ollama (for local 768-dim `nomic-embed-text` embeddings)

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/parthmandore/DocuMind.git
cd DocuMind

# Create virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start backend dev server
python -m backend.main --serve
```

### Frontend Setup
```bash
cd frontend
npm ci
npm run dev
```

---

## 3. Testing Requirements

Before submitting a Pull Request, all automated test suites must pass:

### Backend Tests
```bash
python -m pytest tests/test_chunking_and_structure.py tests/test_query_processing.py tests/test_retrieval.py -v
```

### Frontend Tests & Build
```bash
cd frontend
npm test
npm run build
```

---

## 4. Pull Request Guidelines

1. **Fork & Branch:** Create a feature branch with a descriptive name (e.g., `feat/pdf-table-extraction` or `fix/bm25-acronym-expansion`).
2. **Follow Coding Standards:**
   - Python: Clean type hints (`typing.Optional`, `typing.List`, `Pydantic` models).
   - TypeScript: Strict typing (no unnecessary `any`, functional React components).
3. **Commit Messages:** Follow conventional commit formatting (e.g., `feat:`, `fix:`, `perf:`, `docs:`).
4. **Documentation:** Update relevant documents in `docs/` if modifying APIs or retrieval behavior.
5. **No Breaking Schema Changes:** Any database schema modification must include a valid Alembic migration script under `alembic/versions/`.
