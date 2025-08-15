from __future__ import annotations
from celery import Celery
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
            txn_date = r.get("txn_date")
            desc = (r.get("description") or "").strip()
            amt = r.get("amount")
            tx = models.Transaction(
                statement_id=statement_id,
                txn_date=txn_date,
                description=desc,
                amount=amt,
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
