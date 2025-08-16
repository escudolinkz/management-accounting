from __future__ import annotations
from celery import Celery
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date
from app.config import settings
from app.db import SessionLocal
from app import models
from app.parser import parse_pdf_bytes

celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@celery_app.task(name="queue_parse")
def queue_parse(statement_id: int, path: str):
    db: Session = SessionLocal()
    try:
        stmt = db.get(models.Statement, statement_id)
        if not stmt:
            return
        with open(path, "rb") as rf:
            data = rf.read()
        rows = parse_pdf_bytes(data)
        # Upsert guard by (statement_id, txn_date, description, amount)
        for r in rows:
            # Determine posting/transaction dates.  The Maybank parser returns
            # ISO strings for posting_date and transaction_date; the generic
            # parser returns only txn_date.  Attempt to parse whichever is
            # available.
            txn_date = r.get("transaction_date") or r.get("txn_date")
            post_date = r.get("posting_date")
            # Normalise to date objects if strings are provided
            if isinstance(txn_date, str):
                try:
                    txn_date_obj = datetime.fromisoformat(txn_date).date()
                except Exception:
                    txn_date_obj = None
            else:
                txn_date_obj = txn_date
            if isinstance(post_date, str):
                try:
                    post_date_obj = datetime.fromisoformat(post_date).date()
                except Exception:
                    post_date_obj = None
            else:
                post_date_obj = post_date
            desc = (r.get("description") or "").strip()
            amt = r.get("amount")
            # Determine category and subcategory if provided by parser
            category_id = None
            subcategory = None
            cat_name = r.get("category")
            subcategory = r.get("subcategory")
            if cat_name:
                # Look up (or create) category by name
                cat = db.scalar(select(models.Category).where(models.Category.name == cat_name))
                if not cat:
                    cat = models.Category(name=cat_name)
                    db.add(cat)
                    db.commit(); db.refresh(cat)
                category_id = cat.id
            tx = models.Transaction(
                statement_id=statement_id,
                txn_date=txn_date_obj,
                post_date=post_date_obj,
                description=desc,
                amount=amt,
                category_id=category_id,
                subcategory=subcategory,
                raw_row_json=r,
            )
            try:
                db.add(tx)
                db.commit()
            except Exception:
                db.rollback()
        # Apply rules
        from .repo import reapply_all
        reapply_all(db)
        stmt.status = "processed"; stmt.error_message = None
        db.add(stmt); db.commit()
    except Exception as e:
        if 'stmt' in locals() and stmt:
            stmt.status = "failed"; stmt.error_message = str(e)
            db.add(stmt); db.commit()
    finally:
        db.close()
