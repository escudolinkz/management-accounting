from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import SessionLocal
from app import models
from app.security import hash_password

# Base set of categories used by the application.  These broadly mirror
# business accounting categories and are intended to be extensible.
DEFAULTS = [
    "Business Income",
    "Operating Expenses",
    "Technology Expenses",
    "Other",
]

# Predefined rules to help users get started.  Each entry is a tuple of
# (keyword, category name, subcategory, priority).  A lower priority
# number causes the rule to be applied earlier.  Subcategory may be
# None if not applicable.
RULES = [
    ("ANTHROPIC", "Technology Expenses", "AI Services", 10),
    ("AWS", "Technology Expenses", "Cloud Services", 10),
    ("OPENAI", "Technology Expenses", "AI Services", 10),
    ("SALARY", "Operating Expenses", "Salary", 10),
    ("STRIPE", "Business Income", "Online Payments", 10),
]

def main():
    db: Session = SessionLocal()
    # admin
    if not db.scalar(select(models.User).where(models.User.email=="admin@example.com")):
        db.add(models.User(email="admin@example.com", password_hash=hash_password("admin123")))
        db.commit()
    # categories
    for name in DEFAULTS:
        if not db.scalar(select(models.Category).where(models.Category.name == name)):
            db.add(models.Category(name=name))
            db.commit()
    # rules
    for keyword, cat_name, subcat, pri in RULES:
        c = db.scalar(select(models.Category).where(models.Category.name == cat_name))
        rule = models.Rule(
            pattern=keyword,
            priority=pri,
            category_id=c.id if c else None,
            subcategory=subcat,
            status="active",
        )
        db.add(rule)
    db.commit()
    print("seeded")

if __name__ == "__main__":
    main()
