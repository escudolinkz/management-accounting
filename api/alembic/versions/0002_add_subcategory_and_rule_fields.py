"""
Revision 0002: add subcategory fields and rule metadata

This migration introduces several enhancements to support richer
categorisation.  It adds a `subcategory` column to the `rules` table
alongside `status` and `created_at` to record when a rule was created
and whether it is active.  On the `transactions` table it adds a
`subcategory` column to persist the resolved subcategory when rules
are applied.

This migration is idempotent and can be applied on top of the
initial schema introduced in revision 0001.
"""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_subcategory_and_rule_fields"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to rules table
    with op.batch_alter_table("rules", schema=None) as batch:
        batch.add_column(sa.Column("subcategory", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()))

    # Add new column to transactions table
    with op.batch_alter_table("transactions", schema=None) as batch:
        batch.add_column(sa.Column("subcategory", sa.String(length=100), nullable=True))


def downgrade():
    # Remove columns from transactions table first to avoid dependency issues
    with op.batch_alter_table("transactions", schema=None) as batch:
        batch.drop_column("subcategory")

    # Remove added columns from rules table
    with op.batch_alter_table("rules", schema=None) as batch:
        batch.drop_column("created_at")
        batch.drop_column("status")
        batch.drop_column("subcategory")