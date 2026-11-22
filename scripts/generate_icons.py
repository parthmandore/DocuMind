"""
Generate high-fidelity DocuMind application icons and favicons across all standard resolutions:
- favicon.svg
- favicon-16x16.png
- favicon-32x32.png
- favicon-48x48.png
- apple-touch-icon.png (180x180)
- icon-192.png (192x192)
- icon-512.png (512x512)
- favicon.ico (16x16 + 32x32 ICO container)
"""

import os
import struct
from pathlib import Path
import pymupdf

PUBLIC_DIR = str(Path(__file__).resolve().parents[1] / "frontend" / "public")

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1E1B4B" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <linearGradient id="docGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6366F1" />
      <stop offset="100%" stop-color="#4F46E5" />
    </linearGradient>
    <linearGradient id="foldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#A5B4FC" />
      <stop offset="100%" stop-color="#818CF8" />
    </linearGradient>
    <linearGradient id="gemGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34D399" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Squircle App Background -->
  <rect x="16" y="16" width="480" height="480" rx="112" ry="112" fill="url(#bgGrad)" stroke="#312E81" stroke-width="6" />

  <!-- Document Sheet Body with Folded Corner -->
  <path d="M144 96 H304 L384 176 V384 C384 401.673 369.673 416 352 416 H144 C126.327 416 112 401.673 112 384 V128 C112 110.327 126.327 96 144 96 Z"
        fill="url(#docGrad)" />

  <!-- Folded Corner Flap -->
  <path d="M304 96 V160 C304 168.837 311.163 176 320 176 H384 Z"
        fill="url(#foldGrad)" />

  <!-- Document Text Line Bars -->
  <rect x="160" y="212" width="160" height="24" rx="8" fill="#FFFFFF" fill-opacity="0.9" />
  <rect x="160" y="260" width="192" height="20" rx="6" fill="#C7D2FE" fill-opacity="0.8" />
  <rect x="160" y="300" width="128" height="20" rx="6" fill="#C7D2FE" fill-opacity="0.8" />

  <!-- Grounding Verification Sparkle / Neural Node (Bottom Right) -->
  <g transform="translate(356, 368)">
    <circle cx="0" cy="0" r="44" fill="#0F172A" stroke="#10B981" stroke-width="6" />
    <circle cx="0" cy="0" r="32" fill="url(#gemGrad)" filter="url(#glow)" />
    <!-- Checkmark / Star in Node -->
    <path d="M-12 1 L-3 10 L14 -9" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
  </g>
</svg>"""

def create_ico(icon_png_data_list, output_ico_path):
    """
    Combine multiple PNG byte streams into an ICO container format.
    icon_png_data_list is a list of (width, height, png_bytes)
    """
    # ICO Header: 2 bytes reserved (0), 2 bytes type (1 for ICO), 2 bytes image count
    header = struct.pack("<HHH", 0, 1, len(icon_png_data_list))
    
    entries = []
    offset = 6 + (16 * len(icon_png_data_list))
    image_data_blocks = []
    
    for width, height, data in icon_png_data_list:
        w_byte = 0 if width >= 256 else width
        h_byte = 0 if height >= 256 else height
        # Entry: width, height, color count (0), reserved (0), color planes (1), bpp (32), size, offset
        entry = struct.pack("<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, len(data), offset)
        entries.append(entry)
        image_data_blocks.append(data)
        offset += len(data)
        
    with open(output_ico_path, "wb") as f:
        f.write(header)
        for e in entries:
            f.write(e)
        for d in image_data_blocks:
            f.write(d)

def main():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    
    # 1. Write favicon.svg
    svg_path = os.path.join(PUBLIC_DIR, "favicon.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT)
    print(f"Wrote {svg_path}")

    # 2. Render PNG resolutions using PyMuPDF
    svg_doc = pymupdf.open(stream=SVG_CONTENT.encode("utf-8"), filetype="svg")
    page = svg_doc[0]

    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "favicon-48x48.png": 48,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }

    png_cache = {}

    for filename, size in sizes.items():
        # Scale matrix
        zoom = size / 512.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        out_path = os.path.join(PUBLIC_DIR, filename)
        pix.save(out_path)
        png_cache[size] = pix.tobytes("png")
        print(f"Generated {out_path} ({size}x{size})")

    # 3. Create favicon.ico containing 16x16 and 32x32
    ico_path = os.path.join(PUBLIC_DIR, "favicon.ico")
    ico_entries = [
        (16, 16, png_cache[16]),
        (32, 32, png_cache[32]),
        (48, 48, png_cache[48]),
    ]
    create_ico(ico_entries, ico_path)
    print(f"Generated multi-res {ico_path}")

if __name__ == "__main__":
    main()
