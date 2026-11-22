# Changelog

All notable changes to DocuMind are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.1] - 2026-11-14

### Added
- **Production Security Headers Middleware:** Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, comprehensive Content Security Policy (CSP), and conditional HSTS (`Strict-Transport-Security` over HTTPS only).
- **Rate-Limited Support & Feedback Intake:** Deployed `POST /api/support/contact` with Pydantic validation, client IP rate limiting (5 req / 10 min), anti-spam hidden honeypot (`website`), email masking (`j***n@domain.com`), and configurable SMTP delivery with local fallback.
- **Privacy-Preserving Milestone Telemetry:** Added opt-in, disabled-by-default milestone tracker (`telemetry.ts`) with automatic sanitization stripping all document, query, citation, and credential keys.
- **Next-Gen Asset Encoding:** Converted social preview cards and launcher icons into WebP and AVIF formats, achieving up to 62.0% byte reductions while preserving backward-compatible PNG fallbacks.
- **Route-Level Dynamic Code Splitting:** Converted all application routes to `React.lazy()` with `<Suspense>` boundaries, reducing initial entry JavaScript from 844.8 kB to 60.8 kB (-92.8%) and entry CSS from 152.4 kB to 40.8 kB (-73.3%).
- **Technical SEO & Structured Data:** Generated Schema.org JSON-LD (`WebSite`, `SoftwareApplication`, `BreadcrumbList`), hierarchical breadcrumbs, strictly bounded `sitemap.xml`, and search engine crawl directives in `robots.txt`.
- **UX & Accessibility Hardening:** Implemented custom 404 error recovery page, stack-trace concealing `ErrorBoundary` for production builds, centralized `ToastContext` notification engine, and multi-state loading skeletons.

### Changed
- Parameterized CORS via `config.cors_allowed_origins` for production environment configuration.
- Reorganized repository structure by moving ad-hoc audit and benchmark scripts into `scripts/`.
- Purged transient build artifacts and bytecode caches.

---

## [0.2.0] - 2026-11-13

### Added
- **Dual AI Provider Architecture:** Dynamic provider switching between Local Ollama (`qwen3:4b`) and Groq Cloud (`qwen/qwen3.8-27b`) via `/api/settings/ai-provider`.
- **Hybrid Retrieval Engine:** Combines Okapi BM25 keyword matching with 768-dimensional local `nomic-embed-text` dense vector embeddings using Reciprocal Rank Fusion (RRF).
- **Claim-Level Citation Verification:** Two-stage verification classifying claims into Supported, Partially Supported, Unsupported, Contradicted, or Insufficient Evidence.
- **Strict Document Isolation:** Cross-document search boundaries and single-document query scoping with automated cross-document abstention.
- **Interactive PDF Viewer:** Integrated `pdfjs-dist` PDF inspection with dynamic page navigation, search highlights, and citation bounding box overlays.
- **Persistent Multi-Turn Conversations:** Turn-by-turn context preservation and query resolution stored in SQLite with full conversation history and cascading cleanups.
- **Citation Analytics & Insights:** Dynamic claim verification support matrix, verification density stats, and reactive metric reconciliation.
- **Centralized Design Token System:** Modern responsive dark/light visual identity built with Tailwind CSS, Lucide icons, and accessible focus states.
- **Comprehensive Test Suite:** 29 backend test suites covering parsing, retrieval, verification, and isolation; 4 frontend test suites (96 tests) covering state management, components, and design tokens.

### Changed
- Refactored text ingestion with PyMuPDF layout-aware chunking and typographic ligature normalization.
- Hardened Groq rate limit handling (HTTP 429) and single-flight concurrency arbitration.

---

## [0.1.0] - 2026-11-03

### Initial Release
- Initial prototype featuring document upload, SQLite persistence, and local LLM proof-of-concept.
