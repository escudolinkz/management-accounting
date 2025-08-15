from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
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
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    category = relationship("Category")

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
    txn_date: Mapped
    post_date: Mapped
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped = mapped_column(Numeric(12,2), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    category = relationship("Category")
    raw_row_json = mapped_column(JSONB, default=dict)
    external_id: Mapped[str | None] = mapped_column(String(255))
