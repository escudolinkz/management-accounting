from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import SessionLocal
from app import models
from app.security import hash_password

DEFAULTS = [
    "Income", "Groceries", "Dining", "Fuel", "Utilities", "Rent/Mortgage", "Entertainment", "Fees", "Transfers", "Other"
]

RULES = [
    ("petronas", "Fuel", 10),
    ("tng ewallet", "Transfers", 20),
    ("grabfood", "Dining", 20),
]

def main():
    db: Session = SessionLocal()
    # admin
    if not db.scalar(select(models.User).where(models.User.email=="admin@example.com")):
        db.add(models.User(email="admin@example.com", password_hash=hash_password("admin123")))
        db.commit()
    # categories
    for name in DEFAULTS:
        if not db.scalar(select(models.Category).where(models.Category.name==name)):
            db.add(models.Category(name=name)); db.commit()
    # rules
    for patt, cat, pri in RULES:
        c = db.scalar(select(models.Category).where(models.Category.name==cat))
        db.add(models.Rule(pattern=patt, category_id=c.id if c else None, priority=pri))
    db.commit()
    print("seeded")

if __name__ == "__main__":
    main()
