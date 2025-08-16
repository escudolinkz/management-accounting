from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
from datetime import date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped = mapped_column(DateTime, server_default=func.now())

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class Rule(Base):
    """
    A rule used to automatically categorise transactions.  Each rule consists of a
    case‑insensitive keyword pattern, an optional category and subcategory and
    a priority which determines the order of evaluation (lower numbers are
    applied first).  Rules can be toggled on or off by changing the status
    field.  The created_at timestamp allows sorting rules in the order they
    were added.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    # keyword/phrase to search for (case insensitive) in transaction descriptions
    pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    # priority controls evaluation order; lower numbers run first
    priority: Mapped[int] = mapped_column(Integer, default=100)
    # optional foreign key into categories table
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    category = relationship("Category")
    # optional free‑form subcategory label (e.g. "AI Services", "Cloud Services")
    subcategory: Mapped[str | None] = mapped_column(String(100))
    # status of rule; currently only "active" is used but allows future
    # disabling of rules without deletion
    status: Mapped[str] = mapped_column(String(32), default="active")
    # creation timestamp
    created_at: Mapped = mapped_column(DateTime, server_default=func.now())

class Statement(Base):
    __tablename__ = "statements"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped = mapped_column(DateTime, server_default=func.now())
    transactions = relationship("Transaction", back_populates="statement", cascade="all,delete")

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(ForeignKey("statements.id", ondelete="CASCADE"), nullable=False)
    statement = relationship("Statement", back_populates="transactions")
    # date the transaction actually occurred
    txn_date: Mapped[date | None] = mapped_column(Date)
    # date the transaction was posted to the account (if different)
    post_date: Mapped[date | None] = mapped_column(Date)
    # merchant/description text
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # transaction amount in RM; positive for debits/charges, negative for
    # credits/refunds
    amount: Mapped = mapped_column(Numeric(12, 2), nullable=False)
    # optional foreign key into categories table
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    category = relationship("Category")
    # optional subcategory label stored on the transaction to preserve the
    # subcategory resolved when applying rules
    subcategory: Mapped[str | None] = mapped_column(String(100))
    # raw row JSON for auditing and debugging the parser
    raw_row_json: Mapped = mapped_column(JSONB, default=dict)
    # optional external ID used by some banks to uniquely identify a transaction
    external_id: Mapped[str | None] = mapped_column(String(255))
