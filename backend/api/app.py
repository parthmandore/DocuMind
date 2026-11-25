"""DocuMind FastAPI Application Entrypoint

Local-first document intelligence REST API with production security hardening.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.config import config
from backend.api.routes import api_router
from backend.db.base import init_db

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Production security headers middleware.
    
    Enforces MIME-sniffing prevention, frame isolation (clickjacking defense),
    browser feature restrictions, content security policy, and conditional HSTS.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Defensive security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        
        # Content Security Policy tailored for DocuMind:
        # Allows local scripts, styles, PDF.js web worker blobs, and authorized API endpoints.
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' blob:",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            "connect-src 'self' http://localhost:3000 http://127.0.0.1:3000 http://localhost:8000 http://127.0.0.1:8000 http://localhost:8008 http://127.0.0.1:8008 ws://localhost:3000 ws://127.0.0.1:3000 https://api.groq.com",
            "worker-src 'self' blob:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # HSTS: Enforced ONLY over genuine HTTPS/TLS or forwarded HTTPS proxy, NEVER on local HTTP
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto", "").lower() == "https"
        )
        if is_https and config.enable_hsts:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist, reconcile orphaned jobs, and resume CHUNKED docs waiting on Ollama
    init_db()
    from backend.jobs.worker import reconcile_orphaned_jobs, schedule_waiting_embeddings_resume
    reconcile_orphaned_jobs()
    schedule_waiting_embeddings_resume(force=True)
    yield

app = FastAPI(
    title="DocuMind API",
    version="0.2.0",
    description="Local-first AI Document Intelligence API with grounded citation validation.",
    lifespan=lifespan
)

# 1. Attach Security Headers Middleware (outer layer)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS configuration with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "app": config.app_name,
        "version": "0.2.0",
        "mode": "local-only",
        "docs_url": "/docs"
    }
