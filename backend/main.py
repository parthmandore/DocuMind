"""DocuMind Backend Entrypoint & CLI Test Harness"""

import sys
import uvicorn
from backend.config import config
from backend.db.base import init_db
from backend.extraction.router import extract_document
from backend.chunking.layout_chunker import LayoutAwareChunker
from backend.retrieval.hybrid_retriever import LocalHybridRetriever
from backend.generation.ollama_generator import OllamaGenerator
from backend.citations.validator import CitationValidator
from backend.api.app import app

def main():
    if "--serve" in sys.argv:
        print(f"Starting {config.app_name} API Server at http://127.0.0.1:8000 ...")
        uvicorn.run("backend.api.app:app", host="127.0.0.1", port=8000, reload=False)
        return

    print("=" * 60)
    print(f"      {config.app_name} Backend Engine (v0.2.0)")
    print("=" * 60)
    print(f"Ollama Endpoint: {config.ollama_host}")
    print(f"LLM Model:       {config.llm_model}")
    print(f"Embedding Model: {config.embedding_model}")
    print(f"Database URL:    {config.database_url}")
    print(f"Upload Path:     {config.upload_dir}")
    print("-" * 60)
    init_db()
    print("All backend modules and database schemas initialized successfully.")

if __name__ == "__main__":
    main()
