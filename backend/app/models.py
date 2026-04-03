from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Date, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base


class STE(Base):
    """Standard Trade Entity - product catalog item."""
    __tablename__ = "ste"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict | None] = mapped_column(JSONB, default={})
    name_tsv: Mapped[str | None] = mapped_column(TSVECTOR)
    embedding = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)

    __table_args__ = (
        Index("ix_ste_name_tsv", "name_tsv", postgresql_using="gin"),
        Index("ix_ste_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
        Index("ix_ste_category", "category"),
    )


class Contract(Base):
    """Historical contract data linking customers to STE purchases."""
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    purchase_name: Mapped[str | None] = mapped_column(Text)
    contract_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    ste_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    contract_date: Mapped[date | None] = mapped_column(Date)
    cost: Mapped[float | None] = mapped_column(Numeric(15, 2))
    customer_inn: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(Text)
    customer_region: Mapped[str | None] = mapped_column(Text)
    supplier_inn: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(Text)
    supplier_region: Mapped[str | None] = mapped_column(Text)


class UserProfile(Base):
    """Customer profile built from contract history and onboarding."""
    __tablename__ = "user_profiles"

    inn: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    profile_data: Mapped[dict | None] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class Event(Base):
    """User interaction event for dynamic indexing and personalization."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_inn: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ste_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text, index=True)
    query: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("ix_events_user_type", "user_inn", "event_type"),
    )
