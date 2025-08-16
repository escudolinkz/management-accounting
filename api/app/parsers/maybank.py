"""
Parser for Maybank credit card statements (dual language versions).

This module implements a custom parser for the credit card statements issued
by Maybank (Visa Ikhwan).  The statements include two sections – a header
with the statement date and one or more card summaries followed by
transaction tables for each card.  Each transaction row contains a posting
date, transaction date, description and amount.  Credits are denoted by
either a trailing ``CR`` suffix, a leading minus sign or surrounding
parentheses.  The parser extracts each row and normalises the fields into
a structured dictionary.

Important parsing rules:

* Only rows between the transaction table headers (e.g. ``Posting Date / Tarikh
  Pos``) and the totals section (``TOTAL CREDIT THIS MONTH`` or
  ``SUB TOTAL/JUMLAH``) are parsed.
* The parser infers the year for posting and transaction dates from the
  statement date.  Dates always use the statement year except when the
  transaction month is greater than the statement month (i.e. cross-year
  transactions appearing in January statements), in which case the year is
  decremented by one.
* Description normalisation removes trailing country codes (``MY``, ``US``,
  ``IE``, etc.) and extra whitespace.  The full unmodified line is stored
  in ``description_raw``.
* A category mapping is applied using simple keyword rules defined in
  ``CATEGORY_MAPPING``.  First match wins (case insensitive).  Both category
  and subcategory fields are populated.

If the PDF does not match the expected Maybank format this parser returns
an empty list and should fall back to a generic parser.
"""

from __future__ import annotations
import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

# Map three‑letter month abbreviations to integers.  Statement months and
# transaction/posting months use English abbreviations.
MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# Special merchant keywords mapped to categories and subcategories.  These
# values are opinionated and can be customised further.  Keys should be
# uppercase and represent substrings of the cleaned description.  Values
# are tuples of (category, subcategory).  If subcategory is None it will
# be omitted.
CATEGORY_MAPPING: Dict[str, Tuple[str, Optional[str]]] = {
    "SETEL": ("Fuel", None),
    "99 SPEEDMART": ("Groceries", None),
    "WATSON": ("Personal Care", None),
    "LOTUS'S": ("Groceries", None),
    "AEON SMKT": ("Groceries", None),
    "AEON": ("Groceries", None),
    "MCDONALDS": ("Dining", None),
    "KRISPY KREME": ("Dining", None),
    "AUNTIE ANNE": ("Dining", None),
    "SHOPEE": ("Shopping", None),
    "SHOPEE-EC": ("Shopping", None),
    "SPAYLATER": ("Loan", None),
    "TNG-EWALLET": ("E-Wallet", None),
    "BIGPAY": ("E-Wallet", None),
    "PYMT@MAYBANK2U.COM": ("Payment", None),
    "CASH REBATE": ("Rebate", None),
    "APPLE.COM/BILL": ("Subscriptions", None),
    "HACKTHEBOX": ("Subscriptions", None),
    "THAI CHICKEN RICE": ("Dining", None),
}


def _infer_date(day_month: str, stmt_year: int, stmt_month: int) -> Optional[datetime.date]:
    """
    Given a string containing ``DD/MM`` and the statement year/month, infer
    the correct date.  If the month of the transaction is greater than the
    statement month it is assumed to belong to the previous year (e.g. an
    December transaction appearing on a January statement belongs to the
    previous year).
    """
    try:
        day, month = map(int, day_month.split("/"))
    except Exception:
        return None
    year = stmt_year
    if month > stmt_month:
        year -= 1
    try:
        return datetime(year, month, day).date()
    except Exception:
        return None


def _normalise_description(desc: str) -> Tuple[str, str]:
    """
    Clean up the transaction description by removing trailing country
    codes and excess spaces.  Returns a tuple of (cleaned, raw).
    """
    raw = desc.strip()
    # Remove repeated spaces
    cleaned = re.sub(r"\s+", " ", raw)
    # Remove trailing country code (two uppercase letters) if present
    cleaned = re.sub(r"\s+[A-Z]{2}$", "", cleaned)
    return cleaned, raw


def _parse_amount(amount_str: str, is_credit: bool) -> Optional[float]:
    """
    Parse the amount string into a float.  Handles commas, CR suffixes,
    parentheses and minus signs.  The ``is_credit`` flag denotes whether
    the CR suffix was present.
    """
    s = amount_str.strip().replace(",", "")
    # Remove currency symbols
    s = re.sub(r"[RM\$]\s*", "", s, flags=re.IGNORECASE)
    # Detect parentheses indicating credit
    credit = is_credit or s.endswith(")")
    if s.startswith("(") and s.endswith(")"):
        credit = True
        s = s[1:-1]
    # Remove trailing 'CR'
    s = re.sub(r"CR$", "", s, flags=re.IGNORECASE).strip()
    # Remove any plus or minus sign; we'll apply sign after parsing
    sign = 1
    if s.startswith("-"):
        sign = -1
        s = s.lstrip("-")
    try:
        value = float(s)
        if credit:
            sign = -1
        return sign * value
    except Exception:
        return None


