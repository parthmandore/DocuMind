import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys
import shutil
import json
import httpx
import psutil

def check_python():
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    # Target is Python 3.14 (or >= 3.11)
    passed = (version_info.major == 3 and version_info.minor >= 11)
    return {
        "item": "Python Version",
        "status": "PASS" if passed else "FAIL",
        "details": f"Python {version_str} ({sys.executable})"
    }

def check_backend_dependencies():
    required_packages = ["httpx", "ollama", "pydantic", "psutil"]
    missing = []
    found = {}
    for pkg in required_packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            found[pkg] = ver
        except ImportError:
            missing.append(pkg)
    
    if missing:
        return {
            "item": "Core Backend Dependencies",
            "status": "FAIL",
            "details": f"Missing: {', '.join(missing)}; Installed: {found}"
        }
    return {
        "item": "Core Backend Dependencies",
        "status": "PASS",
        "details": f"All installed: {found}"
    }

def check_ollama_executable():
    path = shutil.which("ollama")
    if not path:
        # Check standard user local directory
        import os
        local_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        if os.path.exists(local_path):
            path = local_path
    
    if path:
        return {
            "item": "Ollama Executable",
            "status": "PASS",
            "details": f"Found at {path}"
        }
    return {
        "item": "Ollama Executable",
        "status": "FAIL",
        "details": "ollama.exe not found on PATH or LocalAppData"
    }

def check_ollama_service():
    try:
        resp = httpx.get("http://127.0.0.1:11434/", timeout=3.0)
        if resp.status_code == 200 and "Ollama is running" in resp.text:
            return {
                "item": "Ollama Local Service",
                "status": "PASS",
                "details": "Responding at http://127.0.0.1:11434/ ('Ollama is running')"
            }
        return {
            "item": "Ollama Local Service",
            "status": "FAIL",
            "details": f"Unexpected response: HTTP {resp.status_code} - {resp.text[:50]}"
        }
    except Exception as e:
        return {
            "item": "Ollama Local Service",
            "status": "FAIL",
            "details": f"Could not reach http://127.0.0.1:11434/: {e}"
        }

def check_language_model():
    target_model = "qwen3:4b"
    try:
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m.get("name") for m in models]
            matched = [m for m in model_names if target_model in m or "qwen3" in m]
            if matched:
                return {
                    "item": f"Language Model ({target_model})",
                    "status": "PASS",
                    "details": f"Available: {matched[0]}"
                }
            return {
                "item": f"Language Model ({target_model})",
                "status": "FAIL",
                "details": f"Model '{target_model}' not found in local models: {model_names}"
            }
    except Exception as e:
        return {
            "item": f"Language Model ({target_model})",
            "status": "FAIL",
            "details": f"Error querying local tags: {e}"
        }

def check_local_generation():
    target_model = "qwen3:4b"
    try:
        resp = httpx.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": target_model, "prompt": "Say hello in one word.", "stream": False},
            timeout=30.0
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            if text:
                return {
                    "item": "Local Generation Test",
                    "status": "PASS",
                    "details": f"Generated non-empty output: '{text}'"
                }
            return {
                "item": "Local Generation Test",
                "status": "FAIL",
                "details": "Model returned an empty response string."
            }
        return {
            "item": "Local Generation Test",
            "status": "FAIL",
            "details": f"HTTP {resp.status_code}: {resp.text[:100]}"
        }
    except Exception as e:
        return {
            "item": "Local Generation Test",
            "status": "FAIL",
            "details": f"Generation request failed: {e}"
        }

def check_embedding_model():
    target_model = "embeddinggemma"
    try:
        resp = httpx.post(
            "http://127.0.0.1:11434/api/embed",
            json={"model": target_model, "input": "DocuMind document intelligence"},
            timeout=30.0
        )
        if resp.status_code == 200:
            embeddings = resp.json().get("embeddings", [])
            if embeddings and len(embeddings[0]) > 0:
                dim = len(embeddings[0])
                return {
                    "item": f"Embedding Model ({target_model})",
                    "status": "PASS",
                    "details": f"Successfully produced embedding vector (dimension={dim})"
                }
            return {
                "item": f"Embedding Model ({target_model})",
                "status": "FAIL",
                "details": "Returned empty embedding vector"
            }
        return {
            "item": f"Embedding Model ({target_model})",
            "status": "FAIL",
            "details": f"HTTP {resp.status_code}: {resp.text[:100]}"
        }
    except Exception as e:
        return {
            "item": f"Embedding Model ({target_model})",
            "status": "FAIL",
            "details": f"Embedding request failed: {e}"
        }

def check_database_connectivity():
    # PostgreSQL audit: Explicitly checking local PostgreSQL
    # PostgreSQL is preferred for pgvector but optional for initial model tests.
    try:
        import psycopg
        # Try connecting to local default postgres port 5432 with short timeout
        conn = psycopg.connect("host=127.0.0.1 port=5432 user=postgres connect_timeout=1")
        conn.close()
        return {
            "item": "Database Connectivity (PostgreSQL/pgvector)",
            "status": "PASS",
            "details": "Local PostgreSQL connected at 127.0.0.1:5432"
        }
    except Exception as e:
        return {
            "item": "Database Connectivity (PostgreSQL/pgvector)",
            "status": "OPTIONAL_MISSING",
            "details": f"PostgreSQL not running locally ({e}). Planned for storage phase."
        }

def check_free_disk_space():
    disk = psutil.disk_usage("C:\\")
    free_gb = round(disk.free / (1024**3), 2)
    total_gb = round(disk.total / (1024**3), 2)
    # Require at least 5 GB free
    passed = free_gb >= 5.0
    return {
        "item": "Free Disk Space (C:)",
        "status": "PASS" if passed else "FAIL",
        "details": f"{free_gb} GB free out of {total_gb} GB ({round(100 - disk.percent, 1)}% available)"
    }

def main():
    print("=" * 70)
    print("       DOCUMIND ENVIRONMENT VERIFICATION REPORT")
    print("=" * 70)

    checks = [
        check_python(),
        check_backend_dependencies(),
        check_ollama_executable(),
        check_ollama_service(),
        check_language_model(),
        check_local_generation(),
        check_embedding_model(),
        check_database_connectivity(),
        check_free_disk_space(),
    ]

    all_passed = True
    for res in checks:
        status = res["status"]
        status_display = f"[{status}]".ljust(18)
        item_display = res["item"].ljust(35)
        print(f"{item_display} {status_display} : {res['details']}")
        if status == "FAIL":
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("RESULT: ALL REQUIRED ENVIRONMENT CHECKS PASSED.")
    else:
        print("RESULT: ONE OR MORE REQUIRED CHECKS FAILED.")
    print("=" * 70)

    with open("environment_verification.json", "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=2)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
