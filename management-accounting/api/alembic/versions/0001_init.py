from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pattern", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id", ondelete="SET NULL")),
    )

    op.create_table(
        "statements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("statement_id", sa.Integer, sa.ForeignKey("statements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("txn_date", sa.Date),
        sa.Column("post_date", sa.Date),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("raw_row_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("external_id", sa.String(255)),
    )

    op.create_index(
        "uq_txn_upsert_guard",
        "transactions",
        ["statement_id", "txn_date", "description", "amount"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_txn_upsert_guard", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("statements")
    op.drop_table("rules")
    op.drop_table("categories")
    op.drop_table("users")
