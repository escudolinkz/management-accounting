from __future__ import annotations
import io
from datetime import datetime
from typing import Iterable

import pdfplumber
import pandas as pd
import tabula

# Generic date formats for the fallback parser
DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

# Import the Maybank parser
try:
    from app.parsers.maybank import parse_maybank_pdf
except Exception:
    parse_maybank_pdf = None  # type: ignore


def _coerce_date(s: str):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except Exception:
            continue
    return None


def parse_pdf_bytes(data: bytes) -> list[dict]:
    """
    Attempt to parse a PDF into a list of transaction dictionaries.  The
    function tries the Maybank parser first (for card statements) and if
    nothing is returned it falls back to a simple table extractor using
    pdfplumber or tabula.  The return value is intentionally generic: for
    statements parsed by the Maybank parser you will receive rich fields
    (posting_date, transaction_date, description, amount, category,
    subcategory, etc.), while the fallback returns only txn_date,
    description and amount.
    """
    # Try custom Maybank parser if available
    if parse_maybank_pdf:
        try:
            maybank_rows = parse_maybank_pdf(data)
            if maybank_rows:
                return maybank_rows
        except Exception:
            # if specialised parser fails we silently fall back to generic
            pass

    rows: list[dict] = []
    # Try pdfplumber table extract
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                tbls = page.extract_tables() or []
                for tbl in tbls:
                    # Expect columns like Date, Description, Amount
                    for r in tbl:
                        if not r or len([x for x in r if x]) < 2:
                            continue
                        cand = {
                            "txn_date": _coerce_date(str(r[0])) if len(r) > 0 else None,
                            "description": str(r[1]).strip() if len(r) > 1 else None,
                        }
                        amt = None
                        if len(r) >= 3 and r[2]:
                            try:
                                amt = float(str(r[2]).replace(",", "").replace("RM", "").strip())
                            except Exception:
                                amt = None
                        if cand["description"] and amt is not None:
                            cand["amount"] = amt
                            rows.append({"raw": r, **cand})
        if rows:
            return rows
    except Exception:
        pass
    # Fallback to tabula
    try:
        dfs = tabula.read_pdf(io.BytesIO(data), pages="all", stream=True, guess=False, multiple_tables=True)
        for df in dfs:
            for _, rr in df.iterrows():
                r = rr.tolist()
                if not r or len([x for x in r if pd.notna(x)]) < 2:
                    continue
                desc = str(r[1]) if len(r) > 1 else None
                amt = None
                try:
                    amt = float(str(r[2]).replace(",", "").replace("RM", "").strip()) if len(r) > 2 else None
                except Exception:
                    amt = None
                if desc and amt is not None:
                    rows.append({"raw": r, "txn_date": _coerce_date(str(r[0]) if len(r) > 0 else ""), "description": desc.strip(), "amount": amt})
    except Exception:
        pass
    return rows
