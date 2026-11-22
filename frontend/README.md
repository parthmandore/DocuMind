# DocuMind Frontend Foundation

The DocuMind user interface is designed as a local-first web application enabling side-by-side document examination and grounding verification.

## Architecture

```
frontend/
├── package.json         # Dependency manifest
├── src/
│   ├── app/             # Next.js App Router (local client-side views)
│   ├── components/      # UI components:
│   │   ├── DocumentViewer/   # Side-by-side PDF / Markdown viewer with bounding box overlay
│   │   ├── ChatInterface/    # Local LLM conversation interface
│   │   └── CitationPanel/    # Grounding & citation inspector
│   └── lib/             # API client connecting to local backend at 127.0.0.1
```

## Key UI Principles
1. **Side-by-Side Verification**: Answer and source PDF displayed concurrently.
2. **Bounding Box Highlighting**: Clicking any cited passage navigates the document viewer directly to the exact page and highlights the corresponding bounding box coordinates.
3. **Reasoning Transparency**: Optional expandable drawer to view the local model's thinking trace.
4. **100% Offline**: No remote CDNs or external asset loading.
