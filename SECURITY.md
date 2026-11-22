# Security Policy & Responsible Disclosure

DocuMind is an open-source document intelligence and research assistant. We take the privacy and security of enterprise documents, user data, and API credentials seriously.

---

## 1. Supported Versions

| Version | Supported |
|---|---|
| 0.2.x | :white_check_mark: Active |
| < 0.2.0 | :x: End of Life |

---

## 2. Reporting a Vulnerability

If you discover a security vulnerability or credential exposure in DocuMind:

1. **Do NOT open a public GitHub issue.** Public disclosure exposes existing users to risk before a patch is available.
2. Report the vulnerability privately to the project maintainers via GitHub's **Private Vulnerability Reporting** feature in the repository's "Security" tab.
3. Include detailed steps to reproduce the issue, along with any proof-of-concept material.

We will acknowledge receipt within 48 hours and work with you on a timeline for verification and remediation.

---

## 3. Privacy & Data Handling Guarantees

- **Local Storage by Default:** Ingested documents, text extracts, SQLite database rows, and vector embeddings remain strictly on the host machine running the DocuMind service.
- **Inference Transmission Notice:** When `AI_PROVIDER=groq` is active, selected evidence passages and user queries are transmitted over HTTPS to Groq Cloud for synthesis. Complete document files and unrelated corpus chunks are never transmitted.
- **Document Isolation Boundary:** Document boundaries are enforced at the retrieval layer via explicit SQL query filters. Cross-document contamination is treated as a security defect.
- **Zero Chain-of-Thought Leakage:** Internal AI thinking tokens and reasoning logs are strictly stripped before returning answers to user-facing APIs.
