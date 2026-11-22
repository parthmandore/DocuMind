import fitz  # PyMuPDF
import os

def create_single_column_pdf(output_path: str):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Standard Letter
    
    # Title
    page.insert_text(fitz.Point(54, 72), "Apex Global Logistics — Operational Audit Report", fontsize=16, fontname="helv", color=(0, 0, 0.5))
    page.insert_text(fitz.Point(54, 96), "Executive Summary & Operational Protocol Review", fontsize=12, fontname="helv", color=(0.3, 0.3, 0.3))
    
    # Body Paragraph 1
    p1 = (
        "In fiscal year 2025, Apex Global Logistics expanded its core European sorting hub "
        "network with the inauguration of the Rotterdam Central Facility in the Netherlands. "
        "The automated terminal processes up to 1,200,000 package units per operating cycle with "
        "an average optical barcode read reliability rate of 99.84%. Initial throughput testing "
        "demonstrated zero mechanical conveyor stalls during peak holiday throughput shifts."
    )
    rect1 = fitz.Rect(54, 120, 558, 200)
    page.insert_textbox(rect1, p1, fontsize=10, fontname="helv", color=(0, 0, 0))
    
    # Section 2
    page.insert_text(fitz.Point(54, 220), "1.1 Mandatory Compliance Protocols", fontsize=12, fontname="helv", color=(0, 0, 0.5))
    p2 = (
        "Operating teams must verify that all package telemetry data is mirrored across local "
        "hot-standby storage arrays. Section 4.2 of the data compliance handbook dictates a "
        "mandatory retention window of exactly 365 calendar days for all sorting scans. Purge "
        "routines must initiate automatically within 14 business days following threshold expiry."
    )
    rect2 = fitz.Rect(54, 240, 558, 330)
    page.insert_textbox(rect2, p2, fontsize=10, fontname="helv", color=(0, 0, 0))
    
    # Footer
    page.insert_text(fitz.Point(54, 750), "Confidential — Internal Operations — Page 1 of 1", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    doc.save(output_path)
    doc.close()
    print(f"Created single-column PDF at {output_path}")

def create_multi_column_pdf(output_path: str):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    
    # Header spanning both columns
    page.insert_text(fitz.Point(54, 60), "Horizon Cloud Architecture Review", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text(fitz.Point(54, 80), "Dual-Column Structural Assessment and Edge Router Protocols", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
    
    # Column 1 (Left: x=54 to 290)
    page.insert_text(fitz.Point(54, 110), "Left Column: Ingestion Engine", fontsize=11, fontname="helv", color=(0, 0, 0))
    col1_text = (
        "The edge ingestion layer receives incoming REST and gRPC API payloads across public "
        "Internet transit nodes. Rate limiting is enforced through token bucket algorithms with "
        "a strict cap of 100 requests per minute for unauthenticated diagnostic calls. Payloads "
        "exceeding 15 MB are systematically rejected with HTTP 413. Session state is decentralized "
        "into distributed cache nodes to ensure horizontal resilience across multi-region edge clusters."
    )
    rect_col1 = fitz.Rect(54, 125, 290, 360)
    page.insert_textbox(rect_col1, col1_text, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
    
    # Column 2 (Right: x=320 to 558)
    page.insert_text(fitz.Point(320, 110), "Right Column: Security Policy", fontsize=11, fontname="helv", color=(0, 0, 0))
    col2_text = (
        "Security hardening directives mandate TLS 1.3 encryption across all outer-perimeter "
        "interfaces. Cryptographic signature verification employs ECDSA over curve P-256 with "
        "SHA-256 (ES256). In case of confirmed boundary violations, automated intrusion response "
        "systems quarantine affected container namespaces within 120 milliseconds while dispatching "
        "incident telemetry to the centralized Security Operations Center (SOC)."
    )
    rect_col2 = fitz.Rect(320, 125, 558, 360)
    page.insert_textbox(rect_col2, col2_text, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
    
    page.insert_text(fitz.Point(54, 750), "Document ID: HORIZON-TECH-2026 — Page 1", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    doc.save(output_path)
    doc.close()
    print(f"Created multi-column PDF at {output_path}")

def create_table_dense_pdf(output_path: str):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    
    page.insert_text(fitz.Point(54, 60), "Industrial Hardware Specifications & Maintenance Schedule", fontsize=15, fontname="helv", color=(0, 0.2, 0.3))
    page.insert_text(fitz.Point(54, 80), "Table 1: Turbo-Compressor Model Operating Parameters", fontsize=11, fontname="helv", color=(0.3, 0.3, 0.3))
    
    # Draw table bounding box and grid
    start_y = 100
    row_height = 28
    col_widths = [100, 100, 100, 100, 104]
    col_x = [54]
    for w in col_widths:
        col_x.append(col_x[-1] + w)
        
    headers = ["Model", "Displacement", "Max RPM", "Vibration Cap", "Lube Oil Spec"]
    rows = [
        ["Vang-100", "4,200 m3/h", "7,500 RPM", "4.5 mm/s RMS", "ISO VG 32"],
        ["Vang-200", "8,800 m3/h", "9,200 RPM", "5.8 mm/s RMS", "ISO VG 46"],
        ["Vang-500", "16,500 m3/h", "11,400 RPM", "7.1 mm/s RMS", "ISO VG 46 Synth"],
        ["Vang-900", "28,000 m3/h", "14,000 RPM", "8.2 mm/s RMS", "ISO VG 68 Synth"]
    ]
    
    # Draw header row background
    page.draw_rect(fitz.Rect(54, start_y, 558, start_y + row_height), color=(0, 0, 0), fill=(0.9, 0.9, 0.95))
    for i, h in enumerate(headers):
        page.insert_text(fitz.Point(col_x[i] + 8, start_y + 18), h, fontsize=9.5, fontname="hebo")
        
    curr_y = start_y + row_height
    for r_idx, row in enumerate(rows):
        bg = (1, 1, 1) if r_idx % 2 == 0 else (0.97, 0.97, 0.97)
        page.draw_rect(fitz.Rect(54, curr_y, 558, curr_y + row_height), color=(0.8, 0.8, 0.8), fill=bg)
        for c_idx, cell in enumerate(row):
            page.insert_text(fitz.Point(col_x[c_idx] + 8, curr_y + 18), cell, fontsize=9, fontname="helv")
        curr_y += row_height
        
    # Footnote below table
    page.insert_text(fitz.Point(54, curr_y + 25), "Note: Operating vibrations exceeding 7.1 mm/s RMS require immediate emergency cycle trip.", fontsize=8.5, fontname="heit", color=(0.4, 0.4, 0.4))
    
    page.insert_text(fitz.Point(54, 750), "Document ID: VANGUARD-SPEC-900 — Page 1", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    doc.save(output_path)
    doc.close()
    print(f"Created table-dense PDF at {output_path}")

if __name__ == "__main__":
    out_dir = "tests/fixtures/pdfs"
    os.makedirs(out_dir, exist_ok=True)
    create_single_column_pdf(os.path.join(out_dir, "single_column_report.pdf"))
    create_multi_column_pdf(os.path.join(out_dir, "multi_column_article.pdf"))
    create_table_dense_pdf(os.path.join(out_dir, "table_dense_spec.pdf"))
