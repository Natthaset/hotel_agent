import io
import os
import re
import csv
import shutil
import logging
import zipfile
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("ai_orchestrator.file_parser")

_markitdown_instance = None

def get_markitdown():
    global _markitdown_instance
    if _markitdown_instance is None:
        try:
            from markitdown import MarkItDown
            _markitdown_instance = MarkItDown()
            logger.info("Microsoft MarkItDown multi-format converter initialized successfully.")
        except Exception as ex:
            logger.warning("Microsoft MarkItDown initialization error (%s). Using fallback parsers.", ex)
    return _markitdown_instance

def generate_suggested_title(filename: str) -> str:
    """
    Cleans up a filename to generate a readable human-friendly document title.
    Example: 'resort_pool_rules_2026.docx' -> 'Resort Pool Rules 2026'
    """
    stem = Path(filename).stem
    # Replace underscores, hyphens, and dots with spaces
    cleaned = re.sub(r'[-_.]+', ' ', stem).strip()
    # Capitalize title words nicely
    words = [w.capitalize() if not w.isupper() else w for w in cleaned.split()]
    return " ".join(words) if words else "New Hotel Policy"

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decodes plain text with automatic fallback for Thai/Latin encodings."""
    for enc in ["utf-8", "utf-8-sig", "tis-620", "cp874", "latin-1"]:
        try:
            return file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return file_bytes.decode("utf-8", errors="ignore")

def extract_text_from_csv(file_bytes: bytes) -> str:
    """Parses CSV content into human-readable pipe-delimited table rows."""
    raw_text = extract_text_from_txt(file_bytes)
    reader = csv.reader(io.StringIO(raw_text))
    lines = []
    for row in reader:
        cleaned_cells = [c.strip() for c in row if c is not None]
        if cleaned_cells and any(cleaned_cells):
            lines.append(" | ".join(cleaned_cells))
    return "\n".join(lines)

def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extracts text paragraphs from a .docx file by inspecting word/document.xml
    without requiring third-party libraries.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_data = z.read("word/document.xml")
            tree = ET.fromstring(xml_data)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.iterfind(".//w:p", ns):
                texts = [node.text for node in p.iterfind(".//w:t", ns) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n".join(paragraphs)
    except Exception as ex:
        logger.warning("Pure Python docx extraction failed: %s", ex)
        # Fallback to macOS textutil if available
        if shutil.which("textutil"):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                cmd = ["textutil", "-convert", "txt", "-stdout", tmp_path]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    return res.stdout.strip()
            except Exception:
                pass
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        raise ValueError(f"Unable to read Word (.docx) document: {ex}")

def extract_text_from_xlsx(file_bytes: bytes) -> str:
    """
    Extracts table rows from .xlsx file by parsing sharedStrings.xml and sheet XMLs
    using Python built-in zipfile and ElementTree.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            names = z.namelist()
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            
            # Read shared strings table
            shared_strings = []
            if "xl/sharedStrings.xml" in names:
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in tree.findall(".//s:si", ns):
                    t_nodes = si.findall(".//s:t", ns)
                    shared_strings.append("".join([t.text or "" for t in t_nodes]))

            # Read worksheets
            sheet_files = [n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
            all_rows = []
            for sheet_file in sorted(sheet_files):
                tree = ET.fromstring(z.read(sheet_file))
                for row in tree.findall(".//s:row", ns):
                    cells = []
                    for c in row.findall(".//s:c", ns):
                        t = c.attrib.get("t")
                        v = c.find(".//s:v", ns)
                        val = v.text if v is not None and v.text else ""
                        if t == "s" and val.isdigit():
                            idx = int(val)
                            if 0 <= idx < len(shared_strings):
                                val = shared_strings[idx]
                        cells.append(val.strip())
                    if cells and any(cells):
                        all_rows.append(" | ".join(cells))
            return "\n".join(all_rows)
    except Exception as ex:
        logger.error("Failed to parse Excel .xlsx file: %s", ex)
        raise ValueError(f"Unable to read Excel (.xlsx) file: {ex}")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from PDF documents.
    Prefers native macOS PDFKit for perfect rendering & Thai language support,
    with robust pure-Python stream fallback for containerized environments.
    """
    # 1. Native macOS PDFKit
    if shutil.which("swift"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            swift_script = (
                "import PDFKit; import Foundation; "
                "let u = URL(fileURLWithPath: CommandLine.arguments[1]); "
                "if let d = PDFDocument(url: u) { "
                "  let txt = (0..<d.pageCount).compactMap { d.page(at: $0)?.string }.joined(separator: \"\\n\\n\"); "
                "  print(txt); "
                "}"
            )
            res = subprocess.run(["swift", "-e", swift_script, tmp_path], capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as ex:
            logger.warning("Native Swift PDFKit extraction skipped: %s", ex)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    # 2. Pure Python FlateDecode Stream Fallback
    import zlib
    texts = []
    streams = re.findall(rb'stream[\r\n]+(.*?)[\r\n]+endstream', file_bytes, re.DOTALL)
    for s in streams:
        decompressed = None
        for wbits in [15, -15, 31, 47]:
            try:
                decompressed = zlib.decompress(s, wbits)
                break
            except Exception:
                continue
        if decompressed is None:
            decompressed = s

        # Find Tj string operators
        tj_matches = re.findall(rb'\((.*?)\)\s*Tj', decompressed)
        for m in tj_matches:
            for enc in ['utf-8', 'tis-620', 'latin1']:
                try:
                    t = m.decode(enc)
                    if t.strip():
                        texts.append(t.strip())
                    break
                except Exception:
                    continue

        # Find TJ array operators
        tj_blocks = re.findall(rb'\[(.*?)\]\s*TJ', decompressed)
        for blk in tj_blocks:
            parts = re.findall(rb'\((.*?)\)', blk)
            for p in parts:
                for enc in ['utf-8', 'tis-620', 'latin1']:
                    try:
                        t = p.decode(enc)
                        if t.strip():
                            texts.append(t.strip())
                        break
                    except Exception:
                        continue

    if texts:
        return " ".join(texts)
    
    return "เอกสาร PDF ได้รับการประมวลผลแล้ว (ไม่มีข้อความในรูปแบบ Text Layer หรือเป็นเอกสารสแกน)"

def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Extracts text from image files (.png, .jpg, .jpeg, .webp) using
    Apple Vision Framework OCR (high accuracy, native Apple Neural Engine, Thai & English support).
    """
    if shutil.which("swift"):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            swift_script = """
import Vision
import Foundation
import AppKit

let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let img = NSImage(contentsOf: url),
      let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    exit(1)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages = ["th-TH", "en-US"]
let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
try? handler.perform([req])
let texts = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }
print(texts.joined(separator: "\\n"))
"""
            res = subprocess.run(["swift", "-e", swift_script, tmp_path], capture_output=True, text=True, timeout=20)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as ex:
            logger.warning("Apple Vision OCR failed or skipped: %s", ex)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return "รูปภาพได้รับการอัปโหลดเรียบร้อยแล้ว (ไม่พบตัวอักษรหรือข้อความที่สามารถอ่านได้ในรูปภาพ)"

def extract_file_content(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    """
    High-level entry point:
    1. Uses Microsoft MarkItDown as primary multi-format parser for Linux, Docker, Windows, and macOS.
    2. Gracefully falls back to pure-Python/built-in parsers if MarkItDown encounters format-specific nuances.
    Returns: (extracted_text, suggested_title)
    """
    ext = Path(filename).suffix.lower()
    title = generate_suggested_title(filename)

    # 1. Primary Engine: Microsoft MarkItDown
    md = get_markitdown()
    if md is not None:
        try:
            stream = io.BytesIO(file_bytes)
            result = md.convert_stream(stream, file_extension=ext)
            if result and result.text_content and result.text_content.strip():
                extracted = result.text_content.strip()
                logger.info("Successfully parsed '%s' using Microsoft MarkItDown (%d chars).", filename, len(extracted))
                return extracted, title
        except Exception as ex:
            logger.info("MarkItDown conversion note for %s (%s). Using fallback parser.", filename, ex)

    # 2. Defensive Fallback to format-specific parsers
    if ext in [".txt", ".md", ".json", ".yaml", ".yml"]:
        content = extract_text_from_txt(file_bytes)
    elif ext in [".csv", ".tsv"]:
        content = extract_text_from_csv(file_bytes)
    elif ext in [".docx", ".doc"]:
        content = extract_text_from_docx(file_bytes)
    elif ext in [".xlsx", ".xls"]:
        content = extract_text_from_xlsx(file_bytes)
    elif ext == ".pdf":
        content = extract_text_from_pdf(file_bytes)
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        content = extract_text_from_image(file_bytes)
    else:
        # Default try text decode
        try:
            content = extract_text_from_txt(file_bytes)
        except Exception:
            raise ValueError(f"ไฟล์นามสกุล '{ext}' ไม่รองรับ กรุณาอัปโหลดไฟล์ PDF, Image, Word, Text, Excel หรือ CSV ค่ะ")

    cleaned_content = content.strip()
    if not cleaned_content:
        cleaned_content = f"เอกสาร {filename} ได้รับการนำเข้าสู่ระบบเรียบร้อยแล้ว"

    return cleaned_content, title
