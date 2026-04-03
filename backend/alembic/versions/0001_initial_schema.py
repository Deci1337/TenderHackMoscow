"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "ste",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=True),
        sa.Column("attributes", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("name_tsv", sa.dialects.postgresql.TSVECTOR, nullable=True),
        sa.Column("embedding", Vector(312), nullable=True),
    )
    op.create_index("ix_ste_name_tsv", "ste", ["name_tsv"], postgresql_using="gin")
    op.create_index(
        "ix_ste_name_trgm", "ste", ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index("ix_ste_category", "ste", ["category"])

    op.create_table(
        "contracts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("purchase_name", sa.Text, nullable=True),
        sa.Column("contract_id", sa.Text, unique=True, nullable=False),
        sa.Column("ste_id", sa.BigInteger, nullable=True, index=True),
        sa.Column("contract_date", sa.Date, nullable=True),
        sa.Column("cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("customer_inn", sa.Text, nullable=False, index=True),
        sa.Column("customer_name", sa.Text, nullable=True),
        sa.Column("customer_region", sa.Text, nullable=True),
        sa.Column("supplier_inn", sa.Text, nullable=True),
        sa.Column("supplier_name", sa.Text, nullable=True),
        sa.Column("supplier_region", sa.Text, nullable=True),
    )

    op.create_table(
        "user_profiles",
        sa.Column("inn", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("region", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=True),
        sa.Column("profile_data", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_inn", sa.Text, nullable=False, index=True),
        sa.Column("ste_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("session_id", sa.Text, nullable=True, index=True),
        sa.Column("query", sa.Text, nullable=True),
        sa.Column("meta", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_events_user_type", "events", ["user_inn", "event_type"])


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("user_profiles")
    op.drop_table("contracts")
    op.drop_table("ste")
