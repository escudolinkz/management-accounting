from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models

def apply_rules(db: Session, tx: models.Transaction, rules: list[models.Rule]):
    desc = (tx.description or "").lower()
    for r in sorted(rules, key=lambda x: x.priority):
        if r.pattern.lower() in desc:
            tx.category_id = r.category_id
            break

def reapply_all(db: Session):
    rules = list(db.scalars(select(models.Rule)).all())
    txs = list(db.scalars(select(models.Transaction)).all())
    for tx in txs:
        apply_rules(db, tx, rules)
    db.commit()
