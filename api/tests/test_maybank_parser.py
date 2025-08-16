from __future__ import annotations
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app.parsers.maybank import parse_maybank_pdf


def _build_pdf(lines: list[str]) -> bytes:
    """
    Build an in‑memory PDF from a list of text lines.  Each line is drawn
    at a decreasing y position on a single page.  This helper is used to
    simulate Maybank statement layouts in tests without relying on external
    files.
    """
    bio = io.BytesIO()
    c = canvas.Canvas(bio, pagesize=letter)
    y = 750
    for line in lines:
        c.drawString(30, y, line)
        y -= 20
    c.showPage(); c.save()
    return bio.getvalue()


def test_parse_sample_rows():
    """Ensure the parser extracts rows and normalises fields correctly."""
    lines = [
        "STATEMENT OF CREDIT CARD ACCOUNT",
        "Statement Date/",
        "12 JUL 25",
        "KHAIRUL ANWAR    VISA IKHWAN PLATINUM      1234 5678 9012 7141",
        "Posting Date / Tarikh Pos    Transaction Date / Tarikh Transaksi    Transaction Description / Huraian Transaksi    Amount (RM) / Amaun (RM)",
        # Example rows from the spec
        "01/07 30/06 WATSON'S LOTUS'S MUTIARA JOHOR MY 30.40",
        "01/07 30/06 CASH REBATE 9.52CR",
        "18/06 18/06 PYMT@MAYBANK2U.COM 3,198.71CR",
    ]
    pdf = _build_pdf(lines)
    rows = parse_maybank_pdf(pdf)
    # We expect three rows from the above lines
    assert len(rows) == 3
    # First row
    r0 = rows[0]
    assert r0["card_last4"] == "7141"
    assert r0["posting_date"] == "2025-07-01"
    assert r0["transaction_date"] == "2025-06-30"
    assert r0["amount"] == 30.40
    assert r0["category"] == "Personal Care"
    # Second row is a rebate (credit)
    r1 = rows[1]
    assert r1["amount"] == -9.52
    assert r1["category"] == "Rebate"
    # Third row is a payment (credit)
    r2 = rows[2]
    assert r2["amount"] == -3198.71
    assert r2["category"] == "Payment"