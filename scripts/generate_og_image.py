"""
Generate the official 1200x630 DocuMind social preview image (Open Graph / Twitter Card).
Saved to frontend/public/og-image.png
"""

import os
from pathlib import Path
import pymupdf

OUTPUT_DIR = str(Path(__file__).resolve().parents[1] / "frontend" / "public")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "og-image.png")

SVG_OG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B0F17" />
      <stop offset="50%" stop-color="#111827" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>

    <!-- Subtle Glow Behind Emblem -->
    <radialGradient id="glowGrad" cx="30%" cy="50%" r="40%">
      <stop offset="0%" stop-color="#4F46E5" stop-opacity="0.35" />
      <stop offset="60%" stop-color="#4F46E5" stop-opacity="0.05" />
      <stop offset="100%" stop-color="#4F46E5" stop-opacity="0" />
    </radialGradient>

    <!-- Document Body Gradient -->
    <linearGradient id="docGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6366F1" />
      <stop offset="100%" stop-color="#4338CA" />
    </linearGradient>

    <!-- Folded Corner Gradient -->
    <linearGradient id="foldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#C7D2FE" />
      <stop offset="100%" stop-color="#818CF8" />
    </linearGradient>

    <!-- Emerald Verification Node -->
    <linearGradient id="gemGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34D399" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>

    <!-- Subtle Bounding Box Grid Pattern -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="1" stroke-opacity="0.6" />
    </pattern>
  </defs>

  <!-- Deep Background -->
  <rect width="1200" height="630" fill="url(#bgGrad)" />

  <!-- Grid Overlay -->
  <rect width="1200" height="630" fill="url(#grid)" />

  <!-- Ambient Glow -->
  <rect width="1200" height="630" fill="url(#glowGrad)" />

  <!-- Accent Border Top Bar -->
  <rect x="0" y="0" width="1200" height="4" fill="#4F46E5" />

  <!-- Brand Emblem Container (Left Side: x=140, y=175) -->
  <g transform="translate(140, 165)">
    <!-- Squircle Backdrop -->
    <rect x="0" y="0" width="220" height="220" rx="48" fill="#131B28" stroke="#1E293B" stroke-width="3" />

    <!-- Document Sheet Body -->
    <path d="M60 40 H135 L175 80 V175 C175 183.284 168.284 190 160 190 H60 C51.716 190 45 183.284 45 175 V55 C45 46.716 51.716 40 60 40 Z"
          fill="url(#docGrad)" />

    <!-- Folded Corner Flap -->
    <path d="M135 40 V72 C135 76.418 138.582 80 143 80 H175 Z"
          fill="url(#foldGrad)" />

    <!-- Document Content Lines -->
    <rect x="68" y="95" width="75" height="11" rx="4" fill="#FFFFFF" fill-opacity="0.95" />
    <rect x="68" y="118" width="90" height="9" rx="3.5" fill="#C7D2FE" fill-opacity="0.85" />
    <rect x="68" y="137" width="60" height="9" rx="3.5" fill="#C7D2FE" fill-opacity="0.85" />

    <!-- Grounding Verification Sparkle Node -->
    <g transform="translate(160, 168)">
      <circle cx="0" cy="0" r="22" fill="#0F172A" stroke="#10B981" stroke-width="3.5" />
      <circle cx="0" cy="0" r="16" fill="url(#gemGrad)" />
      <path d="M-6 0.5 L-1.5 5 L7 -4" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    </g>
  </g>

  <!-- Typography & Information Hierarchy (Right of Emblem) -->
  <g transform="translate(410, 175)">
    <!-- Eyebrow Tag -->
    <g transform="translate(0, 20)">
      <rect x="0" y="-18" width="220" height="28" rx="6" fill="#1E1B4B" stroke="#4F46E5" stroke-width="1.5" />
      <text x="12" y="1" font-family="'Inter', -apple-system, sans-serif" font-size="11" font-weight="700" fill="#818CF8" letter-spacing="1.5">
        LOCAL-FIRST AI ENGINE
      </text>
    </g>

    <!-- Main Title -->
    <text x="0" y="85" font-family="'Inter', -apple-system, sans-serif" font-size="64" font-weight="800" fill="#F8FAFC" letter-spacing="-1.5">
      DocuMind
    </text>

    <!-- Subtitle -->
    <text x="0" y="130" font-family="'Inter', -apple-system, sans-serif" font-size="22" font-weight="500" fill="#CBD5E1">
      Grounded Document Intelligence &amp; Research Assistant
    </text>

    <!-- Description Paragraph -->
    <text x="0" y="172" font-family="'Inter', -apple-system, sans-serif" font-size="15" font-weight="400" fill="#94A3B8">
      Synthesize verifiable research answers with exact PDF coordinate citations.
    </text>
    <text x="0" y="196" font-family="'Inter', -apple-system, sans-serif" font-size="15" font-weight="400" fill="#94A3B8">
      Air-gapped capable, two-stage claim verification, and hybrid vector retrieval.
    </text>
  </g>

  <!-- Bottom Feature Pill Badges -->
  <g transform="translate(140, 480)">
    <!-- Badge 1: Hybrid Retrieval -->
    <g transform="translate(0, 0)">
      <rect x="0" y="0" width="280" height="48" rx="12" fill="#131B28" stroke="#1E293B" stroke-width="1.5" />
      <circle cx="24" cy="24" r="6" fill="#6366F1" />
      <text x="42" y="29" font-family="'Inter', -apple-system, sans-serif" font-size="13" font-weight="600" fill="#E2E8F0">
        Hybrid Retrieval (Dense + BM25)
      </text>
    </g>

    <!-- Badge 2: Two-Stage Verification -->
    <g transform="translate(300, 0)">
      <rect x="0" y="0" width="290" height="48" rx="12" fill="#131B28" stroke="#1E293B" stroke-width="1.5" />
      <circle cx="24" cy="24" r="6" fill="#10B981" />
      <text x="42" y="29" font-family="'Inter', -apple-system, sans-serif" font-size="13" font-weight="600" fill="#E2E8F0">
        Two-Stage Claim Verification
      </text>
    </g>

    <!-- Badge 3: Dual Provider Engine -->
    <g transform="translate(610, 0)">
      <rect x="0" y="0" width="310" height="48" rx="12" fill="#131B28" stroke="#1E293B" stroke-width="1.5" />
      <circle cx="24" cy="24" r="6" fill="#38BDF8" />
      <text x="42" y="29" font-family="'Inter', -apple-system, sans-serif" font-size="13" font-weight="600" fill="#E2E8F0">
        Dual AI Routing (Groq &amp; Ollama)
      </text>
    </g>
  </g>
</svg>"""

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc = pymupdf.open(stream=SVG_OG.encode("utf-8"), filetype="svg")
    page = doc[0]
    mat = pymupdf.Matrix(1.0, 1.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(OUTPUT_FILE)
    print(f"Generated {OUTPUT_FILE} ({pix.width}x{pix.height})")

if __name__ == "__main__":
    main()
