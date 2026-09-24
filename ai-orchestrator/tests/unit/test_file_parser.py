import io
import zipfile
import pytest
from rag.file_parser import (
    generate_suggested_title,
    extract_text_from_txt,
    extract_text_from_csv,
    extract_text_from_docx,
    extract_text_from_xlsx,
    extract_file_content
)

def test_generate_suggested_title():
    assert generate_suggested_title("luxury_infinity_pool_policy.pdf") == "Luxury Infinity Pool Policy"
    assert generate_suggested_title("pet-rules-2026.docx") == "Pet Rules 2026"
    assert generate_suggested_title("breakfast_menu.csv") == "Breakfast Menu"

def test_extract_text_from_txt():
    content = "กฎการใช้บริการสระว่ายน้ำ เปิดเวลา 07:00 - 21:00 น."
    data = content.encode("utf-8")
    extracted = extract_text_from_txt(data)
    assert "สระว่ายน้ำ" in extracted
    assert "07:00 - 21:00" in extracted

def test_extract_text_from_csv():
    csv_data = "Service,Hours,Location\nFitness,24 Hours,Level 3\nSpa,10:00 - 22:00,Ground Floor".encode("utf-8")
    extracted = extract_text_from_csv(csv_data)
    assert "Fitness | 24 Hours | Level 3" in extracted
    assert "Spa | 10:00 - 22:00 | Ground Floor" in extracted

def test_extract_text_from_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:body>
                <w:p><w:r><w:t>Late Check-out Regulation</w:t></w:r></w:p>
                <w:p><w:r><w:t>Available until 14:00 upon request.</w:t></w:r></w:p>
            </w:body>
        </w:document>"""
        z.writestr("word/document.xml", xml_content)
    
    extracted = extract_text_from_docx(buf.getvalue())
    assert "Late Check-out Regulation" in extracted
    assert "Available until 14:00 upon request." in extracted

def test_extract_text_from_xlsx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        shared_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">
            <si><t>Room</t></si>
            <si><t>Price</t></si>
            <si><t>Penthouse</t></si>
            <si><t>25000</t></si>
        </sst>"""
        sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
            <sheetData>
                <row r="1">
                    <c r="A1" t="s"><v>0</v></c>
                    <c r="B1" t="s"><v>1</v></c>
                </row>
                <row r="2">
                    <c r="A2" t="s"><v>2</v></c>
                    <c r="B2" t="s"><v>3</v></c>
                </row>
            </sheetData>
        </worksheet>"""
        z.writestr("xl/sharedStrings.xml", shared_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    extracted = extract_text_from_xlsx(buf.getvalue())
    assert "Room | Price" in extracted
    assert "Penthouse | 25000" in extracted

def test_extract_file_content_dispatcher():
    # Test CSV dispatch
    csv_bytes = "Amenity,Status\nFree Wi-Fi,Active".encode("utf-8")
    content, title = extract_file_content("hotel_amenities.csv", csv_bytes)
    assert title == "Hotel Amenities"
    assert "Free Wi-Fi" in content

def test_markitdown_integration():
    from rag.file_parser import get_markitdown
    md = get_markitdown()
    assert md is not None

    markdown_doc = "# Grand Azure Rules\n\n- No smoking in suites\n- 24/7 Concierge available".encode("utf-8")
    content, title = extract_file_content("hotel_rules.md", markdown_doc)
    assert title == "Hotel Rules"
    assert "Grand Azure Rules" in content
    assert "No smoking" in content
