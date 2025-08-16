from __future__ import annotations
import io
import pdfplumber
import pandas as pd
import tabula
from datetime import datetime
from typing import Iterable

# Minimal, Malaysia-friendly heuristics. Adjust per bank format.
DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

def _coerce_date(s: str):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except Exception:
            continue
    return None

def parse_pdf_bytes(data: bytes) -> list[dict]:
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
                    rows.append({"raw": r, "txn_date": _coerce_date(str(r[0]) if len(r)>0 else ""), "description": desc.strip(), "amount": amt})
    except Exception:
        pass
    return rows
