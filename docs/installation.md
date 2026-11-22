# Installation & Setup Guide — DocuMind

DocuMind is an enterprise-grade document intelligence and research assistant. It supports hybrid local (Ollama) and cloud (Groq) language model execution with local embeddings (`nomic-embed-text`).

---

## 1. System Requirements

### Hardware Requirements
- **CPU**: Modern x86_64 or ARM64 multicore processor (4+ cores recommended).
- **RAM**: Minimum 8 GB (16 GB recommended for running local LLMs alongside embedding models).
- **Storage**: At least 10 GB free space for vector embeddings, SQLite database, and local models.

### Software Prerequisites
- **Python**: Version 3.11, 3.12, 3.13, or 3.14.
- **Node.js**: Version 18.0.0 or higher (v20+ LTS recommended).
- **Git**: For cloning the repository.
- **Ollama**: For local embeddings and optional local LLM inference ([Download Ollama](https://ollama.com/download)).

---

## 2. Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/parthmandore/DocuMind.git
cd DocuMind
```

### Step 2: Python Environment Setup

#### Windows (PowerShell):
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Linux / macOS:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 3: Frontend Environment Setup

```bash
cd frontend
npm install
cd ..
```

---

### Step 4: Ollama Model Setup

DocuMind uses `nomic-embed-text` for local vector embeddings. Ensure Ollama is running and download the embedding model:

```bash
# Verify Ollama service is active
ollama serve

# Pull embedding model (required for vector search)
ollama pull nomic-embed-text

# Optional: pull local generation model (if using Ollama for LLM generation)
ollama pull llama3.2:3b
```

---

### Step 5: Environment Configuration

Copy the example environment file:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Open `.env` in your text editor and configure your preferred AI generation provider:
- To use **Groq** (recommended for low-latency fast generation):
  ```env
  GROQ_API_KEY=gsk_your_actual_groq_api_key_here
  ACTIVE_LLM_PROVIDER=groq
  GROQ_MODEL=llama-3.3-70b-versatile
  ```
- To use **Ollama** (100% offline, zero cloud calls):
  ```env
  ACTIVE_LLM_PROVIDER=ollama
  OLLAMA_MODEL=llama3.2:3b
  ```

For full configuration options, see [docs/configuration.md](file:///c:/Users/mando/document-intelligence/docs/configuration.md).

---

## 3. Running DocuMind

DocuMind runs as a FastAPI backend alongside a Vite React frontend.

### Option A: Running Manually (Two Terminals)

**Terminal 1 (Backend):**
```bash
# Windows
.\.venv\Scripts\Activate.ps1
python -m backend.main --serve

# Linux / macOS
source .venv/bin/activate
python -m backend.main --serve
```
The backend API server will start on `http://127.0.0.1:8000`.

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```
The frontend web interface will open on `http://localhost:3000`.

---

## 4. Verifying the Installation

1. **Backend Health Check**:
   Open `http://127.0.0.1:8000/api/health` in your browser. You should receive:
   ```json
   {
     "status": "healthy",
     "active_llm_provider": "groq",
     "embedding_provider": "ollama"
   }
   ```
2. **Frontend UI**:
   Navigate to `http://localhost:3000` to access the Document Intelligence Dashboard.
3. **Run Unit Tests**:
   ```bash
   pytest tests/test_chunking_and_structure.py tests/test_retrieval.py -v
   cd frontend && npm test
   ```
