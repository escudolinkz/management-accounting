from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models

def apply_rules(db: Session, tx: models.Transaction, rules: list[models.Rule]):
    desc = (tx.description or "").lower()
    for r in sorted(rules, key=lambda x: (r.priority, r.id)):
        # perform a case‑insensitive substring search.  If the rule pattern
        # appears anywhere in the transaction description then assign the
        # category and subcategory from the rule and stop evaluating.  Do
        # not apply rules that are not active.
        if r.status != "active":
            continue
        if r.pattern.lower() in desc:
            tx.category_id = r.category_id
            tx.subcategory = r.subcategory
            break

def reapply_all(db: Session):
    rules = list(db.scalars(select(models.Rule)).all())
    txs = list(db.scalars(select(models.Transaction)).all())
    for tx in txs:
        apply_rules(db, tx, rules)
    db.commit()
