from __future__ import annotations
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from app.parser import parse_pdf_bytes


def _fake_pdf(rows):
    bio = io.BytesIO()
    c = canvas.Canvas(bio, pagesize=letter)
    y = 750
    c.drawString(30, 770, "Date | Description | Amount")
    for d, desc, amt in rows:
        c.drawString(30, y, f"{d} {desc} {amt}")
        y -= 20
    c.showPage(); c.save()
    return bio.getvalue()


def test_parse_simple_pdf():
    pdf = _fake_pdf([
        ("01/07/2025", "PETRONAS STN 123", "-50.25"),
        ("02/07/2025", "SALARY", "2000.00"),
    ])
    rows = parse_pdf_bytes(pdf)
    assert isinstance(rows, list)


def test_parse_has_rows():
    pdf = _fake_pdf([
        ("03/07/2025", "TNG Ewallet", "-10.00"),
        ("05/07/2025", "GrabFood", "-22.90"),
    ])
    rows = parse_pdf_bytes(pdf)
    assert len(rows) >= 1