def parse_maybank_pdf(data: bytes) -> List[Dict[str, Any]]:
    """
    Parse a Maybank credit card PDF statement into a list of transaction
    dictionaries.  If the PDF does not appear to be a Maybank statement the
    function returns an empty list.
    """
    rows: List[Dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        # Concatenate text from all pages for header detection
        all_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        # Quick sanity check: ensure the document contains the Maybank header
        if not ("STATEMENT OF CREDIT CARD ACCOUNT" in all_text.upper() or "PENYATA AKAUN KAD KREDIT" in all_text.upper()):
            return []
        # Flatten all lines preserving order for card and row parsing
        lines: List[str] = []
        for page in pdf.pages:
            txt = page.extract_text() or ""
            for line in txt.splitlines():
                line = line.rstrip()
                if line:
                    lines.append(line)

    # Extract statement date to infer year and month.  Search for a line
    # containing a date in the format ``DD MMM YY`` (e.g. ``12 JUL 25``) after
    # the phrase 'Statement Date'.  We consider the first occurrence.
    stmt_year: int = None  # type: ignore
    stmt_month: int = None  # type: ignore
    for i, line in enumerate(lines):
        if re.search(r"Statement Date", line, re.IGNORECASE):
            # Look ahead a couple of lines for the date
            for j in range(1, 4):
                if i + j < len(lines):
                    m = re.search(r"(\d{2})\s+([A-Z]{3})\s+(\d{2})", lines[i + j])
                    if m:
                        day, mon_abbr, yr = m.groups()
                        stmt_month = MONTHS.get(mon_abbr.upper())
                        stmt_year = int(yr) + (2000 if int(yr) < 70 else 1900)
                        break
            if stmt_year and stmt_month:
                break
    # Fallback: try to find any line with dd MMM yy if not found after Statement Date
    if stmt_year is None or stmt_month is None:
        for line in lines:
            m = re.search(r"(\d{2})\s+([A-Z]{3})\s+(\d{2})", line)
            if m:
                _, mon_abbr, yr = m.groups()
                stmt_month = MONTHS.get(mon_abbr.upper())
                stmt_year = int(yr) + (2000 if int(yr) < 70 else 1900)
                break
    # If we still don't know the statement date, bail out
    if stmt_year is None or stmt_month is None:
        return []

    # Track which card we are currently parsing.  Each card section begins
    # with a header identifying the cardholder and card number.
    current_card_last4: Optional[str] = None
    # Compile regexes once
    card_header_re = re.compile(
        r"VISA IKHWAN\s+(?P<tier>PLATINUM|GOLD).+?:\s+(?:\d{4}\s+){3}(?P<last4>\d{4})",
        re.IGNORECASE,
    )
    row_re = re.compile(
        r"^(?P<post>\d{2}/\d{2})\s+(?P<tran>\d{2}/\d{2})\s+(?P<desc>.+?)\s+(?P<amount>[0-9,\.]+)(?P<cr>CR)?$",
        re.IGNORECASE,
    )
    total_re = re.compile(r"TOTAL CREDIT THIS MONTH|TOTAL DEBIT THIS MONTH|SUB TOTAL|JUMLAH", re.IGNORECASE)

    for idx, line in enumerate(lines):
        # Detect card header
        m_card = card_header_re.search(line)
        if m_card:
            current_card_last4 = m_card.group("last4")
            continue
        # Stop parsing rows once we hit a totals section
        if total_re.search(line):
            current_card_last4 = None
            continue
        # Only attempt to parse rows if within a card section
        if current_card_last4:
            m_row = row_re.match(line)
            if m_row:
                post = m_row.group("post")
                tran = m_row.group("tran")
                desc = m_row.group("desc").strip()
                amt_str = m_row.group("amount").strip()
                cr_flag = bool(m_row.group("cr"))
                # parse dates
                post_date = _infer_date(post, stmt_year, stmt_month)
                txn_date = _infer_date(tran, stmt_year, stmt_month)
                # normalise description
                cleaned_desc, raw_desc = _normalise_description(desc)
                # parse amount
                amt = _parse_amount(amt_str, cr_flag)
                if amt is None:
                    continue
                # derive category/subcategory
                category = None
                subcategory = None
                updesc = cleaned_desc.upper()
                for key, (cat, subcat) in CATEGORY_MAPPING.items():
                    if key in updesc:
                        category = cat
                        subcategory = subcat
                        break
                row: Dict[str, Any] = {
                    "statement_month": f"{stmt_year}-{stmt_month:02d}",
                    "card_last4": current_card_last4,
                    "posting_date": post_date.isoformat() if post_date else None,
                    "transaction_date": txn_date.isoformat() if txn_date else None,
                    "description": cleaned_desc,
                    "description_raw": raw_desc,
                    "amount": amt,
                    "category": category,
                    "subcategory": subcategory,
                    "source": "maybank",
                }
                rows.append(row)
    return rows